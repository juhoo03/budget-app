import csv
from datetime import datetime
from collections import defaultdict
from typing import List, Optional, Tuple, Dict, Any
from budget_app.models import Transaction, Budget
from budget_app.storage import StorageManager
from budget_app.decorators import BudgetAppError


class BudgetService:
    def __init__(self, storage: StorageManager):
        self.storage = storage

    def _generate_next_id(self) -> str:
        max_id = 0
        for tx in self.storage.stream_transactions():
            if tx.id.startswith("TX-"):
                try:
                    num = int(tx.id.split("-")[1])
                    if num > max_id:
                        max_id = num
                except (IndexError, ValueError):
                    continue
        return f"TX-{max_id + 1:06d}"

    def validate_date(self, date_str: str) -> None:
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise BudgetAppError(
                "날짜 형식이 올바르지 않습니다 (YYYY-MM-DD).",
                hint="예: 2024-01-15 형식으로 입력하세요."
            )

    def validate_month(self, month_str: str) -> None:
        try:
            datetime.strptime(month_str, "%Y-%m")
        except ValueError:
            raise BudgetAppError(
                "월 형식이 올바르지 않습니다 (YYYY-MM).",
                hint="예: 2024-01 형식으로 입력하세요."
            )

    def add_transaction(
        self, date: str, type_: str, category: str, amount: int, memo: str, tags: List[str]
    ) -> Transaction:
        self.validate_date(date)
        if type_ not in ["income", "expense"]:
            raise BudgetAppError("타입은 income 또는 expense여야 합니다.", hint="income 또는 expense 중 하나를 입력하세요.")
        if amount <= 0:
            raise BudgetAppError("금액은 양의 정수여야 합니다.", hint="1원 이상의 정수 값을 입력하세요.")

        categories = self.storage.get_all_categories()
        if category not in categories:
            raise BudgetAppError(
                f"등록되지 않은 카테고리입니다: '{category}'",
                hint=f"현재 등록된 카테고리: {', '.join(categories)} (신규 추가는 category add 사용)"
            )

        new_id = self._generate_next_id()
        tx = Transaction(
            id=new_id,
            type=type_,
            date=date,
            amount=amount,
            category=category,
            memo=memo.strip(),
            tags=[t.strip() for t in tags if t.strip()],
        )
        self.storage.append_transaction(tx)
        return tx

    def list_transactions(self, limit: Optional[int] = 10) -> List[Transaction]:
        # 제너레이터 스트리밍으로 읽어온 뒤 날짜 기준 최신순 정렬
        all_tx = list(self.storage.stream_transactions())
        all_tx.sort(key=lambda x: (x.date, x.id), reverse=True)
        if limit is not None and limit > 0:
            return all_tx[:limit]
        return all_tx

    def search_transactions(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        category: Optional[str] = None,
        type_: Optional[str] = None,
        query: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> List[Transaction]:
        if from_date:
            self.validate_date(from_date)
        if to_date:
            self.validate_date(to_date)

        results = []
        for tx in self.storage.stream_transactions():
            if from_date and tx.date < from_date:
                continue
            if to_date and tx.date > to_date:
                continue
            if category and tx.category != category:
                continue
            if type_ and tx.type != type_:
                continue
            if query and (query.lower() not in (tx.memo or "").lower()):
                continue
            if tag and (tag not in tx.tags):
                continue
            results.append(tx)

        results.sort(key=lambda x: (x.date, x.id), reverse=True)
        return results

    def delete_transaction(self, tx_id: str) -> None:
        all_tx = list(self.storage.stream_transactions())
        filtered = [tx for tx in all_tx if tx.id != tx_id]
        if len(all_tx) == len(filtered):
            raise BudgetAppError(f"ID가 '{tx_id}'인 거래 내역을 찾을 수 없습니다.", hint="list 명령으로 정확한 ID를 확인하세요.")
        self.storage.overwrite_transactions(filtered)

    def update_transaction(
        self,
        tx_id: str,
        date: Optional[str] = None,
        type_: Optional[str] = None,
        category: Optional[str] = None,
        amount: Optional[int] = None,
        memo: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Transaction:
        all_tx = list(self.storage.stream_transactions())
        target_idx = -1
        for idx, tx in enumerate(all_tx):
            if tx.id == tx_id:
                target_idx = idx
                break

        if target_idx == -1:
            raise BudgetAppError(f"ID가 '{tx_id}'인 거래를 찾을 수 없습니다.", hint="list 명령으로 존재하는 ID를 확인하세요.")

        target = all_tx[target_idx]

        if date:
            self.validate_date(date)
            target.date = date
        if type_:
            if type_ not in ["income", "expense"]:
                raise BudgetAppError("타입은 income 또는 expense여야 합니다.")
            target.type = type_
        if category:
            categories = self.storage.get_all_categories()
            if category not in categories:
                raise BudgetAppError(f"등록되지 않은 카테고리입니다: {category}")
            target.category = category
        if amount is not None:
            if amount <= 0:
                raise BudgetAppError("금액은 양수여야 합니다.")
            target.amount = amount
        if memo is not None:
            target.memo = memo.strip()
        if tags is not None:
            target.tags = [t.strip() for t in tags if t.strip()]

        self.storage.overwrite_transactions(all_tx)
        return target

    def get_summary(self, month: str, top_n: int = 3) -> Dict[str, Any]:
        self.validate_month(month)
        total_income = 0
        total_expense = 0
        category_expenses: Dict[str, int] = defaultdict(int)
        count = 0

        for tx in self.storage.stream_transactions():
            if tx.date.startswith(month):
                count += 1
                if tx.type == "income":
                    total_income += tx.amount
                elif tx.type == "expense":
                    total_expense += tx.amount
                    category_expenses[tx.category] += tx.amount

        if count == 0:
            return {"empty": True, "month": month}

        balance = total_income - total_expense
        sorted_categories = sorted(category_expenses.items(), key=lambda x: x[1], reverse=True)[:top_n]

        budgets = self.storage.get_budgets()
        budget_amount = budgets.get(month)
        usage_rate = None
        is_over = False
        if budget_amount and budget_amount > 0:
            usage_rate = (total_expense / budget_amount) * 100
            is_over = total_expense > budget_amount

        return {
            "empty": False,
            "month": month,
            "total_income": total_income,
            "total_expense": total_expense,
            "balance": balance,
            "top_categories": sorted_categories,
            "budget": budget_amount,
            "usage_rate": usage_rate,
            "is_over": is_over,
        }

    # --- 카테고리 관리 로직 (사용 중 카테고리 삭제 방어) ---
    def add_category(self, name: str) -> None:
        name = name.strip()
        if not name:
            raise BudgetAppError("카테고리명은 비어 있을 수 없습니다.")
        cats = self.storage.get_all_categories()
        if name in cats:
            raise BudgetAppError(f"이미 존재하는 카테고리입니다: {name}")
        cats.append(name)
        self.storage.save_all_categories(cats)

    def remove_category(self, name: str) -> None:
        cats = self.storage.get_all_categories()
        if name not in cats:
            raise BudgetAppError(f"존재하지 않는 카테고리입니다: {name}")

        # 해당 카테고리를 사용하는 내역이 있는지 스트리밍 점검 (삭제 방어 요건 충족)
        for tx in self.storage.stream_transactions():
            if tx.category == name:
                raise BudgetAppError(
                    f"카테고리 '{name}'를 사용하는 거래 내역(예: {tx.id})이 있어 삭제할 수 없습니다.",
                    hint="해당 카테고리를 사용하는 내역을 먼저 다른 카테고리로 변경(update)하거나 삭제하세요."
                )

        cats.remove(name)
        self.storage.save_all_categories(cats)

    # --- CSV Export / Import ---
    def export_to_csv(self, out_path: str, month: Optional[str] = None, from_date: Optional[str] = None, to_date: Optional[str] = None) -> int:
        if not month and not (from_date and to_date):
            raise BudgetAppError(
                "export 시 --month 또는 (--from 및 --to) 중 하나 이상의 조건을 입력해야 합니다.",
                hint="예: export --out export.csv --month 2024-01"
            )

        matched = []
        for tx in self.storage.stream_transactions():
            if month and not tx.date.startswith(month):
                continue
            if from_date and tx.date < from_date:
                continue
            if to_date and tx.date > to_date:
                continue
            matched.append(tx)

        matched.sort(key=lambda x: (x.date, x.id), reverse=True)

        fieldnames = ["date", "type", "category", "amount", "memo", "tags"]
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for tx in matched:
                writer.writerow({
                    "date": tx.date,
                    "type": tx.type,
                    "category": tx.category,
                    "amount": tx.amount,
                    "memo": tx.memo,
                    "tags": ",".join(tx.tags),
                })
        return len(matched)

    def import_from_csv(self, file_path: str) -> Tuple[int, int]:
        try:
            f = open(file_path, "r", encoding="utf-8")
        except FileNotFoundError:
            raise BudgetAppError(f"가져올 CSV 파일을 찾을 수 없습니다: {file_path}", hint="파일 경로를 확인하세요.")

        imported = 0
        skipped = 0
        categories = set(self.storage.get_all_categories())

        with f:
            reader = csv.DictReader(f)
            required_cols = {"date", "type", "category", "amount"}
            if not reader.fieldnames or not required_cols.issubset(set(reader.fieldnames)):
                raise BudgetAppError("CSV 스키마가 올바르지 않습니다. (필수 컬럼: date, type, category, amount)")

            for row in reader:
                try:
                    date = row["date"].strip()
                    self.validate_date(date)
                    t_type = row["type"].strip()
                    if t_type not in ["income", "expense"]:
                        skipped += 1
                        continue
                    cat = row["category"].strip()
                    if cat not in categories:
                        skipped += 1
                        continue
                    amt = int(row["amount"].strip())
                    if amt <= 0:
                        skipped += 1
                        continue
                    memo = row.get("memo", "").strip()
                    raw_tags = row.get("tags", "").strip()
                    tags = [t.strip() for t in raw_tags.split(",") if t.strip()] if raw_tags else []

                    new_id = self._generate_next_id()
                    tx = Transaction(
                        id=new_id,
                        type=t_type,
                        date=date,
                        amount=amt,
                        category=cat,
                        memo=memo,
                        tags=tags
                    )
                    self.storage.append_transaction(tx)
                    imported += 1
                except Exception:
                    skipped += 1

        return imported, skipped