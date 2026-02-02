"""Task repository for managing task operations.

This module provides a high-level TaskRepository class that manages tasks
using the storage layer. It handles task creation, retrieval, updates, and deletion.
"""

from typing import List, Optional

from src.models import Priority, Status, Task
from src.storage import JsonStorage, Storage


class TaskRepository:
    """Repository for managing tasks with storage backend.

    This class provides high-level operations for task management, including
    creating, retrieving, updating, and deleting tasks. It uses a Storage
    implementation for persistence and manages task ID generation.

    Attributes:
        storage: Storage backend for persisting tasks
    """

    def __init__(self, storage: Optional[Storage] = None):
        """Initialize TaskRepository with a storage backend.

        Args:
            storage: Storage implementation to use. If None, uses JsonStorage
                    with default file path.
        """
        self.storage = storage or JsonStorage()

    def create_task(self, title: str, priority: Priority = Priority.MEDIUM) -> Task:
        """Create a new task.

        Args:
            title: Task title/description
            priority: Task priority level (default: MEDIUM)

        Returns:
            The created Task object with assigned ID
        """
        tasks = self.storage.load()

        # Generate new ID
        next_id = max(tasks.keys(), default=0) + 1

        # Create task with generated ID
        task = Task(id=next_id, title=title, priority=priority, status=Status.PENDING)

        # Save task
        tasks[next_id] = task
        self.storage.save(tasks)

        return task

    def get_all_tasks(self, status: Optional[Status] = None) -> List[Task]:
        """Get all tasks, optionally filtered by status.

        Args:
            status: Optional status filter. If provided, only tasks with
                   this status are returned.

        Returns:
            List of Task objects, sorted by ID
        """
        tasks = self.storage.load()

        # Filter by status if provided
        if status is not None:
            tasks = {task_id: task for task_id, task in tasks.items() if task.status == status}

        # Return sorted by ID
        return [tasks[task_id] for task_id in sorted(tasks.keys())]

    def get_task(self, task_id: int) -> Optional[Task]:
        """Get a specific task by ID.

        Args:
            task_id: ID of the task to retrieve

        Returns:
            Task object if found, None otherwise
        """
        tasks = self.storage.load()
        return tasks.get(task_id)

    def update_task(self, task: Task) -> Task:
        """Update an existing task.

        Args:
            task: Task object with updated data. Must have valid ID.

        Returns:
            The updated Task object

        Raises:
            ValueError: If task ID is None or task doesn't exist
        """
        if task.id is None:
            raise ValueError("Task ID cannot be None")

        tasks = self.storage.load()

        if task.id not in tasks:
            raise ValueError(f"Task with ID {task.id} does not exist")

        tasks[task.id] = task
        self.storage.save(tasks)

        return task

    def delete_task(self, task_id: int) -> bool:
        """Delete a task by ID.

        Args:
            task_id: ID of the task to delete

        Returns:
            True if task was deleted, False if task didn't exist
        """
        tasks = self.storage.load()

        if task_id not in tasks:
            return False

        del tasks[task_id]
        self.storage.save(tasks)

        return True

    def mark_done(self, task_id: int) -> Optional[Task]:
        """Mark a task as done.

        Args:
            task_id: ID of the task to mark as done

        Returns:
            Updated Task object if found, None if task doesn't exist
        """
        task = self.get_task(task_id)
        if task is None:
            return None

        task.status = Status.DONE
        return self.update_task(task)
