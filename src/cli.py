"""Command-line interface for task-cli.

This module provides the CLI interface for managing tasks using argparse.
It supports the following commands:
- add: Create a new task
- list: List all tasks or filter by status
- done: Mark a task as completed
- delete: Delete a task
"""

import argparse
import sys
from typing import List, Optional

from src.models import Priority, Status
from src.repository import TaskRepository


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser.

    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog="task",
        description="CLI-based task management tool"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Add command
    add_parser = subparsers.add_parser("add", help="Add a new task")
    add_parser.add_argument("title", help="Task title")
    add_parser.add_argument(
        "--priority",
        choices=["low", "medium", "high"],
        default="medium",
        help="Task priority (default: medium)"
    )

    # List command
    list_parser = subparsers.add_parser("list", help="List tasks")
    list_parser.add_argument(
        "--status",
        choices=["pending", "done"],
        help="Filter tasks by status"
    )

    # Done command
    done_parser = subparsers.add_parser("done", help="Mark a task as done")
    done_parser.add_argument("id", type=int, help="Task ID")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a task")
    delete_parser.add_argument("id", type=int, help="Task ID")

    return parser


def cmd_add(args: argparse.Namespace, repo: TaskRepository) -> int:
    """Handle the 'add' command.

    Args:
        args: Parsed command-line arguments
        repo: TaskRepository instance

    Returns:
        Exit code (0 for success)
    """
    priority = Priority(args.priority)
    task = repo.create_task(title=args.title, priority=priority)
    print(f"Task added: #{task.id} {task.title} [{task.priority.value}]")
    return 0


def cmd_list(args: argparse.Namespace, repo: TaskRepository) -> int:
    """Handle the 'list' command.

    Args:
        args: Parsed command-line arguments
        repo: TaskRepository instance

    Returns:
        Exit code (0 for success)
    """
    status = Status(args.status) if args.status else None
    tasks = repo.get_all_tasks(status=status)

    if not tasks:
        print("No tasks found.")
        return 0

    for task in tasks:
        status_icon = "✓" if task.status == Status.DONE else " "
        print(
            f"[{status_icon}] #{task.id} {task.title} "
            f"[{task.priority.value}] ({task.status.value})"
        )

    return 0


def cmd_done(args: argparse.Namespace, repo: TaskRepository) -> int:
    """Handle the 'done' command.

    Args:
        args: Parsed command-line arguments
        repo: TaskRepository instance

    Returns:
        Exit code (0 for success, 1 for error)
    """
    task = repo.mark_done(args.id)

    if task is None:
        print(f"Error: Task #{args.id} not found.", file=sys.stderr)
        return 1

    print(f"Task #{task.id} marked as done: {task.title}")
    return 0


def cmd_delete(args: argparse.Namespace, repo: TaskRepository) -> int:
    """Handle the 'delete' command.

    Args:
        args: Parsed command-line arguments
        repo: TaskRepository instance

    Returns:
        Exit code (0 for success, 1 for error)
    """
    deleted = repo.delete_task(args.id)

    if not deleted:
        print(f"Error: Task #{args.id} not found.", file=sys.stderr)
        return 1

    print(f"Task #{args.id} deleted.")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for the CLI.

    Args:
        argv: Command-line arguments. If None, uses sys.argv[1:]

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    repo = TaskRepository()

    # Dispatch to command handlers
    commands = {
        "add": cmd_add,
        "list": cmd_list,
        "done": cmd_done,
        "delete": cmd_delete,
    }

    handler = commands.get(args.command)
    if handler is None:
        print(f"Error: Unknown command '{args.command}'", file=sys.stderr)
        return 1

    return handler(args, repo)


if __name__ == "__main__":
    sys.exit(main())
