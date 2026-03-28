from __future__ import annotations

from datetime import datetime

from rich import box
from rich.align import Align
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, FloatPrompt, IntPrompt, Prompt
from rich.rule import Rule
from rich.text import Text
from rich.table import Table

from finance_cli.manager import FinanceManager
from finance_cli.models import DATE_FORMAT, parse_transaction_date
from finance_cli.storage import TransactionStorage


class FinanceCLI:
    def __init__(self) -> None:
        self.console = Console()
        self.manager = FinanceManager(TransactionStorage())
        self.running = True

    def run(self) -> None:
        while self.running:
            self._show_header()
            self._show_menu()
            choice = Prompt.ask("[bold cyan]Choose an option[/bold cyan]", default="1").strip()
            self._dispatch(choice)

    def _show_header(self) -> None:
        summary = self.manager.summary()
        self.console.clear()

        title = Text("FINANCE", style="bold white")
        title.stylize("bold bright_cyan", 0, 3)
        title.stylize("bold bright_magenta", 3, len(title))

        subtitle = Text("Personal Finance Tracker", style="dim white")
        header_block = Panel(
            Align.left(Text.assemble(title, "\n", subtitle)),
            box=box.DOUBLE_EDGE,
            border_style="bright_cyan",
            padding=(0, 2),
            expand=False,
        )

        summary_cards = Columns(
            [
                self._metric_panel("Transactions", str(summary["count"]), "bright_cyan"),
                self._metric_panel("Income", self._currency(summary["income"]), "green"),
                self._metric_panel("Expense", self._currency(summary["expense"]), "red"),
                self._metric_panel(
                    "Balance",
                    self._currency(summary["balance"]),
                    self._balance_panel_color(summary["balance"]),
                ),
            ],
            equal=True,
            expand=True,
        )

        self.console.print(header_block)
        self.console.print(summary_cards)
        self.console.print(Rule("[dim]Dashboard[/dim]", style="grey35"))
        self.console.print()

    def _show_menu(self) -> None:
        menu = Table(
            show_header=True,
            header_style="bold white",
            box=box.ROUNDED,
            expand=False,
            pad_edge=True,
            border_style="bright_black",
            row_styles=["none", "dim"],
        )
        menu.add_column("#", justify="center", style="bold bright_cyan", width=4)
        menu.add_column("Action", style="bold white", min_width=24)
        menu.add_column("Focus", style="bright_black", min_width=24)

        for option, label in self._menu_items():
            menu.add_row(option, label, self._menu_focus(option))

        self.console.print(
            Panel(
                menu,
                title="[bold bright_white]Main Menu[/bold bright_white]",
                title_align="left",
                border_style="bright_magenta",
                box=box.SQUARE,
                padding=(0, 1),
                expand=False,
            )
        )
        self.console.print("[dim]Select an option from 1 to 10.[/dim]")

    def _menu_items(self) -> list[tuple[str, str]]:
        return [
            ("1", "Add transaction"),
            ("2", "View all transactions"),
            ("3", "Update transaction"),
            ("4", "Delete transaction"),
            ("5", "Search transactions"),
            ("6", "Filter transactions"),
            ("7", "Monthly report"),
            ("8", "Category breakdown"),
            ("9", "Save data"),
            ("10", "Exit"),
        ]

    def _menu_focus(self, option: str) -> str:
        mapping = {
            "1": "Create new entry",
            "2": "Browse history",
            "3": "Edit record",
            "4": "Remove record",
            "5": "Keyword lookup",
            "6": "Smart filtering",
            "7": "Month snapshot",
            "8": "Category analysis",
            "9": "Store changes",
            "10": "Close app",
        }
        return mapping[option]

    def _dispatch(self, choice: str) -> None:
        actions = {
            "1": self.add_transaction,
            "2": self.view_transactions,
            "3": self.update_transaction,
            "4": self.delete_transaction,
            "5": self.search_transactions,
            "6": self.filter_transactions,
            "7": self.show_monthly_report,
            "8": self.show_category_breakdown,
            "9": self.save_data,
            "10": self.exit_program,
        }

        selected_action = actions.get(choice)
        if selected_action is None:
            self._message("Invalid option. Please choose a valid menu item.", "red")
            return

        selected_action()

    def add_transaction(self) -> None:
        try:
            form_data = self._collect_transaction_form()
            transaction = self.manager.add_transaction(*form_data)
        except ValueError as error:
            self._message(str(error), "red")
            return

        self._message(f"Transaction #{transaction.transaction_id} added successfully.", "green")

    def view_transactions(self) -> None:
        if not self._has_transactions("No transactions found."):
            return

        sort_key = Prompt.ask(
            "Sort by",
            choices=["date", "amount", "category", "type", "title"],
            default="date",
        )
        newest_first = Confirm.ask("Sort descending?", default=True)
        transactions = self.manager.list_transactions(sort_key=sort_key, reverse=newest_first)

        self._render_transactions_table(transactions, title="Transaction History")
        self._pause()

    def update_transaction(self) -> None:
        if not self._has_transactions("There are no transactions to update."):
            return

        transaction = self._prompt_for_existing_transaction("Enter transaction ID to update")
        if transaction is None:
            return

        try:
            form_data = self._collect_transaction_form(transaction)
            self.manager.update_transaction(transaction.transaction_id, *form_data)
        except ValueError as error:
            self._message(str(error), "red")
            return

        self._message("Transaction updated successfully.", "green")

    def delete_transaction(self) -> None:
        if not self._has_transactions("There are no transactions to delete."):
            return

        transaction = self._prompt_for_existing_transaction("Enter transaction ID to delete")
        if transaction is None:
            return

        if not Confirm.ask(f"Delete '{transaction.title}'?", default=False):
            self._message("Deletion cancelled.", "yellow")
            return

        self.manager.delete_transaction(transaction.transaction_id)
        self._message("Transaction deleted successfully.", "green")

    def search_transactions(self) -> None:
        keyword = Prompt.ask("Enter keyword to search")
        matches = self.manager.search_transactions(keyword)

        if not matches:
            self._message("No matching transactions found.", "yellow")
            return

        self._render_transactions_table(matches, title=f"Search Results for '{keyword}'")
        self._pause()

    def filter_transactions(self) -> None:
        transaction_type = Prompt.ask(
            "Filter by type",
            choices=["income", "expense", "all"],
            default="all",
        )
        category = Prompt.ask("Filter by category", default="all").strip()

        selected_type = None if transaction_type == "all" else transaction_type
        selected_category = None if category.lower() == "all" else category
        matches = self.manager.filter_transactions(selected_type, selected_category)

        if not matches:
            self._message("No transactions match the selected filters.", "yellow")
            return

        self._render_transactions_table(matches, title="Filtered Transactions")
        self._pause()

    def show_monthly_report(self) -> None:
        today = datetime.now()
        year = IntPrompt.ask("Enter year", default=today.year)
        month = IntPrompt.ask("Enter month number", default=today.month)

        if not 1 <= month <= 12:
            self._message("Month must be between 1 and 12.", "red")
            return

        report = self.manager.monthly_report(year, month)
        self.console.print(
            Panel(
                Text.assemble(
                    ("Monthly Report", "bold bright_blue"),
                    ("  ", ""),
                    (f"{year}-{month:02d}", "bold white"),
                ),
                border_style="blue",
                box=box.ROUNDED,
                expand=False,
                padding=(0, 1),
            )
        )

        table = Table(
            header_style="bold blue",
            box=box.MINIMAL_DOUBLE_HEAD,
            expand=False,
            pad_edge=True,
        )
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right")
        table.add_row("Transactions", str(report["count"]))
        table.add_row("Total Income", self._currency(report["income"]))
        table.add_row("Total Expense", self._currency(report["expense"]))
        table.add_row("Net Balance", self._currency(report["balance"]))
        self.console.print(table)

        if report["transactions"]:
            self._render_transactions_table(report["transactions"], title="Transactions in Month")

        self._pause()

    def show_category_breakdown(self) -> None:
        transaction_type = Prompt.ask(
            "Show category breakdown for",
            choices=["expense", "income"],
            default="expense",
        )
        breakdown = self.manager.category_breakdown(transaction_type)

        if not breakdown:
            self._message(f"No {transaction_type} data found.", "yellow")
            return

        table = Table(
            header_style="bold green",
            box=box.MINIMAL_DOUBLE_HEAD,
            expand=False,
            pad_edge=True,
        )
        self.console.print(
            Panel(
                f"[bold green]{transaction_type.title()} Category Breakdown[/bold green]",
                border_style="green",
                box=box.ROUNDED,
                expand=False,
                padding=(0, 1),
            )
        )
        table.add_column("Category", style="cyan")
        table.add_column("Total", justify="right")
        table.add_column("Share", justify="right")

        for item in breakdown:
            table.add_row(
                item["category"],
                self._currency(item["total"]),
                f"{item['percentage']:.1f}%",
            )

        self.console.print(table)
        self._pause()

    def save_data(self) -> None:
        self.manager.save()
        self._message("Data saved successfully.", "green")

    def exit_program(self) -> None:
        self.manager.save()
        self.running = False
        self.console.print("\n[bold green]Thank you for using Personal Finance CLI.[/bold green]")

    def _has_transactions(self, empty_message: str) -> bool:
        if self.manager.transactions:
            return True

        self._message(empty_message, "yellow")
        return False

    def _prompt_for_existing_transaction(self, prompt_text: str):
        self._render_transactions_table(self.manager.list_transactions(reverse=True), title="Current Transactions")
        transaction_id = IntPrompt.ask(prompt_text)
        transaction = self.manager.get_transaction_by_id(transaction_id)

        if transaction is None:
            self._message("Transaction ID not found.", "red")

        return transaction

    def _collect_transaction_form(self, existing=None) -> tuple[str, float, str, str, str, str]:
        defaults = {
            "title": getattr(existing, "title", ""),
            "amount": getattr(existing, "amount", 0.0),
            "category": getattr(existing, "category", "General"),
            "transaction_type": getattr(existing, "transaction_type", "expense"),
            "date": getattr(existing, "date", datetime.now().strftime(DATE_FORMAT)),
            "note": getattr(existing, "note", ""),
        }

        title = Prompt.ask("Title", default=defaults["title"])
        amount = FloatPrompt.ask("Amount", default=defaults["amount"])
        category = Prompt.ask("Category", default=defaults["category"])
        transaction_type = self._prompt_for_transaction_type(defaults["transaction_type"])
        date_text = self._prompt_for_valid_date(defaults["date"])
        note = Prompt.ask("Note", default=defaults["note"])

        return title, amount, category, transaction_type, date_text, note

    def _prompt_for_transaction_type(self, default: str) -> str:
        while True:
            transaction_type = Prompt.ask(
                "Type [income/expense]",
                default=default,
            ).strip().lower()
            if transaction_type in {"income", "expense"}:
                return transaction_type
            self.console.print(
                "[bold red]Invalid type:[/bold red] please enter 'income' or 'expense'."
            )

    def _prompt_for_valid_date(self, default: str) -> str:
        while True:
            date_text = Prompt.ask("Date (DD-MM-YYYY)", default=default)
            try:
                self._validate_date(date_text)
                return date_text
            except ValueError as error:
                self.console.print(f"[bold red]Invalid date:[/bold red] {error}")

    def _validate_date(self, date_text: str) -> None:
        parsed_date = parse_transaction_date(date_text)
        if parsed_date > datetime.now().date():
            raise ValueError("Date cannot be later than today.")

    def _render_transactions_table(self, transactions, title: str) -> None:
        table = Table(
            header_style="bold magenta",
            box=box.MINIMAL_DOUBLE_HEAD,
            expand=True,
            pad_edge=True,
            row_styles=["none", "dim"],
        )
        self.console.print(
            Panel(
                f"[bold magenta]{title}[/bold magenta]",
                border_style="magenta",
                box=box.ROUNDED,
                expand=False,
                padding=(0, 1),
            )
        )
        table.add_column("ID", justify="right", style="cyan", width=6)
        table.add_column("Date", style="white", width=12)
        table.add_column("Type", style="yellow", width=8)
        table.add_column("Category", style="green", width=12)
        table.add_column("Title", style="white")
        table.add_column("Amount", justify="right", style="bold")
        table.add_column("Note", style="dim")

        for transaction in transactions:
            amount_style = "green" if transaction.transaction_type == "income" else "red"
            table.add_row(
                str(transaction.transaction_id),
                transaction.date,
                transaction.transaction_type.title(),
                transaction.category,
                transaction.title,
                f"[{amount_style}]{self._currency(transaction.amount)}[/{amount_style}]",
                transaction.note or "-",
            )

        self.console.print(table)

    def _message(self, text: str, style: str) -> None:
        message_styles = {
            "green": ("Success", "green"),
            "red": ("Error", "red"),
            "yellow": ("Notice", "yellow"),
            "cyan": ("Info", "cyan"),
        }
        title, border_style = message_styles.get(style, ("Info", style))
        self.console.print(
            Panel(
                f"[bold]{text}[/bold]",
                title=title,
                title_align="left",
                border_style=border_style,
                box=box.ROUNDED,
                expand=False,
                padding=(0, 1),
            )
        )
        self._pause()

    def _pause(self) -> None:
        Prompt.ask("[dim]Press Enter to continue[/dim]", default="")

    def _currency(self, amount: float) -> str:
        return f"${amount:.2f}"

    def _balance_style(self, amount: float) -> str:
        if amount > 0:
            return "bold green"
        if amount < 0:
            return "bold red"
        return "bold white"

    def _balance_panel_color(self, amount: float) -> str:
        if amount > 0:
            return "green"
        if amount < 0:
            return "red"
        return "bright_black"

    def _metric_panel(self, label: str, value: str, color: str) -> Panel:
        content = Align.center(
            Text.assemble(
                (label, f"bold {color}"),
                "\n",
                (value, "bold white"),
            )
        )
        return Panel(
            content,
            border_style=color,
            box=box.ROUNDED,
            padding=(0, 1),
        )