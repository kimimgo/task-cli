"""Comprehensive tests for storage layer."""

import json
import tempfile
import threading
from datetime import datetime
from pathlib import Path

import pytest

from src.models import Priority, Status, Task
from src.storage import JsonStorage, Storage


class TestJsonStorage:
    """Test suite for JsonStorage implementation."""

    @pytest.fixture
    def temp_file(self):
        """Create a temporary file path for testing."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            temp_path = f.name
        # Delete the file immediately - we just need the path
        Path(temp_path).unlink()
        yield temp_path
        # Cleanup
        path = Path(temp_path)
        if path.exists():
            path.unlink()

    @pytest.fixture
    def storage(self, temp_file):
        """Create a JsonStorage instance with temporary file."""
        return JsonStorage(temp_file)

    @pytest.fixture
    def sample_tasks(self):
        """Create sample tasks for testing."""
        return {
            1: Task(
                id=1,
                title="Test task 1",
                status=Status.PENDING,
                priority=Priority.HIGH,
                created_at=datetime(2024, 1, 1, 12, 0, 0),
            ),
            2: Task(
                id=2,
                title="Test task 2",
                status=Status.DONE,
                priority=Priority.LOW,
                created_at=datetime(2024, 1, 2, 12, 0, 0),
            ),
        }

    def test_storage_is_abstract(self):
        """Test that Storage is an abstract base class."""
        with pytest.raises(TypeError):
            Storage()

    def test_save_creates_file(self, storage, sample_tasks):
        """Test that save creates a file if it doesn't exist."""
        assert not Path(storage.file_path).exists()
        storage.save(sample_tasks)
        assert Path(storage.file_path).exists()

    def test_save_writes_valid_json(self, storage, sample_tasks):
        """Test that save writes valid JSON data."""
        storage.save(sample_tasks)

        with open(storage.file_path, "r") as f:
            data = json.load(f)

        assert "1" in data
        assert "2" in data
        assert data["1"]["title"] == "Test task 1"
        assert data["1"]["status"] == "pending"
        assert data["1"]["priority"] == "high"
        assert data["2"]["title"] == "Test task 2"
        assert data["2"]["status"] == "done"
        assert data["2"]["priority"] == "low"

    def test_load_empty_file(self, storage):
        """Test that load returns empty dict when file doesn't exist."""
        assert storage.load() == {}

    def test_load_empty_json_file(self, storage):
        """Test that load returns empty dict when file is empty."""
        # Create empty file
        Path(storage.file_path).touch()
        assert storage.load() == {}

    def test_save_and_load_roundtrip(self, storage, sample_tasks):
        """Test that data survives save-load roundtrip."""
        storage.save(sample_tasks)
        loaded_tasks = storage.load()

        assert len(loaded_tasks) == len(sample_tasks)
        for task_id, task in sample_tasks.items():
            assert task_id in loaded_tasks
            loaded_task = loaded_tasks[task_id]
            assert loaded_task.id == task.id
            assert loaded_task.title == task.title
            assert loaded_task.status == task.status
            assert loaded_task.priority == task.priority
            assert loaded_task.created_at == task.created_at

    def test_save_overwrites_existing_data(self, storage, sample_tasks):
        """Test that save overwrites existing data."""
        storage.save(sample_tasks)

        new_tasks = {
            3: Task(
                id=3,
                title="New task",
                status=Status.PENDING,
                priority=Priority.MEDIUM,
                created_at=datetime(2024, 1, 3, 12, 0, 0),
            )
        }
        storage.save(new_tasks)

        loaded_tasks = storage.load()
        assert len(loaded_tasks) == 1
        assert 3 in loaded_tasks
        assert 1 not in loaded_tasks
        assert 2 not in loaded_tasks

    def test_delete_removes_file(self, storage, sample_tasks):
        """Test that delete removes the storage file."""
        storage.save(sample_tasks)
        assert Path(storage.file_path).exists()

        storage.delete()
        assert not Path(storage.file_path).exists()

    def test_delete_nonexistent_file(self, storage):
        """Test that delete on non-existent file doesn't raise error."""
        assert not Path(storage.file_path).exists()
        storage.delete()  # Should not raise

    def test_save_creates_parent_directories(self):
        """Test that save creates parent directories if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "subdir" / "nested" / "tasks.json"
            storage = JsonStorage(str(file_path))

            tasks = {1: Task(id=1, title="Test")}
            storage.save(tasks)

            assert file_path.exists()
            assert file_path.parent.exists()

    def test_load_preserves_task_types(self, storage):
        """Test that load correctly deserializes enum types."""
        tasks = {
            1: Task(
                id=1,
                title="Test",
                status=Status.DONE,
                priority=Priority.HIGH,
                created_at=datetime(2024, 1, 1),
            )
        }
        storage.save(tasks)
        loaded = storage.load()

        assert isinstance(loaded[1].status, Status)
        assert isinstance(loaded[1].priority, Priority)
        assert loaded[1].status == Status.DONE
        assert loaded[1].priority == Priority.HIGH

    def test_save_empty_dict(self, storage):
        """Test that save handles empty task dictionary."""
        storage.save({})
        loaded = storage.load()
        assert loaded == {}

    def test_concurrent_reads(self, storage, sample_tasks):
        """Test that concurrent reads work correctly with file locking."""
        storage.save(sample_tasks)

        results = []
        errors = []

        def read_tasks():
            try:
                tasks = storage.load()
                results.append(len(tasks))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=read_tasks) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert all(r == 2 for r in results)

    def test_concurrent_writes(self, storage):
        """Test that concurrent writes don't corrupt data."""
        errors = []

        def write_task(task_id):
            try:
                tasks = {task_id: Task(id=task_id, title=f"Task {task_id}")}
                storage.save(tasks)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=write_task, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

        # File should contain valid JSON (last write wins)
        loaded = storage.load()
        assert len(loaded) == 1
        assert list(loaded.values())[0].title.startswith("Task ")

    def test_load_handles_corrupted_json(self, storage):
        """Test that load handles corrupted JSON gracefully."""
        # Write invalid JSON
        with open(storage.file_path, "w") as f:
            f.write("{invalid json")

        with pytest.raises(json.JSONDecodeError):
            storage.load()

    def test_datetime_serialization(self, storage):
        """Test that datetime is correctly serialized and deserialized."""
        now = datetime.now()
        tasks = {1: Task(id=1, title="Test", created_at=now)}
        storage.save(tasks)

        loaded = storage.load()
        # Compare with microsecond precision
        assert loaded[1].created_at.replace(microsecond=0) == now.replace(microsecond=0)

    def test_special_characters_in_title(self, storage):
        """Test that special characters in title are handled correctly."""
        tasks = {1: Task(id=1, title='Task with "quotes" and \n newlines and \t tabs')}
        storage.save(tasks)
        loaded = storage.load()

        assert loaded[1].title == tasks[1].title

    def test_large_task_set(self, storage):
        """Test that storage handles large number of tasks."""
        tasks = {i: Task(id=i, title=f"Task {i}") for i in range(1000)}
        storage.save(tasks)
        loaded = storage.load()

        assert len(loaded) == 1000
        assert all(loaded[i].title == f"Task {i}" for i in range(1000))

    def test_custom_file_path(self):
        """Test that storage works with custom file paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_path = Path(tmpdir) / "custom_tasks.json"
            storage = JsonStorage(str(custom_path))

            tasks = {1: Task(id=1, title="Test")}
            storage.save(tasks)

            assert custom_path.exists()
            loaded = storage.load()
            assert len(loaded) == 1
