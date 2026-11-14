# 💰 나만의 용돈 기입장 프로그램 (Budget App)

별도의 외부 패키지 설치 없이 Python 기본 기능으로 구현한 콘솔 가계부 프로그램입니다. 수입·지출 관리, 카테고리 관리, 월별 예산 및 결산, CSV 가져오기·내보내기를 지원합니다.

---

# 1. 기능 구현 및 동작 확인

## 1-1. 거래 내역 추가·조회·검색·수정·삭제

### 거래 내역 추가 (`add`)
```bash
python -m budget_app add
--- 거래 내역 추가 (대화형) ---
날짜(YYYY-MM-DD): 2026-09-04
타입(income/expense): expense
카테고리: 식비
금액(양수): 12000
메모(선택): 점심
태그(쉼표로 구분, 없으면 엔터): 점심,외식
[저장 완료] id=TX-000001
```

### 전체 목록 조회 (`list`)
최신 날짜와 ID를 기준으로 내림차순 정렬합니다.
```bash
python3 -m budget_app list
TX-000002 | 2026-09-05 | income  | 월급       |   100000원 | 장학금          [장학금]
TX-000001 | 2026-09-04 | expense | 식비       |    12000원 | 점심            [점심, 외식]
```

### 조건별 검색 (`search`)
```bash
# 카테고리 검색
python3 -m budget_app search --category 식비

# 메모 또는 태그에 '점심'이 포함된 내역 검색
python3 -m budget_app search --q 점심
```

### 거래 내역 수정 및 삭제 (`update`, `delete`)
```bash
# 금액과 메모 수정
python3 -m budget_app update --id TX-000001 --amount 15000 --memo "점심(특식)"

# 거래 내역 삭제
python3 -m budget_app delete --id TX-000001
[삭제 완료] id=TX-000001
```

## 1-2. 프로그램 재실행 후 데이터 유지

프로그램은 `./data/` 폴더에 다음 세 파일을 사용합니다.

- `transactions.jsonl`: 수입·지출 거래 내역
- `categories.jsonl`: 카테고리 목록
- `budgets.jsonl`: 월별 예산

파일이 없으면 프로그램 시작 시 생성하며, 카테고리 파일이 비어 있으면 기본 카테고리를 등록합니다. 거래 내역은 JSONL 파일에 추가 저장되므로 프로그램을 종료한 뒤 다시 실행해도 데이터가 유지됩니다.

## 1-3. 카테고리 추가·목록·삭제 (`category`)

```bash
# 카테고리 추가
python3 -m budget_app category add 교육

# 카테고리 목록
python3 -m budget_app category list

# 사용 중인 카테고리 삭제 시도
python3 -m budget_app category remove 식비
[오류] 카테고리 '식비'를 사용하는 거래 내역(예: TX-000001)이 있어 삭제할 수 없습니다.
[힌트] --replace-with <대체카테고리> 옵션을 사용해 일괄 전환하거나 관련 거래를 먼저 수정하세요.

# 사용 중인 내역을 '기타'로 바꾼 뒤 카테고리 삭제
python3 -m budget_app category remove 식비 --replace-with 기타
[삭제 완료] category=식비
```

사용 중인 카테고리는 거래 내역이 참조하고 있는지 먼저 검사합니다. 참조 내역이 있으면 기본 삭제를 거부하고, `--replace-with`를 지정한 경우 기존 거래 내역의 카테고리를 등록된 대체 카테고리로 변경한 뒤 삭제합니다.

## 1-4. 예산 설정 및 월별 결산 (`budget set`, `summary`)

```bash
# 2026년 9월 예산 설정
python3 -m budget_app budget set --month 2026-09 --amount 500000
[저장 완료] 2026-09 예산 500000원

# 월별 결산
python3 -m budget_app summary --month 2026-09
총 수입: 100,000원
총 지출: 12,000원
잔액: 88,000원
예산: 500,000원 (사용률 2.4%)
지출 TOP 1
1) 식비 12,000원
```

요약에는 총수입, 총지출, 잔액(수입-지출), 설정 예산, 예산 사용률, 지출 카테고리 상위 항목이 표시됩니다.

