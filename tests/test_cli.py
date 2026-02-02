"""Comprehensive tests for CLI module."""

import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from src.cli import cmd_add, cmd_delete, cmd_done, cmd_list, create_parser, main
from src.models import Priority, Status
from src.repository import TaskRepository
from src.storage import JsonStorage


class TestCLI:
    """Test suite for CLI functionality."""

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

    def test_create_parser(self):
        """Test that parser is created with correct subcommands."""
        parser = create_parser()
        assert parser.prog == "task"

        # Parse help to check subcommands exist
        with pytest.raises(SystemExit):
            parser.parse_args(["--help"])

    def test_parser_add_command(self):
        """Test parsing 'add' command."""
        parser = create_parser()
        args = parser.parse_args(["add", "Test task"])
        assert args.command == "add"
        assert args.title == "Test task"
        assert args.priority == "medium"

    def test_parser_add_command_with_priority(self):
        """Test parsing 'add' command with priority."""
        parser = create_parser()
        args = parser.parse_args(["add", "Urgent task", "--priority", "high"])
        assert args.command == "add"
        assert args.title == "Urgent task"
        assert args.priority == "high"

    def test_parser_list_command(self):
        """Test parsing 'list' command."""
        parser = create_parser()
        args = parser.parse_args(["list"])
        assert args.command == "list"
        assert args.status is None

    def test_parser_list_command_with_status(self):
        """Test parsing 'list' command with status filter."""
        parser = create_parser()
        args = parser.parse_args(["list", "--status", "pending"])
        assert args.command == "list"
        assert args.status == "pending"

    def test_parser_done_command(self):
        """Test parsing 'done' command."""
        parser = create_parser()
        args = parser.parse_args(["done", "42"])
        assert args.command == "done"
        assert args.id == 42

    def test_parser_delete_command(self):
        """Test parsing 'delete' command."""
        parser = create_parser()
        args = parser.parse_args(["delete", "42"])
        assert args.command == "delete"
        assert args.id == 42

    def test_cmd_add(self, repo):
        """Test cmd_add function."""
        parser = create_parser()
        args = parser.parse_args(["add", "Test task", "--priority", "high"])

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_add(args, repo)

        assert result == 0
        output = mock_stdout.getvalue()
        assert "Task added:" in output
        assert "#1" in output
        assert "Test task" in output
        assert "[high]" in output

        # Verify task was created
        tasks = repo.get_all_tasks()
        assert len(tasks) == 1
        assert tasks[0].title == "Test task"
        assert tasks[0].priority == Priority.HIGH

    def test_cmd_list_empty(self, repo):
        """Test cmd_list with no tasks."""
        parser = create_parser()
        args = parser.parse_args(["list"])

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_list(args, repo)

        assert result == 0
        output = mock_stdout.getvalue()
        assert "No tasks found." in output

    def test_cmd_list_with_tasks(self, repo):
        """Test cmd_list with multiple tasks."""
        repo.create_task("Task 1", Priority.HIGH)
        repo.create_task("Task 2", Priority.LOW)

        parser = create_parser()
        args = parser.parse_args(["list"])

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_list(args, repo)

        assert result == 0
        output = mock_stdout.getvalue()
        assert "#1" in output
        assert "Task 1" in output
        assert "[high]" in output
        assert "#2" in output
        assert "Task 2" in output
        assert "[low]" in output

    def test_cmd_list_filter_by_status(self, repo):
        """Test cmd_list with status filter."""
        task1 = repo.create_task("Task 1", Priority.HIGH)
        repo.create_task("Task 2", Priority.LOW)  # Create second task (used in assertion)
        repo.mark_done(task1.id)

        parser = create_parser()
        args = parser.parse_args(["list", "--status", "pending"])

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_list(args, repo)

        assert result == 0
        output = mock_stdout.getvalue()
        assert "Task 2" in output
        assert "Task 1" not in output

    def test_cmd_list_shows_done_status(self, repo):
        """Test cmd_list displays done tasks with checkmark."""
        task = repo.create_task("Task 1", Priority.HIGH)
        repo.mark_done(task.id)

        parser = create_parser()
        args = parser.parse_args(["list"])

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_list(args, repo)

        assert result == 0
        output = mock_stdout.getvalue()
        assert "✓" in output
        assert "(done)" in output

    def test_cmd_done_success(self, repo):
        """Test cmd_done marks task as done."""
        task = repo.create_task("Test task")

        parser = create_parser()
        args = parser.parse_args(["done", str(task.id)])

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_done(args, repo)

        assert result == 0
        output = mock_stdout.getvalue()
        assert f"Task #{task.id} marked as done" in output
        assert "Test task" in output

        # Verify task is marked as done
        updated_task = repo.get_task(task.id)
        assert updated_task.status == Status.DONE

    def test_cmd_done_task_not_found(self, repo):
        """Test cmd_done with non-existent task."""
        parser = create_parser()
        args = parser.parse_args(["done", "999"])

        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            result = cmd_done(args, repo)

        assert result == 1
        output = mock_stderr.getvalue()
        assert "Error:" in output
        assert "Task #999 not found" in output

    def test_cmd_delete_success(self, repo):
        """Test cmd_delete removes task."""
        task = repo.create_task("Test task")

        parser = create_parser()
        args = parser.parse_args(["delete", str(task.id)])

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = cmd_delete(args, repo)

        assert result == 0
        output = mock_stdout.getvalue()
        assert f"Task #{task.id} deleted." in output

        # Verify task is deleted
        deleted_task = repo.get_task(task.id)
        assert deleted_task is None

    def test_cmd_delete_task_not_found(self, repo):
        """Test cmd_delete with non-existent task."""
        parser = create_parser()
        args = parser.parse_args(["delete", "999"])

        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            result = cmd_delete(args, repo)

        assert result == 1
        output = mock_stderr.getvalue()
        assert "Error:" in output
        assert "Task #999 not found" in output

    def test_main_no_command(self, temp_storage):
        """Test main with no command prints help."""
        with patch("src.cli.TaskRepository") as mock_repo:
            mock_repo.return_value = TaskRepository(JsonStorage(temp_storage))
            with patch("sys.stdout", new_callable=StringIO):
                result = main([])

        assert result == 1

    def test_main_add_command(self, temp_storage):
        """Test main with 'add' command."""
        with patch("src.cli.TaskRepository") as mock_repo:
            mock_repo.return_value = TaskRepository(JsonStorage(temp_storage))
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                result = main(["add", "Test task"])

        assert result == 0
        output = mock_stdout.getvalue()
        assert "Task added:" in output

    def test_main_list_command(self, temp_storage):
        """Test main with 'list' command."""
        with patch("src.cli.TaskRepository") as mock_repo:
            mock_repo.return_value = TaskRepository(JsonStorage(temp_storage))
            with patch("sys.stdout", new_callable=StringIO):
                result = main(["list"])

        assert result == 0

    def test_main_done_command(self, temp_storage):
        """Test main with 'done' command."""
        repo = TaskRepository(JsonStorage(temp_storage))
        task = repo.create_task("Test task")

        with patch("src.cli.TaskRepository") as mock_repo:
            mock_repo.return_value = repo
            with patch("sys.stdout", new_callable=StringIO):
                result = main(["done", str(task.id)])

        assert result == 0

    def test_main_delete_command(self, temp_storage):
        """Test main with 'delete' command."""
        repo = TaskRepository(JsonStorage(temp_storage))
        task = repo.create_task("Test task")

        with patch("src.cli.TaskRepository") as mock_repo:
            mock_repo.return_value = repo
            with patch("sys.stdout", new_callable=StringIO):
                result = main(["delete", str(task.id)])

        assert result == 0

    def test_main_uses_default_repo(self, temp_storage):
        """Test that main creates TaskRepository with default storage."""
        with patch("sys.stdout", new_callable=StringIO):
            result = main(["list"])

        assert result == 0

    def test_add_multiple_tasks_sequential_ids(self, repo):
        """Test that adding multiple tasks generates sequential IDs."""
        parser = create_parser()

        for i in range(1, 4):
            args = parser.parse_args(["add", f"Task {i}"])
            with patch("sys.stdout", new_callable=StringIO):
                cmd_add(args, repo)

        tasks = repo.get_all_tasks()
        assert len(tasks) == 3
        assert tasks[0].id == 1
        assert tasks[1].id == 2
        assert tasks[2].id == 3

    def test_priority_choices(self):
        """Test that parser accepts all valid priority values."""
        parser = create_parser()

        for priority in ["low", "medium", "high"]:
            args = parser.parse_args(["add", "Test", "--priority", priority])
            assert args.priority == priority

    def test_status_choices(self):
        """Test that parser accepts all valid status values."""
        parser = create_parser()

        for status in ["pending", "done"]:
            args = parser.parse_args(["list", "--status", status])
            assert args.status == status

    def test_invalid_priority_raises_error(self):
        """Test that invalid priority value raises error."""
        parser = create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(["add", "Test", "--priority", "invalid"])

    def test_invalid_status_raises_error(self):
        """Test that invalid status value raises error."""
        parser = create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(["list", "--status", "invalid"])

    def test_done_requires_id(self):
        """Test that 'done' command requires an ID."""
        parser = create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(["done"])

    def test_delete_requires_id(self):
        """Test that 'delete' command requires an ID."""
        parser = create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(["delete"])

    def test_add_requires_title(self):
        """Test that 'add' command requires a title."""
        parser = create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(["add"])

    def test_task_title_with_spaces(self, repo):
        """Test adding task with title containing spaces."""
        parser = create_parser()
        args = parser.parse_args(["add", "Task with multiple words"])

        with patch("sys.stdout", new_callable=StringIO):
            result = cmd_add(args, repo)

        assert result == 0
        tasks = repo.get_all_tasks()
        assert tasks[0].title == "Task with multiple words"

    def test_task_title_with_special_characters(self, repo):
        """Test adding task with special characters in title."""
        parser = create_parser()
        args = parser.parse_args(["add", "Task: with-special_chars!"])

        with patch("sys.stdout", new_callable=StringIO):
            result = cmd_add(args, repo)

        assert result == 0
        tasks = repo.get_all_tasks()
        assert tasks[0].title == "Task: with-special_chars!"

    def test_list_preserves_task_order(self, repo):
        """Test that list command shows tasks in ID order."""
        repo.create_task("Task 3", Priority.LOW)
        repo.create_task("Task 1", Priority.HIGH)
        repo.create_task("Task 2", Priority.MEDIUM)

        tasks = repo.get_all_tasks()
        assert [t.id for t in tasks] == [1, 2, 3]

    def test_workflow_add_list_done_delete(self, repo):
        """Test complete workflow: add, list, done, delete."""
        # Add task
        parser = create_parser()
        args = parser.parse_args(["add", "Test task"])
        with patch("sys.stdout", new_callable=StringIO):
            cmd_add(args, repo)

        # List tasks
        args = parser.parse_args(["list"])
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            cmd_list(args, repo)
        output = mock_stdout.getvalue()
        assert "Test task" in output
        assert "(pending)" in output

        # Mark done
        args = parser.parse_args(["done", "1"])
        with patch("sys.stdout", new_callable=StringIO):
            cmd_done(args, repo)

        # Verify done
        args = parser.parse_args(["list"])
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            cmd_list(args, repo)
        output = mock_stdout.getvalue()
        assert "✓" in output
        assert "(done)" in output

        # Delete
        args = parser.parse_args(["delete", "1"])
        with patch("sys.stdout", new_callable=StringIO):
            cmd_delete(args, repo)

        # Verify deleted
        args = parser.parse_args(["list"])
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            cmd_list(args, repo)
        output = mock_stdout.getvalue()
        assert "No tasks found." in output
