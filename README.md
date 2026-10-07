# CLI To-Do Manager

A simple, polished command-line to-do manager written in Python.

You can add tasks, check them off, edit them and delete them, all from your
terminal. Tasks are saved on your computer, so they are still there the next
time you open a terminal.

The project is also meant to show good software engineering practice in a
small codebase: a clear separation of concerns, readable code, automated tests
and documentation.

---

## Features

- **Add** tasks with a title and an optional description
- **List** tasks as a clear, colour-coded table, with filters for pending or completed tasks
- **View** all the details of a single task
- **Edit** a task's title and/or description
- **Complete** and **reopen** tasks
- **Delete** tasks (IDs are never reused, so `#3` always means the same task)
- **Safe storage**:
  - data is written atomically, so a crash mid-save cannot leave a half-written file
  - a corrupted data file is backed up, never deleted
- **Friendly output** with colours, tables, helpful hints and clear error messages
- Timestamps are stored in UTC and shown in **your local time**

---

## Demo

```text
$ todo add "Buy milk" -d "2 litres, semi-skimmed"
Success: Added task #1: "Buy milk"

$ todo add "Write report"
Success: Added task #2: "Write report"

$ todo complete 1
Success: Completed task #1: "Buy milk"

$ todo list
                              All Tasks
┏━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┓
┃ ID ┃ Status  ┃ Title        ┃ Created            ┃ Completed          ┃
┡━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━┩
│  1 │ Done    │ Buy milk     │ 07 Oct 2026, 11:34 │ 07 Oct 2026, 11:35 │
│  2 │ Pending │ Write report │ 07 Oct 2026, 11:34 │ -                  │
└────┴─────────┴──────────────┴────────────────────┴────────────────────┘
2 total, 1 completed, 1 pending

$ todo view 1
╭────────────── Task #1 ──────────────╮
│ Title        Buy milk               │
│ Description  2 litres, semi-skimmed │
│ Status       Done                   │
│ Created      07 Oct 2026, 11:34     │
│ Completed    07 Oct 2026, 11:35     │
╰─────────────────────────────────────╯

$ todo complete 1
Note: Task #1 "Buy milk" is already completed.

$ todo view 42
Error: No task found with ID 42.
Hint: Run 'todo list' to see the IDs of your tasks.
```

In a real terminal the output is coloured. Completed tasks are shown in dim,
struck-through text, statuses are green or yellow, and errors are red.

---

## Installation

You need **Python 3.12 or newer** and **git**.

**1. Clone the repository**

```bash
git clone <repository-url>
cd cli-todo-manager
```

**2. Create and activate a virtual environment**

```bash
python -m venv .venv
```

Then activate it:

| System                  | Command                       |
| ----------------------- | ----------------------------- |
| Windows (PowerShell)    | `.venv\Scripts\Activate.ps1`  |
| Windows (Command Prompt)| `.venv\Scripts\activate.bat`  |
| macOS / Linux           | `source .venv/bin/activate`   |

**3. Install the project together with the test tools**

```bash
pip install -e ".[dev]"
```

This installs the `todo` command. Check that it works:

```bash
todo --help
```

> If you only want to use the app and do not need to run the tests,
> `pip install -e .` is enough.

---

## Usage

| Command                                   | What it does                              |
| ----------------------------------------- | ----------------------------------------- |
| `todo add "Title"`                        | Add a task                                |
| `todo add "Title" -d "Description"`       | Add a task with a description             |
| `todo list`                               | Show all tasks                            |
| `todo list --pending`                     | Show only tasks that are not done         |
| `todo list --completed`                   | Show only completed tasks                 |
| `todo list --all`                         | Show all tasks (same as `todo list`)      |
| `todo view <id>`                          | Show every detail of one task             |
| `todo edit <id> --title "New title"`      | Change a task's title                     |
| `todo edit <id> --description "New text"` | Change a task's description (`""` clears it) |
| `todo complete <id>`                      | Mark a task as done                       |
| `todo reopen <id>`                        | Mark a done task as not done              |
| `todo delete <id>`                        | Delete a task permanently                 |
| `todo --help`                             | Show help (also `todo <command> --help`)  |

### Rules

- Titles are trimmed, cannot be empty and can be at most 100 characters long.
- `--pending`, `--completed` and `--all` cannot be combined.
- `todo edit` needs at least one of `--title` or `--description`.
- Completing a task that is already done, or reopening one that is already open,
  is harmless. You get a yellow note and nothing changes.

### Exit codes

| Code | Meaning                                                       |
| ---- | ------------------------------------------------------------- |
| `0`  | Success                                                       |
| `1`  | Application error, such as an unknown task ID, an invalid title or a file problem |
| `2`  | Invalid command-line usage, such as a missing argument or an unknown option |

### Where are my tasks stored?

By default tasks are saved in `~/.todo-manager/tasks.json` in your home folder.
This means the command works the same from any directory.

To use a different file, set the `TODO_DATA_FILE` environment variable:

```bash
# macOS / Linux
export TODO_DATA_FILE="$HOME/work-tasks.json"

# Windows (PowerShell)
$env:TODO_DATA_FILE = "$HOME\work-tasks.json"
```

If the data file is ever damaged and cannot be read, it is renamed to
`tasks.json.bak` (or `tasks.json.bak.1`, `.bak.2`, ... if a backup already
exists). You see a warning, and the app starts with an empty list. Your old
data is never deleted.

---

## Project structure

```text
cli-todo-manager/
├── src/
│   └── todo_manager/
│       ├── __init__.py    # Package marker and version number
│       ├── main.py        # CLI: argument parsing, Rich output, exit codes
│       ├── todo.py        # Business logic: Task dataclass and TodoManager
│       └── storage.py     # Loading and saving JSON (atomic writes, backups)
├── tests/
│   ├── test_todo.py       # Tests for the business logic
│   └── test_storage.py    # Tests for loading and saving
├── pyproject.toml         # Package metadata, dependencies and `todo` command
├── README.md
└── .gitignore
```

Each module has one job:

- **`todo.py`** knows the rules: valid titles, ID assignment, completing and
  reopening. It never prints and never touches files, which makes it easy to test.
- **`storage.py`** only reads and writes the JSON file.
- **`main.py`** is the only place that talks to the user. It turns commands
  into calls to `TodoManager` and shows the results with
  [Rich](https://github.com/Textualize/rich).

The data file looks like this:

```json
{
  "next_id": 3,
  "tasks": [
    {
      "id": 1,
      "title": "Buy milk",
      "description": "2 litres, semi-skimmed",
      "completed": true,
      "created_at": "2026-10-07T03:34:02.905441+00:00",
      "completed_at": "2026-10-07T03:35:10.112233+00:00"
    }
  ]
}
```

`next_id` is saved separately so that a deleted task's ID is never handed out again.

---

## Running tests

With the virtual environment activated and dev dependencies installed:

```bash
pytest
```

The tests use temporary folders and never touch your real task file.

---

## Limitations

- Single user and single machine. There is no syncing between devices.
- Not designed for several `todo` commands running at exactly the same time.
  If that happens, the last save wins.
- Tasks have only a title and a description. There are no due dates, priorities or tags.
- All tasks are loaded into memory, which is fine for personal use but not for very large lists.

## Future improvements

Ideas that are deliberately **not** implemented, to keep the project small:

- Due dates and priorities, with sorting
- Tags or projects for grouping tasks
- Searching tasks by keyword
- An `undo` for the last delete
- Exporting tasks to CSV or Markdown
- Continuous integration (for example GitHub Actions) to run the tests on every push
