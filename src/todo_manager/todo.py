"""Business logic: the Task model and the TodoManager that operates on tasks.

This module never prints anything and never touches files. That keeps it
easy to test and lets the CLI (main.py) and storage (storage.py) change
independently.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

MAX_TITLE_LENGTH = 100


class TodoError(Exception):
    """Base class for all task-related errors."""


class TaskNotFoundError(TodoError):
    """Raised when no task exists with the requested ID."""

    def __init__(self, task_id: int):
        super().__init__(f"No task found with ID {task_id}.")
        self.task_id = task_id


class InvalidTitleError(TodoError):
    """Raised when a task title is empty or too long."""


def utc_now() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def clean_title(title: str) -> str:
    """Trim a title and check that it is valid. Returns the trimmed title."""
    title = title.strip()
    if not title:
        raise InvalidTitleError("Task title cannot be empty.")
    if len(title) > MAX_TITLE_LENGTH:
        raise InvalidTitleError(
            f"Task title is too long ({len(title)} characters). "
            f"The maximum is {MAX_TITLE_LENGTH}."
        )
    return title


def parse_timestamp(value: str) -> datetime:
    """Parse an ISO 8601 string into a timezone-aware datetime (UTC if no zone given)."""
    moment = datetime.fromisoformat(value)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment


@dataclass
class Task:
    """A single to-do item."""

    id: int
    title: str
    description: str
    completed: bool
    created_at: datetime
    completed_at: datetime | None = None

    def to_dict(self) -> dict:
        """Convert the task to a JSON-friendly dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "completed": self.completed,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """Build a task from a dictionary. Raises ValueError if the data is invalid."""
        if not isinstance(data.get("id"), int) or isinstance(data.get("id"), bool):
            raise ValueError("Task 'id' must be an integer.")
        if not isinstance(data.get("title"), str):
            raise ValueError("Task 'title' must be text.")
        if not isinstance(data.get("description", ""), str):
            raise ValueError("Task 'description' must be text.")
        if not isinstance(data.get("completed"), bool):
            raise ValueError("Task 'completed' must be true or false.")
        if not isinstance(data.get("created_at"), str):
            raise ValueError("Task 'created_at' must be a timestamp.")
        completed_at = data.get("completed_at")
        if completed_at is not None and not isinstance(completed_at, str):
            raise ValueError("Task 'completed_at' must be a timestamp or null.")

        return cls(
            id=data["id"],
            title=data["title"],
            description=data.get("description", ""),
            completed=data["completed"],
            created_at=parse_timestamp(data["created_at"]),
            completed_at=parse_timestamp(completed_at) if completed_at is not None else None,
        )


class TodoManager:
    """Holds the list of tasks and provides every operation on them."""

    def __init__(self, tasks: list[Task] | None = None, next_id: int = 1):
        self.tasks: list[Task] = tasks if tasks is not None else []
        # Never hand out an ID that is already in use, even if next_id is stale.
        highest_id = max((task.id for task in self.tasks), default=0)
        self.next_id = max(next_id, highest_id + 1)

    def add(self, title: str, description: str = "") -> Task:
        """Create a new task and return it."""
        task = Task(
            id=self.next_id,
            title=clean_title(title),
            description=description.strip(),
            completed=False,
            created_at=utc_now(),
        )
        self.tasks.append(task)
        self.next_id += 1
        return task

    def get(self, task_id: int) -> Task:
        """Return the task with the given ID, or raise TaskNotFoundError."""
        for task in self.tasks:
            if task.id == task_id:
                return task
        raise TaskNotFoundError(task_id)

    def list_tasks(self, status: str = "all") -> list[Task]:
        """Return tasks filtered by status: 'all', 'pending' or 'completed'."""
        if status == "pending":
            return [task for task in self.tasks if not task.completed]
        if status == "completed":
            return [task for task in self.tasks if task.completed]
        return list(self.tasks)

    def update(
        self, task_id: int, title: str | None = None, description: str | None = None
    ) -> Task:
        """Change the title and/or description of a task and return it."""
        task = self.get(task_id)
        # The title is checked first, so an invalid title leaves the task untouched.
        if title is not None:
            task.title = clean_title(title)
        if description is not None:
            task.description = description.strip()
        return task

    def complete(self, task_id: int) -> bool:
        """Mark a task as completed.

        Returns True if the task changed, or False if it was already completed.
        """
        task = self.get(task_id)
        if task.completed:
            return False
        task.completed = True
        task.completed_at = utc_now()
        return True

    def reopen(self, task_id: int) -> bool:
        """Mark a completed task as pending again.

        Returns True if the task changed, or False if it was already open.
        """
        task = self.get(task_id)
        if not task.completed:
            return False
        task.completed = False
        task.completed_at = None
        return True

    def delete(self, task_id: int) -> Task:
        """Remove a task and return it. Its ID is never reused."""
        task = self.get(task_id)
        self.tasks.remove(task)
        return task

    def to_dict(self) -> dict:
        """Convert all data to a JSON-friendly dictionary."""
        return {
            "next_id": self.next_id,
            "tasks": [task.to_dict() for task in self.tasks],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TodoManager":
        """Build a manager from a dictionary. Raises ValueError if the data is invalid."""
        if not isinstance(data, dict):
            raise ValueError("Data must be a JSON object.")
        next_id = data.get("next_id", 1)
        tasks = data.get("tasks", [])
        if not isinstance(next_id, int) or isinstance(next_id, bool) or next_id < 1:
            raise ValueError("'next_id' must be a positive integer.")
        if not isinstance(tasks, list) or not all(isinstance(t, dict) for t in tasks):
            raise ValueError("'tasks' must be a list of task objects.")
        loaded = [Task.from_dict(item) for item in tasks]
        ids = [task.id for task in loaded]
        if len(ids) != len(set(ids)):
            raise ValueError("Task IDs must be unique.")
        return cls(loaded, next_id)
