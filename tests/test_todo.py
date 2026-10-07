"""Tests for the business logic in todo_manager.todo."""

import pytest

from todo_manager.todo import (
    MAX_TITLE_LENGTH,
    InvalidTitleError,
    Task,
    TaskNotFoundError,
    TodoManager,
)


@pytest.fixture
def manager() -> TodoManager:
    return TodoManager()


# --- Creating tasks ---------------------------------------------------------


def test_add_creates_pending_task(manager):
    task = manager.add("Buy milk", "2 litres")

    assert task.id == 1
    assert task.title == "Buy milk"
    assert task.description == "2 litres"
    assert task.completed is False
    assert task.completed_at is None
    assert task.created_at.tzinfo is not None
    assert manager.tasks == [task]


def test_add_trims_title_and_defaults_description(manager):
    task = manager.add("   Buy milk   ")

    assert task.title == "Buy milk"
    assert task.description == ""


def test_add_assigns_sequential_ids(manager):
    first = manager.add("First")
    second = manager.add("Second")

    assert (first.id, second.id) == (1, 2)
    assert manager.next_id == 3


# --- Invalid titles ---------------------------------------------------------


@pytest.mark.parametrize("title", ["", "   ", "\t\n"])
def test_add_rejects_empty_title(manager, title):
    with pytest.raises(InvalidTitleError):
        manager.add(title)
    assert manager.tasks == []
    assert manager.next_id == 1


def test_add_rejects_title_that_is_too_long(manager):
    with pytest.raises(InvalidTitleError):
        manager.add("x" * (MAX_TITLE_LENGTH + 1))


def test_add_accepts_title_at_maximum_length(manager):
    task = manager.add("x" * MAX_TITLE_LENGTH)
    assert len(task.title) == MAX_TITLE_LENGTH


# --- Updating tasks ---------------------------------------------------------


def test_update_title(manager):
    manager.add("Old title", "Keep me")

    task = manager.update(1, title="  New title  ")

    assert task.title == "New title"
    assert task.description == "Keep me"


def test_update_description_only(manager):
    manager.add("Title", "Old")

    task = manager.update(1, description="New")

    assert task.title == "Title"
    assert task.description == "New"


def test_update_can_clear_description(manager):
    manager.add("Title", "Old")
    assert manager.update(1, description="").description == ""


def test_update_with_invalid_title_changes_nothing(manager):
    manager.add("Title", "Old")

    with pytest.raises(InvalidTitleError):
        manager.update(1, title="   ", description="New")

    task = manager.get(1)
    assert task.title == "Title"
    assert task.description == "Old"


# --- Completing and reopening ----------------------------------------------


def test_complete_marks_task_done(manager):
    manager.add("Task")

    assert manager.complete(1) is True

    task = manager.get(1)
    assert task.completed is True
    assert task.completed_at is not None
    assert task.completed_at.tzinfo is not None


def test_complete_already_completed_task_returns_false(manager):
    manager.add("Task")
    manager.complete(1)
    first_completed_at = manager.get(1).completed_at

    assert manager.complete(1) is False
    assert manager.get(1).completed_at == first_completed_at


def test_reopen_clears_completion(manager):
    manager.add("Task")
    manager.complete(1)

    assert manager.reopen(1) is True

    task = manager.get(1)
    assert task.completed is False
    assert task.completed_at is None


def test_reopen_open_task_returns_false(manager):
    manager.add("Task")
    assert manager.reopen(1) is False


# --- Deleting tasks and IDs ------------------------------------------------


def test_delete_removes_task(manager):
    manager.add("Task")

    deleted = manager.delete(1)

    assert deleted.title == "Task"
    assert manager.tasks == []


def test_id_not_reused_after_deletion(manager):
    manager.add("First")
    manager.add("Second")
    manager.delete(2)

    assert manager.next_id == 3
    assert manager.add("Third").id == 3


def test_next_id_never_below_existing_ids():
    task = Task.from_dict(
        {"id": 7, "title": "T", "completed": False, "created_at": "2026-01-01T00:00:00+00:00"}
    )
    assert TodoManager([task], next_id=1).next_id == 8


# --- Invalid IDs ------------------------------------------------------------


@pytest.mark.parametrize("operation", ["get", "complete", "reopen", "delete"])
def test_unknown_id_raises(manager, operation):
    manager.add("Task")
    with pytest.raises(TaskNotFoundError):
        getattr(manager, operation)(99)


def test_update_unknown_id_raises(manager):
    with pytest.raises(TaskNotFoundError):
        manager.update(1, title="New")


# --- Filtering --------------------------------------------------------------


def test_list_tasks_filters_by_status(manager):
    manager.add("Open")
    manager.add("Done")
    manager.complete(2)

    assert [t.title for t in manager.list_tasks()] == ["Open", "Done"]
    assert [t.title for t in manager.list_tasks("pending")] == ["Open"]
    assert [t.title for t in manager.list_tasks("completed")] == ["Done"]


# --- Dictionary conversion --------------------------------------------------


def test_to_dict_and_from_dict_round_trip(manager):
    manager.add("One", "desc")
    manager.add("Two")
    manager.complete(2)
    manager.delete(1)

    restored = TodoManager.from_dict(manager.to_dict())

    assert restored.next_id == 3
    assert restored.tasks == manager.tasks


def test_from_dict_rejects_invalid_task():
    with pytest.raises(ValueError):
        TodoManager.from_dict({"next_id": 2, "tasks": [{"id": "one"}]})
