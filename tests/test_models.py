"""Tests for core models."""

from datetime import datetime

from src.models import Priority, Status, Task


class TestPriority:
    """Tests for Priority enum."""

    def test_priority_values(self):
        """Test that Priority enum has correct values."""
        assert Priority.LOW.value == "low"
        assert Priority.MEDIUM.value == "medium"
        assert Priority.HIGH.value == "high"

    def test_priority_members(self):
        """Test that all expected priority levels exist."""
        priorities = [p.name for p in Priority]
        assert "LOW" in priorities
        assert "MEDIUM" in priorities
        assert "HIGH" in priorities
        assert len(priorities) == 3


class TestStatus:
    """Tests for Status enum."""

    def test_status_values(self):
        """Test that Status enum has correct values."""
        assert Status.PENDING.value == "pending"
        assert Status.DONE.value == "done"

    def test_status_members(self):
        """Test that all expected statuses exist."""
        statuses = [s.name for s in Status]
        assert "PENDING" in statuses
        assert "DONE" in statuses
        assert len(statuses) == 2


class TestTask:
    """Tests for Task dataclass."""

    def test_task_creation_with_title_only(self):
        """Test creating a task with only title."""
        task = Task(title="Test task")

        assert task.title == "Test task"
        assert task.status == Status.PENDING
        assert task.priority == Priority.MEDIUM
        assert task.id is None
        assert isinstance(task.created_at, datetime)

    def test_task_creation_with_all_fields(self):
        """Test creating a task with all fields specified."""
        created_time = datetime(2026, 2, 1, 12, 0, 0)
        task = Task(
            id=1,
            title="Complete task",
            status=Status.DONE,
            priority=Priority.HIGH,
            created_at=created_time,
        )

        assert task.id == 1
        assert task.title == "Complete task"
        assert task.status == Status.DONE
        assert task.priority == Priority.HIGH
        assert task.created_at == created_time

    def test_task_default_status(self):
        """Test that default status is PENDING."""
        task = Task(title="New task")
        assert task.status == Status.PENDING

    def test_task_default_priority(self):
        """Test that default priority is MEDIUM."""
        task = Task(title="New task")
        assert task.priority == Priority.MEDIUM

    def test_task_default_id(self):
        """Test that default id is None."""
        task = Task(title="New task")
        assert task.id is None

    def test_task_created_at_auto_generated(self):
        """Test that created_at is automatically set to current time."""
        before = datetime.now()
        task = Task(title="New task")
        after = datetime.now()

        assert before <= task.created_at <= after

    def test_task_with_custom_priority(self):
        """Test creating tasks with different priority levels."""
        low_task = Task(title="Low priority", priority=Priority.LOW)
        medium_task = Task(title="Medium priority", priority=Priority.MEDIUM)
        high_task = Task(title="High priority", priority=Priority.HIGH)

        assert low_task.priority == Priority.LOW
        assert medium_task.priority == Priority.MEDIUM
        assert high_task.priority == Priority.HIGH

    def test_task_with_custom_status(self):
        """Test creating tasks with different statuses."""
        pending_task = Task(title="Pending task", status=Status.PENDING)
        done_task = Task(title="Done task", status=Status.DONE)

        assert pending_task.status == Status.PENDING
        assert done_task.status == Status.DONE

    def test_task_equality(self):
        """Test that tasks with same values are equal."""
        created_time = datetime(2026, 2, 1, 12, 0, 0)
        task1 = Task(
            id=1,
            title="Same task",
            status=Status.PENDING,
            priority=Priority.HIGH,
            created_at=created_time,
        )
        task2 = Task(
            id=1,
            title="Same task",
            status=Status.PENDING,
            priority=Priority.HIGH,
            created_at=created_time,
        )

        assert task1 == task2

    def test_task_inequality(self):
        """Test that tasks with different values are not equal."""
        task1 = Task(id=1, title="Task 1")
        task2 = Task(id=2, title="Task 2")

        assert task1 != task2

    def test_task_repr(self):
        """Test task string representation."""
        task = Task(id=1, title="Test task", status=Status.PENDING, priority=Priority.HIGH)

        repr_str = repr(task)
        assert "Task" in repr_str
        assert "title='Test task'" in repr_str
        assert "id=1" in repr_str
