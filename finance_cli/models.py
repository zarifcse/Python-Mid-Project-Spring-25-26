from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

DATE_FORMAT = "%d-%m-%Y"
LEGACY_DATE_FORMAT = "%Y-%m-%d"


def parse_transaction_date(date_text: str) -> datetime.date:
    date_text = date_text.strip()
    try:
        return datetime.strptime(date_text, DATE_FORMAT).date()
    except ValueError:
        try:
            return datetime.strptime(date_text, LEGACY_DATE_FORMAT).date()
        except ValueError as error:
            raise ValueError("Date must be in DD-MM-YYYY format.") from error


@dataclass
class Transaction:
    transaction_id: int
    title: str
    amount: float
    category: str
    transaction_type: str
    date: str
    note: str = ""

    def __post_init__(self) -> None:
        self.title = self.title.strip()
        self.category = self.category.strip().title()
        self.transaction_type = self.transaction_type.strip().lower()
        self.date = self.date.strip()
        self.note = self.note.strip()

        if self.transaction_type not in {"income", "expense"}:
            raise ValueError("Transaction type must be 'income' or 'expense'.")
        if self.amount <= 0:
            raise ValueError("Amount must be greater than zero.")

        parsed_date = parse_transaction_date(self.date)
        if parsed_date > datetime.now().date():
            raise ValueError("Date cannot be later than today.")
        self.date = parsed_date.strftime(DATE_FORMAT)

    def to_dict(self) -> dict:
        return {
            "transaction_id": self.transaction_id,
            "title": self.title,
            "amount": self.amount,
            "category": self.category,
            "transaction_type": self.transaction_type,
            "date": self.date,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Transaction":
        return cls(
            transaction_id=data["transaction_id"],
            title=data["title"],
            amount=float(data["amount"]),
            category=data["category"],
            transaction_type=data["transaction_type"],
            date=data["date"],
            note=data.get("note", ""),
        )
