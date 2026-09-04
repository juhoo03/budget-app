import functools
import sys
from typing import Callable, Any


class BudgetAppError(Exception):
    """비즈니스 로직 및 유효성 검증 예외 클래스"""
    def __init__(self, message: str, hint: str = ""):
        super().__init__(message)
        self.message = message
        self.hint = hint


def handle_cli_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    공통 예외 처리 데코레이터:
    - 스택트레이스를 숨기고 [오류] 및 [힌트] 형태로 출력
    - 예외 발생 시 exit code 1로 종료, 정상 시 0 반환
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except BudgetAppError as e:
            print(f"[오류] {e.message}", file=sys.stderr)
            if e.hint:
                print(f"[힌트] {e.hint}", file=sys.stderr)
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n[알림] 작업이 사용자에 의해 중단되었습니다.", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"[시스템 오류] 예기치 않은 오류가 발생했습니다: {str(e)}", file=sys.stderr)
            print("[힌트] 입력 데이터 형식을 다시 확인하거나 관리자에게 문의하세요.", file=sys.stderr)
            sys.exit(1)
    return wrapper