## 1-5. CSV 내보내기 및 가져오기 (`export`, `import`)

CSV는 UTF-8 인코딩을 사용하며 첫 줄에 다음 헤더가 있어야 합니다.

```text
date,type,category,amount,memo,tags
```

```bash
# 특정 월의 거래 내역을 CSV로 내보내기
python3 -m budget_app export --out export_data.csv --month 2026-09
[완료] export_data.csv (1 records)

# CSV 파일 가져오기
python3 -m budget_app import --from export_data.csv
[완료] imported = 1, skipped = 0
```

내보내기 시 CSV 헤더와 지정된 열 순서를 사용합니다. 가져오기는 UTF-8 BOM이 포함된 파일도 읽을 수 있도록 `utf-8-sig` 인코딩을 사용합니다.

## 1-6. 잘못된 입력·파일 오류 및 종료 코드

```bash
python3 -m budget_app add
날짜(YYYY-MM-DD): 2026-13-40
[오류] 날짜 형식이 올바르지 않습니다: '2026-13-40'
[힌트] YYYY-MM-DD 형식의 실제 달력 날짜(예: 2026-09-05)를 입력하세요.

# 직전 명령의 종료 코드 확인 (실패 시 1)
echo $?
1
```

`@handle_cli_errors`가 CLI 진입점의 예외를 처리하여 긴 스택 트레이스 대신 오류 메시지와 해결 힌트를 출력합니다. 정상 종료는 코드 `0`, 사용자 입력·업무 규칙 오류는 `1`, 예상하지 못한 시스템 오류는 `2`로 종료하도록 구성했습니다.

---

# 2. 모듈 분리 및 클래스 책임 설계

## 2-1. 5개 모듈로 분리한 이유

```text
budget_app/
├── models.py      # 거래 내역과 예산 데이터 구조
├── storage.py     # JSONL 파일 읽기·쓰기 및 저장 관리
├── services.py    # 거래·예산·카테고리의 핵심 규칙과 계산
├── decorators.py  # 공통 오류 처리·로깅·실행 시간 측정
└── cli.py         # 명령어 입력 및 결과 출력
```

각 모듈이 하나의 역할에 집중하도록 분리했습니다. 특히 화면 입출력(`cli.py`), 업무 규칙(`services.py`), 파일 저장(`storage.py`)을 분리하여 향후 터미널 인터페이스를 웹이나 앱으로 바꾸더라도 핵심 서비스와 저장 기능을 재사용할 수 있도록 했습니다.

패키지 import 확인:
```bash
python -c "import budget_app"
성공 시 아무것도 안뜸

실패시 :
ModuleNotFoundError:
No module named 'budget_app'
```

## 2-2. 클래스별 책임과 경계

- **`Transaction`**: 거래 ID, 거래 유형, 날짜, 금액, 카테고리, 메모, 태그 등 거래 데이터의 구조를 정의하고 `to_dict()` / `from_dict()`로 객체와 저장용 딕셔너리를 변환합니다.
- **`Budget`**: 대상 월과 예산 금액을 표현하며 저장용 딕셔너리와 객체 사이의 변환을 담당합니다.
- **`StorageManager`**: `transactions.jsonl`, `categories.jsonl`, `budgets.jsonl`의 파일 생성·조회·추가·교체를 담당합니다.
- **`BudgetService`**: 날짜·유형·금액·카테고리 유효성 검사, 거래 CRUD, 예산 계산, 카테고리 참조 검사 등 가계부의 업무 규칙을 담당합니다.

즉, 데이터 모양은 모델 클래스가, 파일 입출력은 저장소 클래스가, 실제 처리 규칙은 서비스 클래스가 맡도록 책임을 나누었습니다.

## 2-3. 파일 기반 update/delete의 안전성

거래 내역 수정·삭제는 원본 파일을 바로 덮어쓰지 않고 다음 순서로 처리합니다.

1. 같은 데이터 폴더에 임시 파일을 생성합니다.
2. 기존 거래를 한 줄씩 읽어 수정 또는 삭제 결과를 임시 파일에 기록합니다.
3. `flush()`와 `os.fsync()`로 임시 파일의 기록을 디스크에 반영합니다.
4. 원본 파일을 `.bak` 파일로 복사합니다.
5. `os.replace()`로 임시 파일을 원본 파일 위치에 교체합니다.

