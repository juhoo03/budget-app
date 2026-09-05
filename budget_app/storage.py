import os
import json
import shutil
import tempfile
from typing import Generator, List, Dict, Any
from budget_app.models import Transaction, Budget


class StorageManager:
    """3개의 영구 저장 파일(JSONL)을 관리하는 저장소 클래스"""

    # 한국어 기본 카테고리 목록
    DEFAULT_CATEGORIES = ["식비", "교통", "월급", "주거", "여가", "기타"]

    def __init__(self, data_dir: str = "./data"):
        self.data_dir = os.path.abspath(data_dir)
        self.transactions_path = os.path.join(self.data_dir, "transactions.jsonl")
        self.categories_path = os.path.join(self.data_dir, "categories.jsonl")
        self.budgets_path = os.path.join(self.data_dir, "budgets.jsonl")
        self._ensure_storage_ready()

    def _ensure_storage_ready(self) -> None:
        """저장소 폴더 및 파일 초기화 (한국어 기본 카테고리 자동 생성 및 보장)"""
        os.makedirs(self.data_dir, exist_ok=True)

        for path in [self.transactions_path, self.budgets_path]:
            if not os.path.exists(path):
                with open(path, "w", encoding="utf-8") as _:
                    pass

        # 파일이 없거나 비어있는 경우 기본 카테고리 생성
        if not os.path.exists(self.categories_path) or os.path.getsize(self.categories_path) == 0:
            with open(self.categories_path, "w", encoding="utf-8") as f:
                for cat in self.DEFAULT_CATEGORIES:
                    f.write(json.dumps({"name": cat}, ensure_ascii=False) + "\n")
        else:
            # 이미 파일이 있다면 기존 카테고리에 한국어 기본 카테고리 누락분 자동 병합
            current_cats = self.get_all_categories()
            updated = False
            for cat in self.DEFAULT_CATEGORIES:
                if cat not in current_cats:
                    current_cats.append(cat)
                    updated = True
            if updated:
                self.save_all_categories(current_cats)

    def stream_transactions(self) -> Generator[Transaction, None, None]:
        """transactions.jsonl 파일을 한 줄씩 스트리밍하여 Transaction 객체를 생성"""
        if not os.path.exists(self.transactions_path):
            return

        with open(self.transactions_path, "r", encoding="utf-8") as f:
            for line in f:
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
        """임시 파일 작성 -> fsync -> 직전 버전 백업(.bak) -> 원자적 교체(os.replace)"""
        temp_file = tempfile.NamedTemporaryFile("w", dir=self.data_dir, delete=False, encoding="utf-8")
        try:
            for tx in transactions:
                temp_file.write(json.dumps(tx.to_dict(), ensure_ascii=False) + "\n")
            temp_file.flush()
            os.fsync(temp_file.fileno())
            temp_file.close()

            # 원본 직전 버전 백업 (.bak)
            if os.path.exists(self.transactions_path):
                bak_path = self.transactions_path + ".bak"
                shutil.copy2(self.transactions_path, bak_path)

            os.replace(temp_file.name, self.transactions_path)
        except Exception:
            if os.path.exists(temp_file.name):
                os.remove(temp_file.name)
            raise

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