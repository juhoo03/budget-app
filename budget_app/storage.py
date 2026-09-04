import os
import json
import tempfile
from typing import Generator, List, Dict, Any, Optional
from budget_app.models import Transaction, Budget


class StorageManager:
    """3개의 영구 저장 파일(JSONL)을 관리하는 클래스"""

    def __init__(self, data_dir: str = "./data"):
        self.data_dir = os.path.abspath(data_dir)
        self.transactions_path = os.path.join(self.data_dir, "transactions.jsonl")
        self.categories_path = os.path.join(self.data_dir, "categories.jsonl")
        self.budgets_path = os.path.join(self.data_dir, "budgets.jsonl")
        self._ensure_storage_ready()

    def _ensure_storage_ready(self) -> None:
        """저장소 폴더 및 파일 초기화 (카테고리 기본값 자동 생성 - 안 A)"""
        os.makedirs(self.data_dir, exist_ok=True)

        for path in [self.transactions_path, self.budgets_path]:
            if not os.path.exists(path):
                with open(path, "w", encoding="utf-8") as _:
                    pass

        if not os.path.exists(self.categories_path) or os.path.getsize(self.categories_path) == 0:
            default_categories = ["food", "transport", "salary", "rent", "leisure", "etc"]
            with open(self.categories_path, "w", encoding="utf-8") as f:
                for cat in default_categories:
                    f.write(json.dumps({"name": cat}, ensure_ascii=False) + "\n")

    # --- 스트리밍 읽기 (제너레이터) ---
    def stream_transactions(self) -> Generator[Transaction, None, None]:
        """transactions.jsonl 파일을 한 줄씩 스트리밍하여 Transaction 객체를 생성"""
        if not os.path.exists(self.transactions_path):
            return

        with open(self.transactions_path, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                clean_line = line.strip()
                if not clean_line:
                    continue
                try:
                    data = json.loads(clean_line)
                    yield Transaction.from_dict(data)
                except Exception:
                    continue

    def append_transaction(self, tx: Transaction) -> None:
        with open(self.transactions_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(tx.to_dict(), ensure_ascii=False) + "\n")

    def overwrite_transactions(self, transactions: List[Transaction]) -> None:
        """원자적(Atomic) 교체 기법을 통한 파일 덮어쓰기 (보너스 과제 4 충족)"""
        temp_file = tempfile.NamedTemporaryFile("w", dir=self.data_dir, delete=False, encoding="utf-8")
        try:
            for tx in transactions:
                temp_file.write(json.dumps(tx.to_dict(), ensure_ascii=False) + "\n")
            temp_file.flush()
            os.fsync(temp_file.fileno())
            temp_file.close()
            os.replace(temp_file.name, self.transactions_path)
        except Exception:
            if os.path.exists(temp_file.name):
                os.remove(temp_file.name)
            raise

    # --- 카테고리 관리 ---
    def get_all_categories(self) -> List[str]:
        categories = []
        if os.path.exists(self.categories_path):
            with open(self.categories_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            categories.append(json.loads(line)["name"])
                        except Exception:
                            continue
        return categories

    def save_all_categories(self, categories: List[str]) -> None:
        temp_file = tempfile.NamedTemporaryFile("w", dir=self.data_dir, delete=False, encoding="utf-8")
        try:
            for cat in sorted(set(categories)):
                temp_file.write(json.dumps({"name": cat}, ensure_ascii=False) + "\n")
            temp_file.flush()
            os.fsync(temp_file.fileno())
            temp_file.close()
            os.replace(temp_file.name, self.categories_path)
        except Exception:
            if os.path.exists(temp_file.name):
                os.remove(temp_file.name)
            raise

    # --- 예산 관리 ---
    def get_budgets(self) -> Dict[str, int]:
        budgets = {}
        if os.path.exists(self.budgets_path):
            with open(self.budgets_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            item = json.loads(line)
                            budgets[item["month"]] = int(item["amount"])
                        except Exception:
                            continue
        return budgets

    def set_budget(self, month: str, amount: int) -> None:
        budgets = self.get_budgets()
        budgets[month] = amount
        temp_file = tempfile.NamedTemporaryFile("w", dir=self.data_dir, delete=False, encoding="utf-8")
        try:
            for m, a in budgets.items():
                temp_file.write(json.dumps({"month": m, "amount": a}, ensure_ascii=False) + "\n")
            temp_file.flush()
            os.fsync(temp_file.fileno())
            temp_file.close()
            os.replace(temp_file.name, self.budgets_path)
        except Exception:
            if os.path.exists(temp_file.name):
                os.remove(temp_file.name)
            raise