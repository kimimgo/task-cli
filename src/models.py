"""Core models for task-cli.

This module defines the core data structures for task management:
- Task: A dataclass representing a task with its properties
- Priority: Enum for task priority levels
- Status: Enum for task completion status
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class Priority(Enum):
    """Task priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Status(Enum):
    """Task completion status."""

    PENDING = "pending"
    DONE = "done"


@dataclass
class Task:
    """Task model representing a single task item.

    Attributes:
        id: Unique identifier for the task (auto-generated if None)
        title: Task description/title
        status: Current status of the task (PENDING or DONE)
        priority: Priority level of the task
        created_at: Timestamp when the task was created
    """

    title: str
    status: Status = Status.PENDING
    priority: Priority = Priority.MEDIUM
    id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)
