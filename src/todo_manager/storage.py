"""Persistence: loading and saving tasks as JSON on disk.

Data is stored like this:

    {
        "next_id": 4,
        "tasks": [ {...}, {...} ]
    }
"""

import json
import os
import tempfile
from pathlib import Path

from todo_manager.todo import TodoManager

ENV_VAR = "TODO_DATA_FILE"
DEFAULT_DATA_FILE = Path.home() / ".todo-manager" / "tasks.json"


class StorageError(Exception):
    """Raised when the data file cannot be read or written."""


def get_data_path() -> Path:
    """Return the data file location, honouring the TODO_DATA_FILE variable."""
    override = os.environ.get(ENV_VAR, "").strip()
    if override:
        return Path(override).expanduser()
    return DEFAULT_DATA_FILE


def load(path: Path) -> tuple[TodoManager, Path | None]:
    """Load tasks from `path`.

    Returns a (manager, backup_path) pair:
    - If the file does not exist, an empty manager is returned.
    - If the file is corrupted, it is renamed to a backup (never deleted),
      an empty manager is returned and backup_path tells where the old data went.
    """
    if not path.exists():
        return TodoManager(), None

    try:
        raw = path.read_bytes()
    except OSError as error:
        raise StorageError(f"Could not read data file {path}: {error}") from error

    try:
        return TodoManager.from_dict(json.loads(raw)), None
    except ValueError:  # Also covers JSONDecodeError and UnicodeDecodeError
        return TodoManager(), _back_up(path)


def save(manager: TodoManager, path: Path) -> None:
    """Save tasks to `path` atomically.

    The data is first written to a temporary file in the same folder, then
    moved over the real file in one step. If anything fails half-way, the
    original file is left untouched.
    """
    temp_name = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False
        ) as temp_file:
            temp_name = temp_file.name
            json.dump(manager.to_dict(), temp_file, indent=2)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_name, path)
    except OSError as error:
        if temp_name and os.path.exists(temp_name):
            os.remove(temp_name)
        raise StorageError(f"Could not save data file {path}: {error}") from error


def _back_up(path: Path) -> Path:
    """Rename a corrupted file to tasks.json.bak (or .bak.1, .bak.2, ... if taken)."""
    backup = path.with_name(path.name + ".bak")
    counter = 1
    while backup.exists():
        backup = path.with_name(f"{path.name}.bak.{counter}")
        counter += 1
    try:
        path.rename(backup)
    except OSError as error:
        raise StorageError(
            f"Data file {path} is corrupted and could not be backed up: {error}"
        ) from error
    return backup
