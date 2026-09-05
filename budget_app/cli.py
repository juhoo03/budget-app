import argparse
import sys
from budget_app.storage import StorageManager
from budget_app.services import BudgetService
from budget_app.decorators import handle_cli_errors, BudgetAppError


def format_tx_line(tx) -> str:
    tags_str = f"[{', '.join(tx.tags)}]" if tx.tags else ""
    return f"{tx.id:<9} | {tx.date} | {tx.type:<7} | {tx.category:<10} | {tx.amount:>8}원 | {tx.memo:<12} {tags_str}"


@handle_cli_errors
def run_cli():
    parser = argparse.ArgumentParser(
        prog="python -m budget_app",
        description="나만의 가계부/용돈 기입장 콘솔 서비스"
    )
    parser.add_argument("--data-dir", default="./data", help="데이터 저장 디렉터리 경로 (기본값: ./data)")
    subparsers = parser.add_subparsers(dest="command", help="실행할 명령어")

    # 1. add
    subparsers.add_parser("add", help="거래 추가 (대화형 입력)")

    # 2. list
    list_p = subparsers.add_parser("list", help="거래 목록 최신순 조회 (스트리밍 Top-N)")
    list_p.add_argument("--limit", type=int, default=10, help="출력할 최대 건수 (기본값: 10)")

    # 3. search
    search_p = subparsers.add_parser("search", help="거래 조건 검색 (제너레이터 지연 로드)")
    search_p.add_argument("--from", dest="from_date", help="시작 날짜 (YYYY-MM-DD)")
    search_p.add_argument("--to", dest="to_date", help="종료 날짜 (YYYY-MM-DD)")
    search_p.add_argument("--category", help="카테고리")
    search_p.add_argument("--type", choices=["income", "expense"], help="거래 타입")
    search_p.add_argument("--q", help="메모 검색 키워드")
    search_p.add_argument("--tag", help="태그")

    # 4. summary
    summary_p = subparsers.add_parser("summary", help="월별 요약 조회")
    summary_p.add_argument("--month", required=True, help="조회할 월 (YYYY-MM)")
    summary_p.add_argument("--top", type=int, default=3, help="지출 상위 카테고리 개수 (기본값: 3)")

    # 5. budget
    budget_p = subparsers.add_parser("budget", help="예산 관리")
    budget_sub = budget_p.add_subparsers(dest="budget_action")
    b_set = budget_sub.add_parser("set", help="예산 설정")
    b_set.add_argument("--month", required=True, help="설정 월 (YYYY-MM)")
    b_set.add_argument("--amount", type=int, required=True, help="예산 금액")

    # 6. category
    cat_p = subparsers.add_parser("category", help="카테고리 관리")
    cat_sub = cat_p.add_subparsers(dest="cat_action")
    cat_sub.add_parser("list", help="카테고리 목록 조회")
    cat_add = cat_sub.add_parser("add", help="카테고리 추가")
    cat_add.add_argument("name", nargs="?", help="추가할 카테고리명")
    cat_rm = cat_sub.add_parser("remove", help="카테고리 삭제")
    cat_rm.add_argument("name", help="삭제할 카테고리명")
    cat_rm.add_argument("--replace-with", help="삭제 시 기존 내역을 일괄 전환할 새 카테고리명")

    # 7. update
    update_p = subparsers.add_parser("update", help="거래 내역 수정")
    update_p.add_argument("--id", required=True, help="수정할 거래 ID")
    update_p.add_argument("--date", help="새 날짜 (YYYY-MM-DD)")
    update_p.add_argument("--type", choices=["income", "expense"], help="새 타입")
    update_p.add_argument("--category", help="새 카테고리")
    update_p.add_argument("--amount", type=int, help="새 금액")
    update_p.add_argument("--memo", help="새 메모")
    update_p.add_argument("--tags", help="새 태그들 (콤마 구분)")

    # 8. delete
    del_p = subparsers.add_parser("delete", help="거래 내역 삭제")
    del_p.add_argument("--id", required=True, help="삭제할 거래 ID")

    # 9. export / import
    export_p = subparsers.add_parser("export", help="거래 내역 CSV 내보내기")
    export_p.add_argument("--out", required=True, help="출력 CSV 파일 경로")
    export_p.add_argument("--month", help="지정 월 (YYYY-MM)")
    export_p.add_argument("--from", dest="from_date", help="시작 날짜")
    export_p.add_argument("--to", dest="to_date", help="종료 날짜")

    import_p = subparsers.add_parser("import", help="CSV 거래 내역 가져오기")
    import_p.add_argument("--from", dest="from_file", required=True, help="가져올 CSV 파일 경로")
    import_p.add_argument("--strict", action="store_true", help="오류 행 발생 시 전체 롤백 모드")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    storage = StorageManager(args.data_dir)
    service = BudgetService(storage)

    if args.command == "add":
        print("--- 거래 내역 추가 (대화형) ---")
        date = input("날짜(YYYY-MM-DD): ").strip()
        t_type = input("타입(income/expense): ").strip()
        category = input("카테고리: ").strip()
        amt_str = input("금액(양수): ").strip()
        try:
            amount = int(amt_str)
        except ValueError:
            raise BudgetAppError("금액은 숫자여야 합니다.", hint="정수 형태(예: 15000)로 입력하세요.")
        memo = input("메모(선택): ")
        tags_raw = input("태그(쉼표로 구분, 없으면 엔터): ")
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

        created = service.add_transaction(date, t_type, category, amount, memo, tags)
        print(f"[저장 완료] id={created.id}")

    elif args.command == "list":
        txs = service.list_transactions(limit=args.limit)
        if not txs:
            print("거래 내역이 없습니다.")
            return
        for tx in txs:
            print(format_tx_line(tx))

    elif args.command == "search":
        found = False
        for tx in service.search_transactions(
            from_date=args.from_date,
            to_date=args.to_date,
            category=args.category,
            type_=args.type,
            query=args.q,
            tag=args.tag,
        ):
            print(format_tx_line(tx))
            found = True
        if not found:
            print("검색 조건과 일치하는 내역이 없습니다.")

    elif args.command == "summary":
        res = service.get_summary(args.month, top_n=args.top)
        if res["empty"]:
            print(f"[{args.month}] 등록된 데이터가 없습니다.")
            return

        print(f"총 수입: {res['total_income']:,}원")
        print(f"총 지출: {res['total_expense']:,}원")
        print(f"잔액: {res['balance']:,}원")

        if res["budget"] is not None:
            status = f"예산: {res['budget']:,}원 (사용률 {res['usage_rate']:.1f}%)"
            if res["is_over"]:
                status += " [경고: 예산 초과! 콘솔 알림]"
            print(status)

        print(f"지출 TOP {len(res['top_categories'])}")
        for idx, (cat, amt) in enumerate(res["top_categories"], start=1):
            print(f"{idx}) {cat} {amt:,}원")

    elif args.command == "budget":
        if args.budget_action == "set":
            if args.amount <= 0:
                raise BudgetAppError("예산 금액은 양수여야 합니다.")
            service.validate_month(args.month)
            storage.set_budget(args.month, args.amount)
            print(f"[저장 완료] {args.month} 예산 {args.amount}원")
        else:
            parser.parse_args(["budget", "--help"])

    elif args.command == "category":
        if args.cat_action == "list":
            for cat in storage.get_all_categories():
                print(f"- {cat}")
        elif args.cat_action == "add":
            name = args.name
            if not name:
                name = input("카테고리명: ").strip()
            service.add_category(name)
            print(f"[저장 완료] category={name}")
        elif args.cat_action == "remove":
            service.remove_category(args.name, replace_with=args.replace_with)
            print(f"[삭제 완료] category={args.name}")
        else:
            parser.parse_args(["category", "--help"])

    elif args.command == "update":
        tags = [t.strip() for t in args.tags.split(",")] if args.tags else None
        updated = service.update_transaction(
            tx_id=args.id,
            date=args.date,
            type_=args.type,
            category=args.category,
            amount=args.amount,
            memo=args.memo,
            tags=tags,
        )
        print(f"[수정 완료] {format_tx_line(updated)}")

    elif args.command == "delete":
        service.delete_transaction(args.id)
        print(f"[삭제 완료] id={args.id}")

    elif args.command == "export":
        cnt = service.export_to_csv(
            out_path=args.out,
            month=args.month,
            from_date=args.from_date,
            to_date=args.to_date,
        )
        print(f"[완료] {args.out} ({cnt} records)")

    elif args.command == "import":
        imported, skipped = service.import_from_csv(args.from_file, strict=args.strict)
        print(f"[완료] imported = {imported}, skipped = {skipped}")