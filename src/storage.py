"""Storage layer for task-cli.

This module provides an abstract storage interface and concrete implementations
for persisting tasks. The JsonStorage implementation uses file-based JSON storage
with fcntl-based file locking for thread-safety.
"""

import fcntl
import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional

from src.models import Priority, Status, Task


class Storage(ABC):
    """Abstract base class for task storage implementations."""

    @abstractmethod
    def save(self, tasks: Dict[int, Task]) -> None:
        """Save tasks to storage.

        Args:
            tasks: Dictionary mapping task IDs to Task objects
        """
        pass

    @abstractmethod
    def load(self) -> Dict[int, Task]:
        """Load tasks from storage.

        Returns:
            Dictionary mapping task IDs to Task objects
        """
        pass

    @abstractmethod
    def delete(self) -> None:
        """Delete all data from storage."""
        pass


class JsonStorage(Storage):
    """JSON file-based storage implementation with file locking.

    This implementation uses fcntl for file locking to ensure thread-safe
    operations when reading/writing the JSON file.

    Attributes:
        file_path: Path to the JSON storage file
    """

    def __init__(self, file_path: Optional[str] = None):
        """Initialize JsonStorage with a file path.

        Args:
            file_path: Path to the JSON file for storage. If None, uses
                      TASK_DB_PATH environment variable or defaults to tasks.json
        """
        if file_path is None:
            file_path = os.environ.get("TASK_DB_PATH", "tasks.json")
        self.file_path = Path(file_path)

    def save(self, tasks: Dict[int, Task]) -> None:
        """Save tasks to JSON file with file locking.

        Args:
            tasks: Dictionary mapping task IDs to Task objects
        """
        # Ensure parent directory exists
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert tasks to serializable format
        serializable_tasks = {}
        for task_id, task in tasks.items():
            serializable_tasks[str(task_id)] = {
                "id": task.id,
                "title": task.title,
                "status": task.status.value,
                "priority": task.priority.value,
                "created_at": task.created_at.isoformat()
            }

        # Write with file locking
        with open(self.file_path, 'w') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                json.dump(serializable_tasks, f, indent=2)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def load(self) -> Dict[int, Task]:
        """Load tasks from JSON file with file locking.

        Returns:
            Dictionary mapping task IDs to Task objects. Returns empty dict
            if file doesn't exist or is empty.
        """
        if not self.file_path.exists():
            return {}

        # Read with file locking
        with open(self.file_path, 'r') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            try:
                content = f.read().strip()
                if not content:
                    return {}

                data = json.loads(content)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        # Convert from serializable format to Task objects
        tasks = {}
        for task_id_str, task_data in data.items():
            from datetime import datetime
            task = Task(
                id=task_data["id"],
                title=task_data["title"],
                status=Status(task_data["status"]),
                priority=Priority(task_data["priority"]),
                created_at=datetime.fromisoformat(task_data["created_at"])
            )
            tasks[int(task_id_str)] = task

        return tasks

    def delete(self) -> None:
        """Delete the JSON storage file.

        If the file doesn't exist, this method does nothing.
        """
        if self.file_path.exists():
            self.file_path.unlink()
