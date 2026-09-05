import argparse
import sys
from datetime import datetime
from typing import Any, List

from budget_app.storage import StorageManager
from budget_app.services import BudgetService
from budget_app.models import Transaction
from budget_app.decorators import handle_cli_errors, BudgetAppError


def format_transaction_row(tx: Transaction) -> str:
    """거래 내역 1건을 가독성 높은 테이블 행 문자열로 포맷팅"""
    tags_str = f"[{', '.join(tx.tags)}]" if tx.tags else ""
    return (
        f"{tx.id:<9} | {tx.date} | {tx.type:<7} | {tx.category:<10} | "
        f"{tx.amount:>8}원 | {tx.memo:<12} {tags_str}"
    )


def handle_add(service: BudgetService, args: Any) -> None:
    """대화형 입력을 통한 신규 거래 내역 추가 (각 입력값 즉시 검증)"""
    print("--- 거래 내역 추가 (대화형) ---")

    # 1. 날짜 입력 및 유효성 즉시 검증
    date_str = input("날짜(YYYY-MM-DD): ").strip()
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise BudgetAppError(
            f"날짜 형식이 올바르지 않습니다: '{date_str}'",
            hint="YYYY-MM-DD 형식의 올바른 날짜(예: 2026-09-05)를 입력하세요."
        )

    # 2. 거래 타입 입력 및 즉시 검증
    type_str = input("타입(income/expense): ").strip().lower()
    if type_str not in ["income", "expense"]:
        raise BudgetAppError(
            f"유효하지 않은 거래 타입입니다: '{type_str}'",
            hint="'income' 또는 'expense' 중 하나를 입력하세요."
        )

    # 3. 카테고리 입력 및 등록 여부 사전 검증
    category_str = input("카테고리: ").strip()
    categories = service.storage.get_all_categories()
    if category_str not in categories:
        hint_cats = ", ".join(categories) if categories else "없음"
        raise BudgetAppError(
            f"등록되지 않은 카테고리입니다: '{category_str}'",
            hint=f"현재 등록된 카테고리: {hint_cats} (신규 추가는 category add 사용)"
        )

    # 4. 금액 입력 및 양수 정수 검증
    amount_str = input("금액(양수): ").strip()
    try:
        amount = int(amount_str)
        if amount <= 0:
            raise ValueError
    except ValueError:
        raise BudgetAppError(
            f"금액은 0보다 큰 정수여야 합니다: '{amount_str}'",
            hint="1 이상의 숫자(예: 15000)를 입력하세요."
        )

    # 5. 메모 및 태그 입력 (선택 사항)
    memo_str = input("메모(선택): ").strip()
    tags_str = input("태그(쉼표로 구분, 없으면 엔터): ").strip()
    tags = [t.strip() for t in tags_str.split(",") if t.strip()]

    tx = service.add_transaction(date_str, type_str, category_str, amount, memo_str, tags)
    print(f"[저장 완료] id={tx.id}")


def handle_list(service: BudgetService, args: Any) -> None:
    """최신순 정렬된 거래 목록 조회"""
    txs = service.list_transactions(limit=args.limit)
    if not txs:
        print("등록된 거래 내역이 없습니다.")
        return
    for tx in txs:
        print(format_transaction_row(tx))


def handle_search(service: BudgetService, args: Any) -> None:
    """조건별 거래 내역 검색"""
    results = list(
        service.search_transactions(
            from_date=args.from_date,
            to_date=args.to_date,
            category=args.category,
            type_=args.type,
            q=args.q,
        )
    )
    if not results:
        print("검색 조건에 일치하는 거래 내역이 없습니다.")
        return
    for tx in results:
        print(format_transaction_row(tx))


