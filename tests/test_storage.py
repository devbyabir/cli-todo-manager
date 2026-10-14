"""Tests for JSON persistence in todo_manager.storage.

Every test uses pytest's tmp_path folder, so the real data file in the
user's home directory is never touched.
"""

import json
from pathlib import Path

import pytest

from todo_manager import storage
from todo_manager.todo import TodoManager


@pytest.fixture
def data_file(tmp_path) -> Path:
    return tmp_path / "tasks.json"


def test_missing_file_gives_empty_manager(data_file):
    manager, backup = storage.load(data_file)

    assert manager.tasks == []
    assert manager.next_id == 1
    assert backup is None
    assert not data_file.exists()  # nothing is created until the first save


def test_save_creates_missing_folders(tmp_path):
    path = tmp_path / "nested" / "folder" / "tasks.json"

    storage.save(TodoManager(), path)

    assert json.loads(path.read_text(encoding="utf-8")) == {"next_id": 1, "tasks": []}


def test_save_and_load_round_trip(data_file):
    manager = TodoManager()
    manager.add("Buy milk", "2 litres")
    manager.add("Walk dog")
    manager.complete(2)

    storage.save(manager, data_file)
    loaded, backup = storage.load(data_file)

    assert backup is None
    assert loaded.next_id == manager.next_id
    assert loaded.tasks == manager.tasks


def test_saved_file_has_expected_format(data_file):
    manager = TodoManager()
    manager.add("Buy milk")

    storage.save(manager, data_file)
    data = json.loads(data_file.read_text(encoding="utf-8"))

    assert data["next_id"] == 2
    task = data["tasks"][0]
    assert set(task) == {"id", "title", "description", "completed", "created_at", "completed_at"}
    assert task["created_at"].endswith("+00:00")  # ISO 8601, UTC


def test_id_not_reused_after_delete_and_reload(data_file):
    manager = TodoManager()
    manager.add("First")
    manager.add("Second")
    manager.delete(2)
    storage.save(manager, data_file)

    loaded, _ = storage.load(data_file)

    assert loaded.add("Third").id == 3


def test_save_leaves_no_temporary_files(data_file):
    storage.save(TodoManager(), data_file)
    storage.save(TodoManager(), data_file)

    assert [p.name for p in data_file.parent.iterdir()] == ["tasks.json"]


@pytest.mark.parametrize(
    "content",
    [
        "{ this is not json",
        "[]",
        '{"next_id": "x", "tasks": []}',
        '{"next_id": 2, "tasks": [{"id": 1}]}',
    ],
)
def test_corrupted_file_is_backed_up(data_file, content):
    data_file.write_text(content, encoding="utf-8")

    manager, backup = storage.load(data_file)

    assert manager.tasks == []
    assert backup == data_file.with_name("tasks.json.bak")
    assert backup.read_text(encoding="utf-8") == content  # old data kept
    assert not data_file.exists()


VALID_TASK = (
    '{"id": 1, "title": "A", "description": "", "completed": true, '
    '"created_at": "2026-01-01T00:00:00+00:00", "completed_at": %s}'
)


@pytest.mark.parametrize(
    "content",
    [
        '{"next_id": 2, "tasks": [%s]}' % (VALID_TASK % "123"),
        '{"next_id": 2, "tasks": [%s]}' % (VALID_TASK % "[]"),
        '{"next_id": 2, "tasks": [%s]}' % (VALID_TASK % '"not a date"'),
        '{"next_id": 3, "tasks": [%s, %s]}' % (VALID_TASK % "null", VALID_TASK % "null"),
    ],
    ids=["completed_at-number", "completed_at-list", "completed_at-bad-text", "duplicate-ids"],
)
def test_malformed_task_data_is_backed_up_byte_for_byte(data_file, content):
    original = content.encode("utf-8")
    data_file.write_bytes(original)

    manager, backup = storage.load(data_file)

    assert manager.tasks == []
    assert manager.next_id == 1
    assert backup == data_file.with_name("tasks.json.bak")
    assert backup.read_bytes() == original
    assert not data_file.exists()


def test_existing_backup_is_not_overwritten(data_file):
    old_backup = data_file.with_name("tasks.json.bak")
    old_backup.write_text("older backup", encoding="utf-8")
    data_file.write_text("broken", encoding="utf-8")

    _, backup = storage.load(data_file)

    assert backup == data_file.with_name("tasks.json.bak.1")
    assert old_backup.read_text(encoding="utf-8") == "older backup"
    assert backup.read_text(encoding="utf-8") == "broken"


def test_data_path_uses_environment_variable(monkeypatch, tmp_path):
    custom = tmp_path / "custom.json"
    monkeypatch.setenv(storage.ENV_VAR, str(custom))

    assert storage.get_data_path() == custom


def test_data_path_defaults_to_home_folder(monkeypatch):
    monkeypatch.delenv(storage.ENV_VAR, raising=False)

    assert storage.get_data_path() == Path.home() / ".todo-manager" / "tasks.json"
