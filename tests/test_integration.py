"""End-to-end integration tests for task-cli.

This module tests the complete workflow using subprocess to run the CLI
as a real user would, ensuring all components work together correctly.
"""

import json
import subprocess
import tempfile
from pathlib import Path

import pytest


class TestIntegration:
    """E2E integration tests for the complete task-cli workflow."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        # Delete the file - CLI will create it
        Path(temp_path).unlink()
        yield temp_path
        # Cleanup
        path = Path(temp_path)
        if path.exists():
            path.unlink()

    def run_cli(self, args, db_path, check=True):
        """Run the CLI with given arguments.

        Args:
            args: List of command arguments
            db_path: Path to the database file
            check: Whether to check for non-zero exit codes

        Returns:
            subprocess.CompletedProcess instance
        """
        # Set environment variable to use custom database path
        env = {"TASK_DB_PATH": db_path}
        result = subprocess.run(
            ["python", "-m", "src"] + args,
            capture_output=True,
            text=True,
            check=False,
            env={**subprocess.os.environ, **env},
            cwd="/workspace"
        )
        if check and result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode, result.args, result.stdout, result.stderr
            )
        return result

    def test_complete_workflow_add_list_done_delete(self, temp_db):
        """Test the complete workflow: add -> list -> done -> delete.

        This is the primary E2E test that covers the main user journey.
        """
        # Step 1: Add a task
        result = self.run_cli(["add", "Buy groceries"], temp_db)
        assert result.returncode == 0
        assert "Task added:" in result.stdout
        assert "#1" in result.stdout
        assert "Buy groceries" in result.stdout

        # Step 2: List tasks (should show the pending task)
        result = self.run_cli(["list"], temp_db)
        assert result.returncode == 0
        assert "Buy groceries" in result.stdout
        assert "#1" in result.stdout
        assert "(pending)" in result.stdout

        # Step 3: Mark task as done
        result = self.run_cli(["done", "1"], temp_db)
        assert result.returncode == 0
        assert "Task #1 marked as done" in result.stdout

        # Step 4: List tasks again (should show done task with checkmark)
        result = self.run_cli(["list"], temp_db)
        assert result.returncode == 0
        assert "Buy groceries" in result.stdout
        assert "✓" in result.stdout
        assert "(done)" in result.stdout

        # Step 5: Delete the task
        result = self.run_cli(["delete", "1"], temp_db)
        assert result.returncode == 0
        assert "Task #1 deleted" in result.stdout

        # Step 6: Verify task is gone
        result = self.run_cli(["list"], temp_db)
        assert result.returncode == 0
        assert "No tasks found." in result.stdout

    def test_add_multiple_tasks_with_different_priorities(self, temp_db):
        """Test adding multiple tasks with different priorities."""
        # Add high priority task
        result = self.run_cli(["add", "Fix critical bug", "--priority", "high"], temp_db)
        assert result.returncode == 0
        assert "[high]" in result.stdout

        # Add low priority task
        result = self.run_cli(["add", "Update docs", "--priority", "low"], temp_db)
        assert result.returncode == 0
        assert "[low]" in result.stdout

        # Add medium priority task (default)
        result = self.run_cli(["add", "Code review"], temp_db)
        assert result.returncode == 0
        assert "[medium]" in result.stdout

        # List all tasks
        result = self.run_cli(["list"], temp_db)
        assert result.returncode == 0
        assert "Fix critical bug" in result.stdout
        assert "Update docs" in result.stdout
        assert "Code review" in result.stdout
        assert "[high]" in result.stdout
        assert "[low]" in result.stdout
        assert "[medium]" in result.stdout

    def test_list_filter_by_status(self, temp_db):
        """Test filtering tasks by status."""
        # Add tasks
        self.run_cli(["add", "Task 1"], temp_db)
        self.run_cli(["add", "Task 2"], temp_db)
        self.run_cli(["add", "Task 3"], temp_db)

        # Mark one task as done
        self.run_cli(["done", "2"], temp_db)

        # List only pending tasks
        result = self.run_cli(["list", "--status", "pending"], temp_db)
        assert result.returncode == 0
        assert "Task 1" in result.stdout
        assert "Task 2" not in result.stdout
        assert "Task 3" in result.stdout

        # List only done tasks
        result = self.run_cli(["list", "--status", "done"], temp_db)
        assert result.returncode == 0
        assert "Task 1" not in result.stdout
        assert "Task 2" in result.stdout
        assert "Task 3" not in result.stdout

    def test_error_done_nonexistent_task(self, temp_db):
        """Test error handling when marking nonexistent task as done."""
        result = self.run_cli(["done", "999"], temp_db, check=False)
        assert result.returncode == 1
        assert "Error:" in result.stderr
        assert "Task #999 not found" in result.stderr

    def test_error_delete_nonexistent_task(self, temp_db):
        """Test error handling when deleting nonexistent task."""
        result = self.run_cli(["delete", "999"], temp_db, check=False)
        assert result.returncode == 1
        assert "Error:" in result.stderr
        assert "Task #999 not found" in result.stderr

    def test_task_title_with_spaces(self, temp_db):
        """Test adding task with spaces in title."""
        result = self.run_cli(["add", "This is a task with spaces"], temp_db)
        assert result.returncode == 0
        assert "This is a task with spaces" in result.stdout

        result = self.run_cli(["list"], temp_db)
        assert "This is a task with spaces" in result.stdout

    def test_task_title_with_special_characters(self, temp_db):
        """Test adding task with special characters."""
        title = "Task: with-special_chars! @#$%"
        result = self.run_cli(["add", title], temp_db)
        assert result.returncode == 0
        assert title in result.stdout

        result = self.run_cli(["list"], temp_db)
        assert title in result.stdout

    def test_empty_list_shows_appropriate_message(self, temp_db):
        """Test that empty task list shows appropriate message."""
        result = self.run_cli(["list"], temp_db)
        assert result.returncode == 0
        assert "No tasks found." in result.stdout

    def test_no_command_shows_help(self, temp_db):
        """Test that running CLI with no command shows help."""
        result = self.run_cli([], temp_db, check=False)
        assert result.returncode == 1
        # Help text should be shown
        assert "usage:" in result.stdout or "task" in result.stdout

    def test_persistence_across_cli_invocations(self, temp_db):
        """Test that data persists across multiple CLI invocations.

        This verifies that the storage layer correctly saves and loads data.
        """
        # Add task in first invocation
        self.run_cli(["add", "Persistent task"], temp_db)

        # Verify it exists in second invocation
        result = self.run_cli(["list"], temp_db)
        assert "Persistent task" in result.stdout

        # Mark done in third invocation
        self.run_cli(["done", "1"], temp_db)

        # Verify status in fourth invocation
        result = self.run_cli(["list"], temp_db)
        assert "(done)" in result.stdout

        # Verify database file was created and contains valid JSON
        db_file = Path(temp_db)
        assert db_file.exists()
        with open(db_file, 'r') as f:
            data = json.load(f)
            assert isinstance(data, dict)
            assert "1" in data

    def test_sequential_ids_after_deletion(self, temp_db):
        """Test that IDs continue sequentially even after deletions."""
        # Add three tasks
        self.run_cli(["add", "Task 1"], temp_db)
        self.run_cli(["add", "Task 2"], temp_db)
        self.run_cli(["add", "Task 3"], temp_db)

        # Delete task 2
        self.run_cli(["delete", "2"], temp_db)

        # Add a new task - should get ID 4, not 2
        result = self.run_cli(["add", "Task 4"], temp_db)
        assert "#4" in result.stdout

        # List should show tasks 1, 3, 4
        result = self.run_cli(["list"], temp_db)
        assert "Task 1" in result.stdout
        assert "Task 2" not in result.stdout
        assert "Task 3" in result.stdout
        assert "Task 4" in result.stdout

    def test_mark_already_done_task_as_done(self, temp_db):
        """Test marking an already done task as done (idempotent)."""
        # Add and mark task as done
        self.run_cli(["add", "Task"], temp_db)
        self.run_cli(["done", "1"], temp_db)

        # Mark it as done again
        result = self.run_cli(["done", "1"], temp_db)
        assert result.returncode == 0
        assert "marked as done" in result.stdout

    def test_complex_workflow_multiple_tasks(self, temp_db):
        """Test a complex workflow with multiple tasks and operations.

        This simulates a realistic usage scenario with many operations.
        """
        # Add several tasks
        self.run_cli(["add", "Write tests", "--priority", "high"], temp_db)
        self.run_cli(["add", "Fix bug #123", "--priority", "high"], temp_db)
        self.run_cli(["add", "Update README", "--priority", "low"], temp_db)
        self.run_cli(["add", "Code review PR #456"], temp_db)
        self.run_cli(["add", "Deploy to staging"], temp_db)

        # Complete some tasks
        self.run_cli(["done", "1"], temp_db)
        self.run_cli(["done", "3"], temp_db)

        # Verify pending tasks only
        result = self.run_cli(["list", "--status", "pending"], temp_db)
        assert "Fix bug #123" in result.stdout
        assert "Code review PR #456" in result.stdout
        assert "Deploy to staging" in result.stdout
        assert "Write tests" not in result.stdout
        assert "Update README" not in result.stdout

        # Verify done tasks only
        result = self.run_cli(["list", "--status", "done"], temp_db)
        assert "Write tests" in result.stdout
        assert "Update README" in result.stdout
        assert "Fix bug #123" not in result.stdout

        # Delete a done task
        self.run_cli(["delete", "1"], temp_db)

        # Verify it's gone
        result = self.run_cli(["list"], temp_db)
        assert "Write tests" not in result.stdout

        # Add a new task
        self.run_cli(["add", "New feature"], temp_db)

        # Final list should have 5 tasks total (deleted 1, added 1)
        result = self.run_cli(["list"], temp_db)
        lines_with_task_id = [line for line in result.stdout.split('\n') if '#' in line]
        assert len(lines_with_task_id) == 5

    def test_invalid_priority_shows_error(self, temp_db):
        """Test that invalid priority value shows error."""
        result = self.run_cli(["add", "Task", "--priority", "invalid"], temp_db, check=False)
        assert result.returncode != 0
        # Either in stderr or stdout depending on argparse behavior
        assert "invalid" in result.stderr.lower() or "invalid" in result.stdout.lower()

    def test_invalid_status_filter_shows_error(self, temp_db):
        """Test that invalid status filter shows error."""
        result = self.run_cli(["list", "--status", "invalid"], temp_db, check=False)
        assert result.returncode != 0
        assert "invalid" in result.stderr.lower() or "invalid" in result.stdout.lower()

    def test_done_command_requires_id(self, temp_db):
        """Test that done command requires an ID argument."""
        result = self.run_cli(["done"], temp_db, check=False)
        assert result.returncode != 0

    def test_delete_command_requires_id(self, temp_db):
        """Test that delete command requires an ID argument."""
        result = self.run_cli(["delete"], temp_db, check=False)
        assert result.returncode != 0

    def test_add_command_requires_title(self, temp_db):
        """Test that add command requires a title argument."""
        result = self.run_cli(["add"], temp_db, check=False)
        assert result.returncode != 0

    def test_database_file_creation(self, temp_db):
        """Test that database file is created on first add."""
        db_file = Path(temp_db)
        assert not db_file.exists()

        # Add first task
        self.run_cli(["add", "First task"], temp_db)

        # Database file should now exist
        assert db_file.exists()

        # File should contain valid JSON
        with open(db_file, 'r') as f:
            data = json.load(f)
            assert isinstance(data, dict)
            assert len(data) == 1