이 방식은 임시 파일 작성이 끝난 뒤 파일 교체를 수행하므로, 교체 도중 원본 파일을 직접 수정하는 방식보다 데이터 손상 위험을 줄입니다. 다만 백업 및 교체가 모든 파일에 걸친 하나의 트랜잭션을 의미하는 것은 아닙니다.

확인 예시:
```bash
python -m budget_app update --id TX-000001 --amount 15000 --memo "점심(특식)"
ls -l data/transactions.jsonl.bak
```

---

# 3. Python 핵심 기술 적용

## 3-1. 제너레이터를 이용한 list/search 스트리밍

`StorageManager.stream_transactions()`는 JSONL 파일을 `for line in f`로 한 줄씩 읽고, `yield`를 통해 `Transaction` 객체를 차례로 전달합니다.

`BudgetService.search_transactions()`도 조건에 맞는 거래만 `yield`하므로 검색 결과 전체를 서비스 내부에서 미리 리스트로 만들지 않습니다.

`list` 조회에서는 `heapq.nlargest()`를 사용해 최신 거래 상위 N건을 선택합니다.

```bash
# 최근 거래 상위 5건
python -m budget_app list --limit 5

# 카테고리 검색
python -m budget_app search --category 식비
```

**장점:** 파일 전체를 한 번에 거래 객체 리스트로 변환하지 않아 스트리밍 처리 과정의 메모리 사용량을 줄일 수 있습니다. 단, 검색과 상위 N건 조회 모두 파일을 처음부터 끝까지 순회하므로 파일 읽기 시간 자체가 없어지는 것은 아닙니다. 또한 CLI 출력 단계에서는 검색 결과를 리스트로 변환하는 부분이 있습니다.

## 3-2. 데코레이터로 공통 기능 분리

세 가지 데코레이터를 적용했습니다.

1. **`@handle_cli_errors`**: CLI 진입점에서 예외를 공통 처리하고, 스택 트레이스 대신 오류 메시지와 해결 힌트를 출력합니다.
2. **`@log_execution`**: 디버그 모드에서 함수 호출과 전달 인자 정보를 기록합니다.
3. **`@measure_time`**: 함수 실행 시간을 측정해 디버그 모드에서 밀리초 단위로 출력합니다.

데코레이터를 사용하면 핵심 기능 코드 안에 반복적인 로깅·시간 측정 코드를 매번 작성하지 않아도 됩니다.

확인 명령어:
```bash
BUDGET_DEBUG=1 python3 -m budget_app list
```

출력 예시:
```text
[DEBUG] 'list_transactions' 실행 소요 시간: 0.10ms
```

`log_execution`은 디버그 모드에서 활성화되며, `measure_time`도 `BUDGET_DEBUG=1`일 때 실행 시간을 출력합니다.

## 3-3. 타입 힌트(Type Hints)

실제 코드 예시:
```python
def search_transactions(
    self,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    category: Optional[str] = None,
    type_: Optional[str] = None,
    q: Optional[str] = None,
) -> Generator[Transaction, None, None]:
    ...
```

`Optional[str]`은 문자열 또는 `None`이 올 수 있음을, `Generator[Transaction, None, None]`은 `Transaction` 객체를 순차적으로 생성하는 제너레이터임을 나타냅니다. 타입 힌트는 코드의 입력과 반환 형태를 명확하게 하여 가독성과 유지보수성을 높입니다.

---

# 4. 저장 포맷 선택 및 대용량·오류 데이터 대응

## 4-1. JSONL과 CSV 비교 및 JSONL 선택 이유

| 비교 항목 | JSONL (.jsonl) | CSV (.csv) |
|---|---|---|
| 데이터 구조 | 한 줄마다 JSON 객체 저장 | 행과 열 중심의 표 형식 |
| 복잡한 데이터 | 태그 목록 등 자료형을 구조화해 저장 가능 | 복잡한 값은 별도 문자열 변환 필요 |
| 손상 행 처리 | 개별 줄 단위로 파싱을 시도할 수 있음 | 행·열 형식에 따라 파싱 필요 |
| 활용 | 프로그램 내부 저장에 적합 | 엑셀 등 외부 도구에서 열고 공유하기 편리 |

