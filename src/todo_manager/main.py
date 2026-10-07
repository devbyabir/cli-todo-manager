"""Command-line interface: parses arguments and shows results with Rich.

This module contains no business logic. It asks TodoManager to do the work,
asks storage to load/save, and decides how to present the result.
"""

import argparse
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from todo_manager import __version__, storage
from todo_manager.storage import StorageError
from todo_manager.todo import InvalidTitleError, Task, TaskNotFoundError, TodoManager

EXIT_OK = 0
EXIT_ERROR = 1

console = Console(highlight=False)
error_console = Console(stderr=True, highlight=False)


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def print_success(message: str) -> None:
    console.print(f"[bold green]Success:[/] {message}")


def print_info(message: str) -> None:
    console.print(f"[yellow]Note:[/] {message}")


def print_warning(message: str) -> None:
    error_console.print(f"[bold yellow]Warning:[/] {message}")


def print_error(message: str, hint: str | None = None) -> None:
    error_console.print(f"[bold red]Error:[/] {message}")
    if hint:
        error_console.print(f"[dim]Hint: {hint}[/]")


def format_time(moment: datetime | None) -> str:
    """Show a UTC timestamp in the user's local time zone, e.g. '07 Oct 2026, 14:30'."""
    if moment is None:
        return "-"
    return moment.astimezone().strftime("%d %b %Y, %H:%M")


def quoted(task: Task) -> str:
    """Return the task title, quoted and safe to embed in Rich markup."""
    return f'"{escape(task.title)}"'


# ---------------------------------------------------------------------------
# Command handlers
# Each handler receives the loaded manager, the parsed arguments and the
# data file path. Handlers that change data save before printing success.
# ---------------------------------------------------------------------------


def cmd_add(manager: TodoManager, args: argparse.Namespace, path: Path) -> int:
    task = manager.add(args.title, args.description)
    storage.save(manager, path)
    print_success(f"Added task [bold]#{task.id}[/]: {quoted(task)}")
    return EXIT_OK


def cmd_list(manager: TodoManager, args: argparse.Namespace, path: Path) -> int:
    tasks = manager.list_tasks(args.status)

    if not manager.tasks:
        console.print(
            Panel(
                'You have no tasks yet.\nAdd one with: [bold]todo add "Buy milk"[/]',
                title="To-Do List",
                border_style="blue",
                expand=False,
            )
        )
        return EXIT_OK
    if not tasks:
        console.print(f"[dim]No {args.status} tasks.[/] Try [bold]todo list --all[/].")
        return EXIT_OK

    titles = {"all": "All Tasks", "pending": "Pending Tasks", "completed": "Completed Tasks"}
    table = Table(title=titles[args.status], title_style="bold", header_style="bold cyan")
    table.add_column("ID", justify="right")
    table.add_column("Status")
    table.add_column("Title", overflow="fold")
    table.add_column("Created")
    table.add_column("Completed")

    for task in tasks:
        if task.completed:
            status = Text("Done", style="green")
            title = Text(task.title, style="dim strike")
        else:
            status = Text("Pending", style="yellow")
            title = Text(task.title)
        table.add_row(
            str(task.id),
            status,
            title,
            format_time(task.created_at),
            format_time(task.completed_at),
        )

    console.print(table)
    done = len(manager.list_tasks("completed"))
    console.print(
        f"[dim]{len(manager.tasks)} total, {done} completed, "
        f"{len(manager.tasks) - done} pending[/]"
    )
    return EXIT_OK


def cmd_view(manager: TodoManager, args: argparse.Namespace, path: Path) -> int:
    task = manager.get(args.id)

    details = Table.grid(padding=(0, 2))
    details.add_column(style="bold cyan")
    details.add_column()
    details.add_row("Title", Text(task.title))
    details.add_row("Description", Text(task.description or "(none)"))
    details.add_row(
        "Status",
        Text("Done", style="green") if task.completed else Text("Pending", style="yellow"),
    )
    details.add_row("Created", format_time(task.created_at))
    details.add_row("Completed", format_time(task.completed_at))

    console.print(
        Panel(
            details,
            title=f"Task #{task.id}",
            border_style="green" if task.completed else "blue",
            expand=False,
        )
    )
    return EXIT_OK


def cmd_edit(manager: TodoManager, args: argparse.Namespace, path: Path) -> int:
    task = manager.update(args.id, title=args.title, description=args.description)
    storage.save(manager, path)
    print_success(f"Updated task [bold]#{task.id}[/]: {quoted(task)}")
    return EXIT_OK


def cmd_complete(manager: TodoManager, args: argparse.Namespace, path: Path) -> int:
    task = manager.get(args.id)
    if not manager.complete(args.id):
        print_info(f"Task #{task.id} {quoted(task)} is already completed.")
        return EXIT_OK
    storage.save(manager, path)
    print_success(f"Completed task [bold]#{task.id}[/]: {quoted(task)}")
    return EXIT_OK


