import csv
from collections import defaultdict
from datetime import datetime
import heapq
from typing import Any, Dict, Generator, List, Optional, Tuple

from budget_app.models import Budget, Transaction
from budget_app.storage import StorageManager
from budget_app.decorators import BudgetAppError, log_execution, measure_time


class BudgetService:
    """가계부 핵심 비즈니스 로직, 검증 및 집계를 담당하는 서비스 클래스"""

    def __init__(self, storage: StorageManager) -> None:
        self.storage = storage

    # -------------------------------------------------------------
    # 1. 내부 유효성 검증 헬퍼 메서드
    # -------------------------------------------------------------
    def _validate_date(self, date_str: str) -> None:
        """YYYY-MM-DD 형식 및 유효 달력 날짜 검증"""
        try:
            datetime.strptime(date_str.strip(), "%Y-%m-%d")
        except ValueError:
            raise BudgetAppError(
                f"날짜 형식이 올바르지 않습니다: '{date_str}'",
                hint="YYYY-MM-DD 형식의 실제 달력 날짜(예: 2026-09-05)를 입력하세요.",
            )

    def _validate_month(self, month_str: str) -> None:
        """YYYY-MM 형식 검증"""
        try:
            datetime.strptime(month_str.strip(), "%Y-%m")
        except ValueError:
            raise BudgetAppError(
                f"월 형식이 올바르지 않습니다: '{month_str}'",
                hint="YYYY-MM 형식(예: 2026-09)으로 입력하세요.",
            )

    def _validate_type(self, type_str: str) -> None:
        """income / expense 타입 검증"""
        if type_str not in ["income", "expense"]:
            raise BudgetAppError(
                f"유효하지 않은 거래 타입입니다: '{type_str}'",
                hint="'income' 또는 'expense' 중 하나를 지정하세요.",
            )

    def _validate_amount(self, amount: int) -> None:
        """금액 양의 정수 검증"""
        if not isinstance(amount, int) or amount <= 0:
            raise BudgetAppError(
                f"금액은 0보다 큰 정수여야 합니다: '{amount}'",
                hint="1 이상의 숫자(예: 15000)를 입력하세요.",
            )

    def _validate_category(self, category: str) -> None:
        """등록된 카테고리 여부 검증"""
        registered = self.storage.get_all_categories()
        if category not in registered:
            hint_str = ", ".join(registered) if registered else "없음"
            raise BudgetAppError(
                f"등록되지 않은 카테고리입니다: '{category}'",
                hint=f"현재 등록된 카테고리: {hint_str} (신규 추가는 category add 사용)",
            )

    # -------------------------------------------------------------
    # 2. 거래 내역 CRUD 및 조회
    # -------------------------------------------------------------
    @log_execution
    def add_transaction(
        self,
        date_str: str,
        type_: str,
        category: str,
        amount: int,
        memo: str = "",
        tags: Optional[List[str]] = None,
    ) -> Transaction:
        """신규 거래 내역 검증 및 고유 ID 생성 후 저장"""
        self._validate_date(date_str)
        self._validate_type(type_)
        self._validate_category(category)
        self._validate_amount(amount)

        tx_id = self.storage.generate_next_transaction_id()
        clean_tags = [t.strip() for t in tags] if tags else []

        tx = Transaction(
            id=tx_id,
            date=date_str.strip(),
            type=type_.strip().lower(),
            category=category.strip(),
            amount=amount,
            memo=memo.strip() if memo else "",
            tags=clean_tags,
        )

        self.storage.append_transaction(tx)
        return tx

    @measure_time
    def list_transactions(self, limit: int = 10) -> List[Transaction]:
        """heapq를 활용하여 최신순 상위 N건만 메모리에 유지하는 힙 스트리밍 정렬"""
        if limit <= 0:
            return []

        # 정렬 기준: (date 내림차순, id 내림차순)
        top_n = heapq.nlargest(
            limit,
            self.storage.stream_transactions(),
            key=lambda t: (t.date, t.id),
        )
        return top_n

    def search_transactions(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        category: Optional[str] = None,
        type_: Optional[str] = None,
        q: Optional[str] = None,
    ) -> Generator[Transaction, None, None]:
        """조건별 거래 내역 필터링 스트리밍 (제너레이터 지연 평가)"""
        if from_date:
            self._validate_date(from_date)
        if to_date:
            self._validate_date(to_date)

        for tx in self.storage.stream_transactions():
            if from_date and tx.date < from_date:
                continue
            if to_date and tx.date > to_date:
                continue
            if category and tx.category != category:
                continue
            if type_ and tx.type != type_:
                continue
            if q:
                q_lower = q.lower()
                in_memo = q_lower in (tx.memo or "").lower()
                in_tags = any(q_lower in tag.lower() for tag in tx.tags)
                if not (in_memo or in_tags):
                    continue
            yield tx

    @log_execution
    def update_transaction(
        self,
        tx_id: str,
        date_str: Optional[str] = None,
        type_: Optional[str] = None,
        category: Optional[str] = None,
        amount: Optional[int] = None,
        memo: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Transaction:
        """기존 거래 필드 검증 후 원자적 업데이트"""
        target = self.storage.get_transaction_by_id(tx_id)
        if not target:
            raise BudgetAppError(
                f"수정할 거래 ID를 찾을 수 없습니다: '{tx_id}'",
                hint="python -m budget_app list 명령어로 올바른 ID를 확인하세요.",
            )

        if date_str is not None:
            self._validate_date(date_str)
            target.date = date_str.strip()

        if type_ is not None:
            self._validate_type(type_)
            target.type = type_.strip().lower()

        if category is not None:
            self._validate_category(category)
            target.category = category.strip()

        if amount is not None:
            self._validate_amount(amount)
            target.amount = amount

        if memo is not None:
            target.memo = memo.strip()

        if tags is not None:
            target.tags = [t.strip() for t in tags if t.strip()]

        def update_modifier(tx_gen: Generator[Transaction, None, None]):
            for t in tx_gen:
                if t.id == tx_id:
                    yield target
                else:
                    yield t

        self.storage.rewrite_transactions_atomic(update_modifier)
        return target

    @log_execution
    def delete_transaction(self, tx_id: str) -> None:
        """기존 거래 확인 후 원자적 삭제"""
        target = self.storage.get_transaction_by_id(tx_id)
        if not target:
            raise BudgetAppError(
                f"삭제할 거래 ID를 찾을 수 없습니다: '{tx_id}'",
                hint="python -m budget_app list 명령어로 등록된 ID를 확인하세요.",
            )

        def delete_modifier(tx_gen: Generator[Transaction, None, None]):
            for t in tx_gen:
                if t.id != tx_id:
                    yield t

        self.storage.rewrite_transactions_atomic(delete_modifier)

    # -------------------------------------------------------------
    # 3. 예산 및 월별 결산 요약
    # -------------------------------------------------------------
    @log_execution
    def set_monthly_budget(self, month_str: str, amount: int) -> None:
        """월별 목표 예산 검증 및 저장"""
        self._validate_month(month_str)
        self._validate_amount(amount)
        budget = Budget(month=month_str.strip(), amount=amount)
        self.storage.set_budget(budget)

    def get_monthly_summary(self, month_str: str) -> Dict[str, Any]:
        """월별 총수입, 총지출, 잔액, 예산 사용률 및 지출 TOP 집계"""
        self._validate_month(month_str)
        target_month = month_str.strip()

        total_income = 0
        total_expense = 0
        expense_by_cat: Dict[str, int] = defaultdict(int)

        for tx in self.storage.stream_transactions():
            if tx.date.startswith(target_month):
                if tx.type == "income":
                    total_income += tx.amount
                elif tx.type == "expense":
                    total_expense += tx.amount
                    expense_by_cat[tx.category] += tx.amount

        net = total_income - total_expense
        budget_obj = self.storage.get_budget(target_month)
        budget_amount = budget_obj.amount if budget_obj else None

        usage_pct = 0.0
        if budget_amount and budget_amount > 0:
            usage_pct = (total_expense / budget_amount) * 100.0

        top_expenses = sorted(expense_by_cat.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "month": target_month,
            "total_income": total_income,
            "total_expense": total_expense,
            "net": net,
            "budget": budget_amount,
            "usage_pct": usage_pct,
            "top_expenses": top_expenses,
        }

    # -------------------------------------------------------------
    # 4. 카테고리 관리 및 참조 무결성 방어
    # -------------------------------------------------------------
    def list_categories(self) -> List[str]:
        """카테고리 전체 목록 조회"""
        return self.storage.get_all_categories()

    @log_execution
    def add_category(self, name: str) -> None:
        """신규 카테고리 중복 검증 후 추가"""
        clean_name = name.strip()
        if not clean_name:
            raise BudgetAppError("카테고리 이름은 공백일 수 없습니다.", hint="유효한 이름을 입력하세요.")

        registered = self.storage.get_all_categories()
        if clean_name in registered:
            raise BudgetAppError(
                f"이미 존재하는 카테고리입니다: '{clean_name}'",
                hint="python -m budget_app category list로 등록 목록을 확인하세요.",
            )

        self.storage.add_category(clean_name)

    @log_execution
    def remove_category(self, name: str, replace_with: Optional[str] = None) -> None:
        """사용 중인 카테고리 삭제 방어 및 --replace-with 일괄 대체 삭제"""
        clean_name = name.strip()
        registered = self.storage.get_all_categories()

        if clean_name not in registered:
            raise BudgetAppError(
                f"존재하지 않는 카테고리입니다: '{clean_name}'",
                hint="python -m budget_app category list로 등록된 목록을 확인하세요.",
            )

        # 1. 해당 카테고리를 참조하는 기존 거래 내역 존재 여부 검사
        referencing_txs = [
            tx.id for tx in self.storage.stream_transactions() if tx.category == clean_name
        ]

        if referencing_txs:
            if not replace_with:
                first_id = referencing_txs[0]
                raise BudgetAppError(
                    f"카테고리 '{clean_name}'를 사용하는 거래 내역(예: {first_id})이 있어 삭제할 수 없습니다.",
                    hint="--replace-with <대체카테고리> 옵션을 사용해 일괄 전환하거나 관련 거래를 먼저 수정하세요.",
                )

            clean_replace = replace_with.strip()
            if clean_replace == clean_name:
                raise BudgetAppError(
                    "대체 카테고리는 삭제할 카테고리와 달라야 합니다.",
                    hint="다른 기존 등록 카테고리를 지정하세요.",
                )
            if clean_replace not in registered:
                raise BudgetAppError(
                    f"대체할 카테고리가 등록되어 있지 않습니다: '{clean_replace}'",
                    hint="먼저 category add 명령어로 새 카테고리를 등록하거나 기존 카테고리를 지정하세요.",
                )

            # 기존 거래 내역의 카테고리를 원자적으로 일괄 대체
            def replace_modifier(tx_gen: Generator[Transaction, None, None]):
                for t in tx_gen:
                    if t.category == clean_name:
                        t.category = clean_replace
                    yield t

            self.storage.rewrite_transactions_atomic(replace_modifier)

        # 2. 카테고리 목록에서 제거
        self.storage.remove_category(clean_name)

    # -------------------------------------------------------------
    # 5. CSV 가져오기 / 내보내기 (스키마 및 트랜잭션 롤백)
    # -------------------------------------------------------------
    @log_execution
    def export_to_csv(self, out_path: str, month_str: str) -> int:
        """지정 월의 거래 내역을 UTF-8 CSV 파일로 내보내기"""
        self._validate_month(month_str)
        target_month = month_str.strip()

        matched_txs: List[Transaction] = [
            tx for tx in self.storage.stream_transactions() if tx.date.startswith(target_month)
        ]

        # 최신순 정렬 후 내보내기
        matched_txs.sort(key=lambda t: (t.date, t.id), reverse=True)

        try:
            with open(out_path, mode="w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["date", "type", "category", "amount", "memo", "tags"])
                for tx in matched_txs:
                    tags_joined = ",".join(tx.tags)
                    writer.writerow([tx.date, tx.type, tx.category, tx.amount, tx.memo, tags_joined])
        except OSError as e:
            raise BudgetAppError(
                f"CSV 파일을 저장할 수 없습니다: {e}",
                hint="출력 파일 경로의 쓰기 권한이나 폴더 존재 여부를 확인하세요.",
            )

        return len(matched_txs)

    @log_execution
    def import_from_csv(self, from_path: str, strict: bool = False) -> Tuple[int, int]:
        """
        CSV 파일로부터 거래 내역 적재
        - 기본 모드: 오류 행 건너뛰기 및 (성공 N건, 스킵 M건) 반환
        - strict 모드: 단 1건이라도 검증 실패 시 전체 롤백
        """
        try:
            with open(from_path, mode="r", encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                rows = list(reader)
        except OSError as e:
            raise BudgetAppError(
                f"CSV 파일을 열 수 없습니다: {e}",
                hint="파일 경로가 올바른지 확인하세요.",
            )

        if not rows:
            return (0, 0)

        header = [col.strip().lower() for col in rows[0]]
        expected_header = ["date", "type", "category", "amount", "memo", "tags"]
        if header != expected_header:
            raise BudgetAppError(
                "CSV 첫 줄 헤더가 올바르지 않습니다.",
                hint=f"필수 헤더 규격: {','.join(expected_header)}",
            )

        valid_transactions: List[Transaction] = []
        skipped_count = 0
        registered_cats = set(self.storage.get_all_categories())

        for line_num, row in enumerate(rows[1:], start=2):
            if len(row) < 6:
                if strict:
                    raise BudgetAppError(
                        f"CSV {line_num}행 필드 수 부족(6개 필요): {row}",
                        hint="strict 모드에서는 단 1건의 형식 오류도 허용되지 않으며 전체 롤백됩니다.",
                    )
                skipped_count += 1
                continue

            r_date, r_type, r_cat, r_amount, r_memo, r_tags = [item.strip() for item in row[:6]]

            try:
                # 1. 날짜 검증
                datetime.strptime(r_date, "%Y-%m-%d")
                # 2. 타입 검증
                if r_type.lower() not in ["income", "expense"]:
                    raise ValueError("타입 불일치")
                # 3. 카테고리 검증
                if r_cat not in registered_cats:
                    raise ValueError("미등록 카테고리")
                # 4. 금액 검증
                amt = int(r_amount)
                if amt <= 0:
                    raise ValueError("금액 음수/0")
            except (ValueError, BudgetAppError) as err:
                if strict:
                    raise BudgetAppError(
                        f"CSV {line_num}행 유효성 검증 실패 ({err}): {row}",
                        hint="strict 모드에서는 모든 데이터가 유효해야 적재되며 전체 취소됩니다.",
                    )
                skipped_count += 1
                continue

            clean_tags = [t.strip() for t in r_tags.split(",") if t.strip()]
            tx_id = self.storage.generate_next_transaction_id()
            tx = Transaction(
                id=tx_id,
                date=r_date,
                type=r_type.lower(),
                category=r_cat,
                amount=amt,
                memo=r_memo,
                tags=clean_tags,
            )
            valid_transactions.append(tx)

        # 검증 통과된 건들을 영구 저장소에 추가
        for tx in valid_transactions:
            self.storage.append_transaction(tx)

        return (len(valid_transactions), skipped_count)