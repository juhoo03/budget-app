import functools
import os
import sys
import time
from typing import Callable, Any


class BudgetAppError(Exception):
    """비즈니스 로직 및 유효성 검증 예외 클래스"""
    def __init__(self, message: str, hint: str = ""):
        super().__init__(message)
        self.message = message
        self.hint = hint


def measure_time(func: Callable[..., Any]) -> Callable[..., Any]:
    """함수의 실행 시간을 측정하여 디버그 환경 또는 콘솔에 출력하는 데코레이터"""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = (time.perf_counter() - start_time) * 1000
        if os.environ.get("BUDGET_DEBUG") == "1":
            print(f"[DEBUG] '{func.__name__}' 실행 소요 시간: {elapsed:.2f}ms", file=sys.stderr)
        return result
    return wrapper


def log_execution(func: Callable[..., Any]) -> Callable[..., Any]:
    """함수의 호출 시점과 입력 인자 메타데이터를 로깅하는 데코레이터"""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if os.environ.get("BUDGET_DEBUG") == "1":
            arg_repr = [repr(a) for a in args[1:]]  # self 제외
            kwarg_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
            signature = ", ".join(arg_repr + kwarg_repr)
            print(f"[LOG] 함수 호출: {func.__name__}({signature})", file=sys.stderr)
        return func(*args, **kwargs)
    return wrapper


def handle_cli_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    공통 예외 처리 데코레이터:
    - 스택트레이스를 숨기고 [오류] 및 [힌트] 형태로 출력
    - 성공 시 sys.exit(0), 비즈니스/사용자 오류 시 sys.exit(1), 시스템 오류 시 sys.exit(2)
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            func(*args, **kwargs)
            sys.exit(0)  # 명시적 정상 종료 코드 보장
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
            print("[힌트] 입력 데이터 형식을 다시 확인하거나 로그를 점검하세요.", file=sys.stderr)
            sys.exit(2)
    return wrapper