def cmd_reopen(manager: TodoManager, args: argparse.Namespace, path: Path) -> int:
    task = manager.get(args.id)
    if not manager.reopen(args.id):
        print_info(f"Task #{task.id} {quoted(task)} is already open.")
        return EXIT_OK
    storage.save(manager, path)
    print_success(f"Reopened task [bold]#{task.id}[/]: {quoted(task)}")
    return EXIT_OK


def cmd_delete(manager: TodoManager, args: argparse.Namespace, path: Path) -> int:
    task = manager.delete(args.id)
    storage.save(manager, path)
    print_success(f"Deleted task [bold]#{task.id}[/]: {quoted(task)}")
    return EXIT_OK


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def positive_int(value: str) -> int:
    """argparse type for task IDs: a whole number of 1 or more."""
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' is not a valid task ID (use a number like 3)")
    if number < 1:
        raise argparse.ArgumentTypeError(f"'{value}' is not a valid task ID (IDs start at 1)")
    return number


def add_subcommand(subparsers, name: str, help_text: str, examples: str, handler):
    """Create a subcommand with a help description and an examples section."""
    parser = subparsers.add_parser(
        name,
        help=help_text,
        description=help_text,
        epilog=f"examples:\n{examples}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.set_defaults(handler=handler, command_parser=parser)
    return parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="todo",
        description="A simple command-line to-do manager.",
        epilog=(
            "examples:\n"
            '  todo add "Buy milk" -d "2 litres, semi-skimmed"\n'
            "  todo list --pending\n"
            "  todo complete 1\n\n"
            "Run 'todo <command> --help' for details on a command.\n"
            f"Tasks are stored in ~/.todo-manager/tasks.json "
            f"(override with the {storage.ENV_VAR} environment variable)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(title="commands", dest="command", metavar="<command>")

    add = add_subcommand(
        subparsers, "add", "Add a new task.",
        '  todo add "Buy milk"\n  todo add "Write report" -d "Quarterly sales summary"',
        cmd_add,
    )
    add.add_argument("title", help="short title of the task (max 100 characters)")
    add.add_argument("-d", "--description", default="", help="optional longer description")

    list_parser = add_subcommand(
        subparsers, "list", "List tasks (all tasks by default).",
        "  todo list\n  todo list --pending\n  todo list --completed",
        cmd_list,
    )
    filters = list_parser.add_mutually_exclusive_group()
    filters.add_argument(
        "--all", dest="status", action="store_const", const="all", help="show all tasks (default)"
    )
    filters.add_argument(
        "--pending", dest="status", action="store_const", const="pending",
        help="show only tasks that are not done yet",
    )
    filters.add_argument(
        "--completed", dest="status", action="store_const", const="completed",
        help="show only completed tasks",
    )
    list_parser.set_defaults(status="all")

    view = add_subcommand(
        subparsers, "view", "Show all details of one task.", "  todo view 3", cmd_view
    )
    view.add_argument("id", type=positive_int, help="ID of the task")

    edit = add_subcommand(
        subparsers, "edit", "Change the title and/or description of a task.",
        '  todo edit 3 --title "Buy oat milk"\n'
        '  todo edit 3 --description "From the corner shop"\n'
        '  todo edit 3 --description ""      (removes the description)',
        cmd_edit,
    )
    edit.add_argument("id", type=positive_int, help="ID of the task")
    edit.add_argument("-t", "--title", help="new title (max 100 characters)")
    edit.add_argument("-d", "--description", help="new description (use \"\" to clear it)")

    complete = add_subcommand(
        subparsers, "complete", "Mark a task as done.", "  todo complete 3", cmd_complete
    )
    complete.add_argument("id", type=positive_int, help="ID of the task")

    reopen = add_subcommand(
        subparsers, "reopen", "Mark a completed task as not done.", "  todo reopen 3", cmd_reopen
    )
    reopen.add_argument("id", type=positive_int, help="ID of the task")

    delete = add_subcommand(
        subparsers, "delete", "Delete a task permanently.", "  todo delete 3", cmd_delete
    )
    delete.add_argument("id", type=positive_int, help="ID of the task")

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return EXIT_OK
    if args.command == "edit" and args.title is None and args.description is None:
        # Exits with code 2, like every other argparse usage error.
        args.command_parser.error("nothing to change: use --title and/or --description")

    path = storage.get_data_path()
    try:
        manager, backup = storage.load(path)
        if backup:
            print_warning(
                f"The data file was corrupted and could not be read.\n"
                f"Your old data was kept in: {escape(str(backup))}\n"
                f"Starting with an empty task list."
            )
        return args.handler(manager, args, path)
    except TaskNotFoundError as error:
        print_error(str(error), "Run 'todo list' to see the IDs of your tasks.")
    except InvalidTitleError as error:
        print_error(str(error), 'Example: todo add "Buy milk"')
    except StorageError as error:
        print_error(escape(str(error)), f"Check the file permissions or set {storage.ENV_VAR}.")
    return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