**JSONL 선택 이유:** 거래 한 건을 한 줄의 JSON 객체로 저장하므로 거래별 데이터 구조를 유지하기 쉽고, 파일을 한 줄씩 읽는 스트리밍 처리와도 잘 맞습니다. CSV는 사용자가 엑셀 등으로 확인하고 다른 프로그램과 데이터를 주고받을 수 있도록 Import/Export 용도로 사용합니다.

## 4-2. 거래가 10만 건 이상으로 늘어날 때의 병목과 개선 방향

현재 구조에서 예상되는 병목은 다음과 같습니다.

1. **목록 정렬:** `heapq.nlargest()`로 상위 N건만 메모리에 유지하지만, 대상 파일 전체를 읽어야 합니다. 상위 N건 조회의 메모리 사용량은 줄일 수 있어도 전체 파일 순회 비용은 남습니다.
2. **검색:** 현재는 JSONL을 처음부터 끝까지 순회하므로 거래가 많아질수록 검색 시간이 증가합니다. 날짜·카테고리 인덱스를 도입하거나 SQLite로 이전하면 개선할 수 있습니다.
3. **수정·삭제:** 현재 거래 한 건을 수정하거나 삭제해도 거래 파일 전체를 다시 기록합니다. 데이터가 매우 커지면 SQLite처럼 일부 레코드만 갱신할 수 있는 저장 구조로 전환하는 것이 적합합니다.

현재 `heapq`는 상위 N건을 고르는 데 적용되어 있으며, 인덱스나 SQLite는 대용량 확장 시 고려할 개선 방향입니다.

## 4-3. CSV Import의 잘못된 행 처리와 사용자 신뢰성

CSV 가져오기는 두 가지 모드를 제공합니다.

- **기본 모드:** 날짜·유형·카테고리·금액 등이 유효하지 않은 행은 건너뛰고 정상 행을 저장합니다. 처리 결과로 성공 건수와 건너뛴 건수를 반환합니다.
- **--strict`:** 검증 과정에서 잘못된 행이 하나라도 발견되면 오류를 발생시키고 저장 단계로 넘어가지 않습니다. 따라서 검증 오류 때문에 일부 행만 먼저 저장되는 상황을 방지합니다.

```bash
# 유효한 행만 가져오기
python3 -m budget_app import --from budget_app/data.csv

# 검증 오류가 하나라도 있으면 전체 가져오기 취소
python3 -m budget_app import --from budget_app/data.csv --strict
```

현재 구현은 CSV 전체 행을 먼저 읽고 검증한 다음 정상 행을 저장합니다. 따라서 strict 모드의 검증 실패 시에는 저장이 시작되지 않습니다. 다만 저장 단계에서 파일 시스템 오류가 발생하는 경우까지 여러 행의 저장을 하나의 원자적 트랜잭션으로 보장하는 구조는 아닙니다.

---

# 5. 추가 구현 기능

1. **원자적 파일 교체:** 거래 수정·삭제 시 임시 파일 작성 후 `os.replace()`로 교체합니다.
2. **자동 백업:** 거래 파일 교체 직전에 기존 파일을 `.bak`으로 보관합니다.
3. **대체 카테고리:** 사용 중인 카테고리를 삭제할 때 `--replace-with`로 거래 내역을 다른 카테고리로 변경할 수 있습니다.
4. **콘솔 출력 정렬:** 별도 외부 라이브러리 없이 문자열 포맷팅으로 거래 내역의 열을 정렬합니다.

---

# 6. 자동화 테스트

다음 명령어로 테스트를 실행할 수 있습니다.

```bash
python3 -m unittest discover tests
```

실행 결과:
```text
...
----------------------------------------------------------------------
Ran 3 tests in 0.012s

OK
```

현재 테스트는 거래 추가·목록 조회, 사용 중인 카테고리의 대체 삭제, CSV strict 모드에서 검증 실패 시 저장되지 않는 동작을 확인합니다.
