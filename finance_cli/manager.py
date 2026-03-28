from __future__ import annotations

from collections import defaultdict

from finance_cli.models import Transaction, parse_transaction_date
from finance_cli.storage import TransactionStorage


class FinanceManager:
    def __init__(self, storage: TransactionStorage) -> None:
        self.storage = storage
        self.transactions = self.storage.load()
        self.next_id = self._get_next_id()

    def _get_next_id(self) -> int:
        if not self.transactions:
            return 1
        return max(item.transaction_id for item in self.transactions) + 1

    def add_transaction(
        self,
        title: str,
        amount: float,
        category: str,
        transaction_type: str,
        date: str,
        note: str = "",
    ) -> Transaction:
        transaction = Transaction(
            transaction_id=self.next_id,
            title=title,
            amount=amount,
            category=category,
            transaction_type=transaction_type,
            date=date,
            note=note,
        )
        self.transactions.append(transaction)
        self.next_id += 1
        self.save()
        return transaction

    def update_transaction(
        self,
        transaction_id: int,
        title: str,
        amount: float,
        category: str,
        transaction_type: str,
        date: str,
        note: str = "",
    ) -> Transaction:
        transaction = self.get_transaction_by_id(transaction_id)
        if transaction is None:
            raise ValueError("Transaction not found.")

        updated = Transaction(
            transaction_id=transaction_id,
            title=title,
            amount=amount,
            category=category,
            transaction_type=transaction_type,
            date=date,
            note=note,
        )

        index = self.transactions.index(transaction)
        self.transactions[index] = updated
        self.save()
        return updated

    def delete_transaction(self, transaction_id: int) -> bool:
        transaction = self.get_transaction_by_id(transaction_id)
        if transaction is None:
            return False

        self.transactions.remove(transaction)
        self.save()
        return True

    def get_transaction_by_id(self, transaction_id: int) -> Transaction | None:
        for transaction in self.transactions:
            if transaction.transaction_id == transaction_id:
                return transaction
        return None

    def list_transactions(self, sort_key: str = "date", reverse: bool = False) -> list[Transaction]:
        key_map = {
            "date": lambda item: parse_transaction_date(item.date),
            "amount": lambda item: item.amount,
            "category": lambda item: item.category.lower(),
            "type": lambda item: item.transaction_type,
            "title": lambda item: item.title.lower(),
        }
        key_function = key_map.get(sort_key, key_map["date"])
        return sorted(self.transactions, key=key_function, reverse=reverse)

    def search_transactions(self, keyword: str) -> list[Transaction]:
        keyword = keyword.strip().lower()
        return [
            item
            for item in self.transactions
            if keyword in item.title.lower()
            or keyword in item.category.lower()
            or keyword in item.note.lower()
            or keyword in item.transaction_type.lower()
            or keyword in item.date
        ]

    def filter_transactions(self, transaction_type: str | None = None, category: str | None = None) -> list[Transaction]:
        results = self.transactions
        if transaction_type:
            results = [item for item in results if item.transaction_type == transaction_type.lower()]
        if category:
            results = [item for item in results if item.category.lower() == category.lower()]
        return sorted(results, key=lambda item: parse_transaction_date(item.date), reverse=True)

    def monthly_report(self, year: int, month: int) -> dict:
        monthly_items = []
        for item in self.transactions:
            item_date = parse_transaction_date(item.date)
            if item_date.year == year and item_date.month == month:
                monthly_items.append(item)

        income = sum(item.amount for item in monthly_items if item.transaction_type == "income")
        expense = sum(item.amount for item in monthly_items if item.transaction_type == "expense")

        return {
            "year": year,
            "month": month,
            "income": income,
            "expense": expense,
            "balance": income - expense,
            "count": len(monthly_items),
            "transactions": sorted(monthly_items, key=lambda item: parse_transaction_date(item.date)),
        }

    def category_breakdown(self, transaction_type: str = "expense") -> list[dict]:
        totals = defaultdict(float)
        for item in self.transactions:
            if item.transaction_type == transaction_type.lower():
                totals[item.category] += item.amount

        grand_total = sum(totals.values())
        breakdown = []
        for category, total in sorted(totals.items(), key=lambda pair: pair[1], reverse=True):
            percentage = (total / grand_total * 100) if grand_total else 0
            breakdown.append(
                {
                    "category": category,
                    "total": total,
                    "percentage": percentage,
                }
            )
        return breakdown

    def summary(self) -> dict:
        income = sum(item.amount for item in self.transactions if item.transaction_type == "income")
        expense = sum(item.amount for item in self.transactions if item.transaction_type == "expense")
        return {
            "income": income,
            "expense": expense,
            "balance": income - expense,
            "count": len(self.transactions),
        }

    def save(self) -> None:
        self.storage.save(self.transactions)