def handle_summary(service: BudgetService, args: Any) -> None:
    """월별 수입/지출 집계 및 예산 연동 결산 보고서 출력"""
    summary_data = service.get_monthly_summary(args.month)

    print(f"총 수입: {summary_data['total_income']:,}원")
    print(f"총 지출: {summary_data['total_expense']:,}원")
    print(f"잔액: {summary_data['net']:,}원")

    budget_amount = summary_data["budget"]
    if budget_amount is not None:
        usage_pct = summary_data["usage_pct"]
        print(f"예산: {budget_amount:,}원 (사용률 {usage_pct:.1f}%)")
        if usage_pct > 100.0:
            print("[경고: 예산 초과! 콘솔 알림]")
    else:
        print("예산: 미설정")

    top_expenses: List = summary_data["top_expenses"]
    if top_expenses:
        print(f"지출 TOP {len(top_expenses)}")
        for idx, (cat, amt) in enumerate(top_expenses, start=1):
            print(f"{idx}) {cat} {amt:,}원")


def handle_budget_set(service: BudgetService, args: Any) -> None:
    """월별 목표 예산 설정"""
    service.set_monthly_budget(args.month, args.amount)
    print(f"[저장 완료] {args.month} 예산 {args.amount}원")


def handle_category(service: BudgetService, args: Any) -> None:
    """카테고리 관리 (list, add, remove)"""
    if args.cat_action == "list":
        cats = service.list_categories()
        if not cats:
            print("등록된 카테고리가 없습니다.")
            return
        for c in cats:
            print(f"- {c}")
    elif args.cat_action == "add":
        service.add_category(args.name)
        print(f"[추가 완료] category={args.name}")
    elif args.cat_action == "remove":
        service.remove_category(args.name, replace_with=args.replace_with)
        print(f"[삭제 완료] category={args.name}")


def handle_update(service: BudgetService, args: Any) -> None:
    """지정 ID의 거래 내역 필드 수정"""
    tags = None
    if args.tags is not None:
        tags = [t.strip() for t in args.tags.split(",") if t.strip()]

    tx = service.update_transaction(
        tx_id=args.id,
        date_str=args.date,
        type_=args.type,
        category=args.category,
        amount=args.amount,
        memo=args.memo,
        tags=tags,
    )
    print(f"[수정 완료] {format_transaction_row(tx)}")


def handle_delete(service: BudgetService, args: Any) -> None:
    """지정 ID의 거래 내역 영구 삭제"""
    service.delete_transaction(args.id)
    print(f"[삭제 완료] id={args.id}")


def handle_export(service: BudgetService, args: Any) -> None:
    """지정 월 거래 내역을 CSV 파일로 내보내기"""
    count = service.export_to_csv(args.out, args.month)
    print(f"[완료] {args.out} ({count} records)")


def handle_import(service: BudgetService, args: Any) -> None:
    """CSV 파일로부터 거래 내역 적재 (기본 모드 또는 strict 트랜잭션 모드)"""
    imported, skipped = service.import_from_csv(args.from_path, strict=args.strict)
    print(f"[완료] imported = {imported}, skipped = {skipped}")


