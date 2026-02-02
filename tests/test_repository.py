"""Comprehensive tests for TaskRepository."""

import tempfile
from pathlib import Path

import pytest

from src.models import Priority, Status, Task
from src.repository import TaskRepository
from src.storage import JsonStorage


class TestTaskRepository:
    """Test suite for TaskRepository."""

    @pytest.fixture
    def temp_storage(self):
        """Create a temporary storage file for testing."""
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
    def repo(self, temp_storage):
        """Create a TaskRepository with temporary storage."""
        storage = JsonStorage(temp_storage)
        return TaskRepository(storage)

    def test_create_task_default_priority(self, repo):
        """Test creating task with default priority."""
        task = repo.create_task("Test task")
        assert task.id == 1
        assert task.title == "Test task"
        assert task.priority == Priority.MEDIUM
        assert task.status == Status.PENDING

    def test_create_task_with_priority(self, repo):
        """Test creating task with specific priority."""
        task = repo.create_task("Urgent task", Priority.HIGH)
        assert task.id == 1
        assert task.title == "Urgent task"
        assert task.priority == Priority.HIGH
        assert task.status == Status.PENDING

    def test_create_multiple_tasks_sequential_ids(self, repo):
        """Test that multiple tasks get sequential IDs."""
        task1 = repo.create_task("Task 1")
        task2 = repo.create_task("Task 2")
        task3 = repo.create_task("Task 3")

        assert task1.id == 1
        assert task2.id == 2
        assert task3.id == 3

    def test_get_all_tasks_empty(self, repo):
        """Test get_all_tasks returns empty list when no tasks exist."""
        tasks = repo.get_all_tasks()
        assert tasks == []

    def test_get_all_tasks_returns_all(self, repo):
        """Test get_all_tasks returns all tasks."""
        repo.create_task("Task 1")
        repo.create_task("Task 2")
        repo.create_task("Task 3")

        tasks = repo.get_all_tasks()
        assert len(tasks) == 3
        assert [t.id for t in tasks] == [1, 2, 3]

    def test_get_all_tasks_sorted_by_id(self, repo):
        """Test get_all_tasks returns tasks sorted by ID."""
        repo.create_task("Task 1")
        repo.create_task("Task 2")
        repo.create_task("Task 3")

        tasks = repo.get_all_tasks()
        assert tasks[0].id < tasks[1].id < tasks[2].id

    def test_get_all_tasks_filter_by_pending(self, repo):
        """Test filtering tasks by PENDING status."""
        task1 = repo.create_task("Task 1")
        repo.create_task("Task 2")
        repo.mark_done(task1.id)

        tasks = repo.get_all_tasks(status=Status.PENDING)
        assert len(tasks) == 1
        assert tasks[0].id == 2

    def test_get_all_tasks_filter_by_done(self, repo):
        """Test filtering tasks by DONE status."""
        task1 = repo.create_task("Task 1")
        repo.create_task("Task 2")
        repo.mark_done(task1.id)

        tasks = repo.get_all_tasks(status=Status.DONE)
        assert len(tasks) == 1
        assert tasks[0].id == 1

    def test_get_task_existing(self, repo):
        """Test getting an existing task."""
        created_task = repo.create_task("Test task")
        retrieved_task = repo.get_task(created_task.id)

        assert retrieved_task is not None
        assert retrieved_task.id == created_task.id
        assert retrieved_task.title == created_task.title

    def test_get_task_nonexistent(self, repo):
        """Test getting a non-existent task returns None."""
        task = repo.get_task(999)
        assert task is None

    def test_update_task_success(self, repo):
        """Test updating an existing task."""
        task = repo.create_task("Original title", Priority.LOW)
        task.title = "Updated title"
        task.priority = Priority.HIGH

        updated_task = repo.update_task(task)
        assert updated_task.title == "Updated title"
        assert updated_task.priority == Priority.HIGH

        # Verify persistence
        retrieved_task = repo.get_task(task.id)
        assert retrieved_task.title == "Updated title"
        assert retrieved_task.priority == Priority.HIGH

    def test_update_task_without_id_raises_error(self, repo):
        """Test updating task without ID raises ValueError."""
        task = Task(title="Test task")
        assert task.id is None

        with pytest.raises(ValueError, match="Task ID cannot be None"):
            repo.update_task(task)

    def test_update_task_nonexistent_raises_error(self, repo):
        """Test updating non-existent task raises ValueError."""
        task = Task(id=999, title="Test task")

        with pytest.raises(ValueError, match="Task with ID 999 does not exist"):
            repo.update_task(task)

    def test_delete_task_success(self, repo):
        """Test deleting an existing task."""
        task = repo.create_task("Test task")
        result = repo.delete_task(task.id)

        assert result is True
        assert repo.get_task(task.id) is None

    def test_delete_task_nonexistent(self, repo):
        """Test deleting non-existent task returns False."""
        result = repo.delete_task(999)
        assert result is False

    def test_mark_done_success(self, repo):
        """Test marking task as done."""
        task = repo.create_task("Test task")
        assert task.status == Status.PENDING

        updated_task = repo.mark_done(task.id)
        assert updated_task is not None
        assert updated_task.status == Status.DONE

        # Verify persistence
        retrieved_task = repo.get_task(task.id)
        assert retrieved_task.status == Status.DONE

    def test_mark_done_nonexistent(self, repo):
        """Test marking non-existent task as done returns None."""
        result = repo.mark_done(999)
        assert result is None

    def test_mark_done_already_done(self, repo):
        """Test marking already done task as done."""
        task = repo.create_task("Test task")
        repo.mark_done(task.id)

        # Mark done again
        updated_task = repo.mark_done(task.id)
        assert updated_task is not None
        assert updated_task.status == Status.DONE

    def test_repository_uses_default_storage(self):
        """Test that repository creates default storage if none provided."""
        repo = TaskRepository()
        assert repo.storage is not None

    def test_repository_uses_custom_storage(self, temp_storage):
        """Test that repository uses provided storage."""
        storage = JsonStorage(temp_storage)
        repo = TaskRepository(storage)
        assert repo.storage is storage

    def test_persistence_across_repository_instances(self, temp_storage):
        """Test that data persists across repository instances."""
        storage = JsonStorage(temp_storage)

        # Create task with first repo instance
        repo1 = TaskRepository(storage)
        task = repo1.create_task("Test task", Priority.HIGH)
        task_id = task.id

        # Retrieve task with second repo instance
        repo2 = TaskRepository(storage)
        retrieved_task = repo2.get_task(task_id)

        assert retrieved_task is not None
        assert retrieved_task.id == task_id
        assert retrieved_task.title == "Test task"
        assert retrieved_task.priority == Priority.HIGH

    def test_delete_task_updates_storage(self, repo):
        """Test that deleting task removes it from storage."""
        task1 = repo.create_task("Task 1")
        task2 = repo.create_task("Task 2")

        repo.delete_task(task1.id)

        tasks = repo.get_all_tasks()
        assert len(tasks) == 1
        assert tasks[0].id == task2.id

    def test_create_task_after_delete_uses_next_id(self, repo):
        """Test that new tasks after deletion use incremental IDs."""
        task1 = repo.create_task("Task 1")
        repo.create_task("Task 2")  # Create second task (ID=2)
        repo.delete_task(task1.id)

        task3 = repo.create_task("Task 3")
        assert task3.id == 3  # ID continues from max, not reusing deleted ID

    def test_task_title_with_special_characters(self, repo):
        """Test creating task with special characters in title."""
        task = repo.create_task('Task with "quotes" and \n newlines')
        retrieved = repo.get_task(task.id)
        assert retrieved.title == task.title

    def test_empty_title(self, repo):
        """Test creating task with empty title."""
        task = repo.create_task("")
        assert task.title == ""
        assert task.id == 1

    def test_very_long_title(self, repo):
        """Test creating task with very long title."""
        long_title = "A" * 10000
        task = repo.create_task(long_title)
        retrieved = repo.get_task(task.id)
        assert retrieved.title == long_title

    def test_all_priority_levels(self, repo):
        """Test creating tasks with all priority levels."""
        task_low = repo.create_task("Low priority", Priority.LOW)
        task_medium = repo.create_task("Medium priority", Priority.MEDIUM)
        task_high = repo.create_task("High priority", Priority.HIGH)

        assert repo.get_task(task_low.id).priority == Priority.LOW
        assert repo.get_task(task_medium.id).priority == Priority.MEDIUM
        assert repo.get_task(task_high.id).priority == Priority.HIGH

    def test_filter_empty_status(self, repo):
        """Test filtering by status when no tasks match."""
        repo.create_task("Task 1")
        repo.create_task("Task 2")

        # All tasks are pending by default
        done_tasks = repo.get_all_tasks(status=Status.DONE)
        assert done_tasks == []

    def test_mixed_status_filter(self, repo):
        """Test filtering with mixed task statuses."""
        task1 = repo.create_task("Task 1")
        task2 = repo.create_task("Task 2")
        task3 = repo.create_task("Task 3")

        repo.mark_done(task1.id)
        repo.mark_done(task3.id)

        pending = repo.get_all_tasks(status=Status.PENDING)
        done = repo.get_all_tasks(status=Status.DONE)

        assert len(pending) == 1
        assert pending[0].id == task2.id
        assert len(done) == 2
        assert [t.id for t in done] == [task1.id, task3.id]
