from dataclasses import dataclass, field, asdict
from typing import List, Optional
import json


@dataclass
class Transaction:
    id: str
    type: str  # "income" 또는 "expense"
    date: str  # "YYYY-MM-DD"
    amount: int  # 양수
    category: str
    memo: Optional[str] = ""
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Transaction":
        return cls(
            id=data["id"],
            type=data["type"],
            date=data["date"],
            amount=int(data["amount"]),
            category=data["category"],
            memo=data.get("memo", ""),
            tags=data.get("tags", []),
        )


@dataclass
class Budget:
    month: str  # "YYYY-MM"
    amount: int

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Budget":
        return cls(month=data["month"], amount=int(data["amount"]))