def create_parser() -> argparse.ArgumentParser:
    """리눅스 표준 CLI 옵션 명세를 충족하는 인수 파서 구성"""
    parser = argparse.ArgumentParser(
        prog="python -m budget_app",
        description="나만의 용돈 기입장 콘솔 서비스 (Budget App)",
    )
    parser.add_argument(
        "--data-dir",
        default="./data",
        help="데이터 영구 저장 디렉터리 경로 (기본값: ./data)",
    )

    subparsers = parser.add_subparsers(dest="subcommand", help="사용 가능한 하위 명령어")

    # add
    subparsers.add_parser("add", help="거래 내역 추가 (대화형 인터페이스)")

    # list
    list_p = subparsers.add_parser("list", help="거래 내역 최신순 조회")
    list_p.add_argument("--limit", type=int, default=10, help="조회할 최대 레코드 수 (기본: 10)")

    # search
    search_p = subparsers.add_parser("search", help="다양한 조건으로 거래 내역 필터링 검색")
    search_p.add_argument("--from-date", help="시작일 (YYYY-MM-DD)")
    search_p.add_argument("--to-date", help="종료일 (YYYY-MM-DD)")
    search_p.add_argument("--category", help="카테고리명")
    search_p.add_argument("--type", choices=["income", "expense"], help="거래 타입")
    search_p.add_argument("--q", help="메모 대상 검색 키워드")

    # summary
    sum_p = subparsers.add_parser("summary", help="월별 결산 요약 및 예산 사용률 조회")
    sum_p.add_argument("--month", required=True, help="조회 대상 월 (YYYY-MM)")

    # budget
    budget_p = subparsers.add_parser("budget", help="월별 목표 예산 관리")
    budget_sub = budget_p.add_subparsers(dest="budget_action", help="예산 관련 동작")
    b_set = budget_sub.add_parser("set", help="예산 금액 설정")
    b_set.add_argument("--month", required=True, help="대상 월 (YYYY-MM)")
    b_set.add_argument("--amount", required=True, type=int, help="목표 예산 금액 (양의 정수)")

    # category
    cat_p = subparsers.add_parser("category", help="카테고리 조회/추가/삭제")
    cat_sub = cat_p.add_subparsers(dest="cat_action", help="카테고리 하위 동작")
    cat_sub.add_parser("list", help="전체 카테고리 목록 조회")
    c_add = cat_sub.add_parser("add", help="신규 카테고리 등록")
    c_add.add_argument("name", help="추가할 카테고리명")
    c_rem = cat_sub.add_parser("remove", help="기존 카테고리 삭제")
    c_rem.add_argument("name", help="삭제할 카테고리명")
    c_rem.add_argument(
        "--replace-with",
        help="삭제 대상 카테고리를 사용하는 기존 거래들을 대체할 신규 카테고리명",
    )

    # update
    up_p = subparsers.add_parser("update", help="특정 거래 내역 수정")
    up_p.add_argument("--id", required=True, help="수정할 거래 ID (예: TX-000001)")
    up_p.add_argument("--date", help="변경할 날짜 (YYYY-MM-DD)")
    up_p.add_argument("--type", choices=["income", "expense"], help="변경할 거래 타입")
    up_p.add_argument("--category", help="변경할 카테고리")
    up_p.add_argument("--amount", type=int, help="변경할 금액 (양의 정수)")
    up_p.add_argument("--memo", help="변경할 메모")
    up_p.add_argument("--tags", help="변경할 태그 목록 (쉼표 구분)")

    # delete
    del_p = subparsers.add_parser("delete", help="특정 거래 내역 삭제")
    del_p.add_argument("--id", required=True, help="삭제할 거래 ID (예: TX-000001)")

    # export
    exp_p = subparsers.add_parser("export", help="CSV 파일로 거래 내역 내보내기")
    exp_p.add_argument("--out", required=True, help="저장할 CSV 파일 경로")
    exp_p.add_argument("--month", required=True, help="내보낼 대상 월 (YYYY-MM)")

    # import
    imp_p = subparsers.add_parser("import", help="CSV 파일로부터 거래 내역 가져오기")
    imp_p.add_argument("--from", dest="from_path", required=True, help="불러올 CSV 파일 경로")
    imp_p.add_argument(
        "--strict",
        action="store_true",
        help="단 1건이라도 검증 실패 시 전체 적재를 취소하는 엄격한 롤백 모드 활성화",
    )

    return parser


@handle_cli_errors
def run_cli() -> None:
    """CLI 진입점: 인수 파싱 및 적절한 하위 핸들러 디스패치"""
    parser = create_parser()
    args = parser.parse_args()

    if not args.subcommand:
        parser.print_help()
        return

    storage = StorageManager(args.data_dir)
    service = BudgetService(storage)

    handlers = {
        "add": handle_add,
        "list": handle_list,
        "search": handle_search,
        "summary": handle_summary,
        "update": handle_update,
        "delete": handle_delete,
        "export": handle_export,
        "import": handle_import,
    }

    if args.subcommand in handlers:
        handlers[args.subcommand](service, args)
    elif args.subcommand == "budget":
        if args.budget_action == "set":
            handle_budget_set(service, args)
        else:
            parser.parse_args(["budget", "--help"])
    elif args.subcommand == "category":
        if args.cat_action in ["list", "add", "remove"]:
            handle_category(service, args)
        else:
            parser.parse_args(["category", "--help"])


if __name__ == "__main__":
    run_cli()