from __future__ import annotations

import json
from pathlib import Path

from finance_cli.models import Transaction


class TransactionStorage:
    def __init__(self, file_path: str = "data/transactions.json") -> None:
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> list[Transaction]:
        if not self.file_path.exists():
            return []

        with self.file_path.open("r", encoding="utf-8") as file:
            raw_data = json.load(file)

        return [Transaction.from_dict(item) for item in raw_data]

    def save(self, transactions: list[Transaction]) -> None:
        payload = [transaction.to_dict() for transaction in transactions]
        with self.file_path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2)
