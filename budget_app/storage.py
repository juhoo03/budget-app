import json
import os
import shutil
import tempfile
from typing import Callable, Generator, List, Optional

from budget_app.models import Budget, Transaction


class StorageManager:
    """JSONL 기반 파일 영구 저장, 제너레이터 스트리밍 및 원자적 교체를 관리하는 저장소 클래스"""

    DEFAULT_CATEGORIES = ["식비", "교통", "월급", "주거", "여가", "기타"]

    def __init__(self, data_dir: str = "./data") -> None:
        self.data_dir = data_dir
        self.transactions_file = os.path.join(data_dir, "transactions.jsonl")
        self.categories_file = os.path.join(data_dir, "categories.jsonl")
        self.budgets_file = os.path.join(data_dir, "budgets.jsonl")
        self._ensure_storage_initialized()

    def _ensure_storage_initialized(self) -> None:
        """저장 디렉터리 및 3개 영구 저장 파일 초기화"""
        os.makedirs(self.data_dir, exist_ok=True)

        # 1. transactions.jsonl 초기화
        if not os.path.exists(self.transactions_file):
            with open(self.transactions_file, "w", encoding="utf-8"):
                pass

        # 2. budgets.jsonl 초기화
        if not os.path.exists(self.budgets_file):
            with open(self.budgets_file, "w", encoding="utf-8"):
                pass

        # 3. categories.jsonl 초기화 (비어있는 경우 기본 카테고리 자동 적재)
        if (
            not os.path.exists(self.categories_file)
            or os.path.getsize(self.categories_file) == 0
        ):
            with open(self.categories_file, "w", encoding="utf-8") as f:
                for cat in self.DEFAULT_CATEGORIES:
                    f.write(json.dumps({"name": cat}, ensure_ascii=False) + "\n")

    # -------------------------------------------------------------
    # 거래 내역 (Transactions) 스트리밍 및 단건 처리
    # -------------------------------------------------------------
    def stream_transactions(self) -> Generator[Transaction, None, None]:
        """transactions.jsonl 파일을 한 줄씩 지연 평가(Lazy Evaluation)로 로드하는 제너레이터"""
        if not os.path.exists(self.transactions_file):
            return

        with open(self.transactions_file, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    data = json.loads(line_str)
                    yield Transaction.from_dict(data)
                except (json.JSONDecodeError, KeyError):
                    # 손상된 개별 행은 건너뛰어 장애 격리
                    continue

    def get_transaction_by_id(self, tx_id: str) -> Optional[Transaction]:
        """지정된 ID의 거래 내역 1건을 조회 (없으면 None 반환)"""
        for tx in self.stream_transactions():
            if tx.id == tx_id:
                return tx
        return None

    def generate_next_transaction_id(self) -> str:
        """기존 최대 ID 번호를 추적하여 순차적인 고유 ID (TX-XXXXXX) 발급"""
        max_id = 0
        for tx in self.stream_transactions():
            if tx.id.startswith("TX-"):
                try:
                    num_part = int(tx.id.split("-")[1])
                    if num_part > max_id:
                        max_id = num_part
                except (IndexError, ValueError):
                    continue
        return f"TX-{max_id + 1:06d}"

    def append_transaction(self, tx: Transaction) -> None:
        """단건 거래 내역을 파일 끝에 추가 (Append-Only)"""
        with open(self.transactions_file, "a", encoding="utf-8") as f:
            line = json.dumps(tx.to_dict(), ensure_ascii=False)
            f.write(line + "\n")

    def rewrite_transactions_atomic(
        self,
        modifier: Callable[[Generator[Transaction, None, None]], Generator[Transaction, None, None]],
    ) -> None:
        """
        임시 파일 작성 -> fsync -> .bak 백업 -> os.replace 원자적 교체
        수정/삭제 중 비정상 종료 시에도 파일 무결성을 보장
        """
        temp_fd, temp_path = tempfile.mkstemp(dir=self.data_dir, text=True)
        try:
            with open(temp_fd, "w", encoding="utf-8") as temp_file:
                tx_generator = self.stream_transactions()
                for modified_tx in modifier(tx_generator):
                    line = json.dumps(modified_tx.to_dict(), ensure_ascii=False)
                    temp_file.write(line + "\n")
                temp_file.flush()
                os.fsync(temp_file.fileno())

            # 직전 원본을 백업 파일(.bak)로 복사 보존
            bak_file = self.transactions_file + ".bak"
            if os.path.exists(self.transactions_file):
                shutil.copy2(self.transactions_file, bak_file)

            # 원자적 교체 실행
            os.replace(temp_path, self.transactions_file)
        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise

    # -------------------------------------------------------------
    # 카테고리 (Categories) 영구 저장 관리
    # -------------------------------------------------------------
    def get_all_categories(self) -> List[str]:
        """등록된 전체 카테고리명 목록 반환"""
        if not os.path.exists(self.categories_file):
            return []

        categories = []
        with open(self.categories_file, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    data = json.loads(line_str)
                    if "name" in data:
                        categories.append(data["name"])
                except json.JSONDecodeError:
                    continue
        return categories

    def add_category(self, name: str) -> None:
        """단일 카테고리 추가"""
        with open(self.categories_file, "a", encoding="utf-8") as f:
            f.write(json.dumps({"name": name}, ensure_ascii=False) + "\n")

    def remove_category(self, name: str) -> None:
        """카테고리 제거 (임시 파일 원자적 교체 방식 적용)"""
        current_cats = self.get_all_categories()
        updated_cats = [c for c in current_cats if c != name]

        temp_fd, temp_path = tempfile.mkstemp(dir=self.data_dir, text=True)
        try:
            with open(temp_fd, "w", encoding="utf-8") as temp_file:
                for cat in updated_cats:
                    temp_file.write(json.dumps({"name": cat}, ensure_ascii=False) + "\n")
                temp_file.flush()
                os.fsync(temp_file.fileno())

            os.replace(temp_path, self.categories_file)
        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise

    # -------------------------------------------------------------
    # 예산 (Budgets) 영구 저장 관리
    # -------------------------------------------------------------
    def get_budget(self, month_str: str) -> Optional[Budget]:
        """지정된 월(YYYY-MM)의 목표 예산 반환 (없으면 None)"""
        if not os.path.exists(self.budgets_file):
            return None

        with open(self.budgets_file, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    data = json.loads(line_str)
                    budget = Budget.from_dict(data)
                    if budget.month == month_str:
                        return budget
                except (json.JSONDecodeError, KeyError):
                    continue
        return None

    def set_budget(self, new_budget: Budget) -> None:
        """월별 예산 설정 (동일 월 존재 시 갱신, 없으면 추가 - 원자적 교체)"""
        budgets: List[Budget] = []
        replaced = False

        if os.path.exists(self.budgets_file):
            with open(self.budgets_file, "r", encoding="utf-8") as f:
                for line in f:
                    line_str = line.strip()
                    if not line_str:
                        continue
                    try:
                        data = json.loads(line_str)
                        b = Budget.from_dict(data)
                        if b.month == new_budget.month:
                            budgets.append(new_budget)
                            replaced = True
                        else:
                            budgets.append(b)
                    except (json.JSONDecodeError, KeyError):
                        continue

        if not replaced:
            budgets.append(new_budget)

        temp_fd, temp_path = tempfile.mkstemp(dir=self.data_dir, text=True)
        try:
            with open(temp_fd, "w", encoding="utf-8") as temp_file:
                for b in budgets:
                    temp_file.write(json.dumps(b.to_dict(), ensure_ascii=False) + "\n")
                temp_file.flush()
                os.fsync(temp_file.fileno())

            os.replace(temp_path, self.budgets_file)
        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise