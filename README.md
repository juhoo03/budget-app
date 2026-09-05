# 💰 나만의 용돈 기입장 콘솔 서비스 (Budget App)[cite: 1]

Python 표준 라이브러리만을 활용하여 파일 기반 영구 저장, 제너레이터 스트리밍, 데코레이터 패턴, 원자적 파일 교체(Atomic Write)를 구현한 콘솔 가계부 애플리케이션입니다[cite: 1].

---

## 📸 제출 및 증빙을 위한 필수 캡처 항목 가이드[cite: 1]

과제 평가 시 신뢰도와 완성도 증빙을 위해 권장되는 실제 터미널 실행 캡처 항목입니다[cite: 1].

1. **자동화 테스트 통과 화면**: `python -m unittest discover tests` 실행 후 `OK` 출력 화면
2. **거래 추가(대화형) 및 ID 발급**: `add` 실행을 통한 `TX-000001`, `TX-000002` 순차 저장 화면[cite: 1]
3. **정렬된 목록 조회**: `list` 실행 시 최신순 역순 정렬 및 컬럼 테이블 포맷팅 출력 화면[cite: 1]
4. **월별 요약 및 예산 연동**: `summary --month 2026-09` 실행 시 수입/지출/잔액 및 예산 사용률(%) 출력 화면[cite: 1]
5. **다양한 조건 검색**: `search --category 식비` 및 `search --q 점심` 필터링 스트리밍 결과 화면[cite: 1]
6. **데코레이터 동작 증빙**: `BUDGET_DEBUG=1` 환경변수 주입 시 소요 시간(`0.10ms`) 디버그 출력 화면[cite: 1]

---

## 📌 1. 주요 특징 및 아키텍처[cite: 1]

- **외부 의존성 제로 (Zero-Dependency)**: 외부 라이브러리(`pip`) 설치 없이 Python 3.10+ 표준 라이브러리만으로 동작합니다[cite: 1].
- **메모리 절감 스트리밍**: 대용량 파일도 안정적으로 다룰 수 있도록 `yield` 기반 제너레이터 및 `heapq.nlargest` 스트리밍 방식을 적용해 상위 N건만 메모리에 유지합니다[cite: 1].
- **원자적(Atomic) 파일 교체 및 백업 보존**: 수정/삭제 시 임시 파일(`tempfile`) 작성 -> `fsync` -> 직전 버전 백업(`.bak`) -> 원자적 교체(`os.replace`)를 수행하여 무결성을 보장합니다[cite: 1].
- **공통 관심사 분리 (데코레이터 패턴)**: 스택트레이스를 차단하는 예외 처리(`@handle_cli_errors`), 디버그 로깅(`@log_execution`), 소요 시간 측정(`@measure_time`) 데코레이터를 적용했습니다[cite: 1].
- **리눅스 표준 CLI 규격**: 모든 명령어는 `--help` 도움말을 지원하며 리눅스 표준인 `--` 접두사 옵션 표기법을 준수합니다[cite: 1].
- **데이터 무결성 방어 및 트랜잭션 Import**: 사용 중인 카테고리 삭제 방지 및 `--replace-with` 일괄 대체 기능을 지원하며, CSV 임포트 시 `--strict` 롤백 모드를 제공합니다[cite: 1].

---

## 📂 2. 프로젝트 디렉터리 구조[cite: 1]

    my_project/
    ├── .gitignore                  # Git 추적 제외 설정 (data/, __pycache__/ 등)
    ├── README.md                   # 프로젝트 통합 문서
    ├── data/                       # 영구 저장 데이터 디렉터리 (기본값)[cite: 1]
    │   ├── transactions.jsonl      # 거래 내역 파일[cite: 1]
    │   ├── categories.jsonl        # 카테고리 목록 파일 (기본 한글 카테고리)[cite: 1]
    │   └── budgets.jsonl           # 월별 목표 예산 파일[cite: 1]
    ├── budget_app/                 # 애플리케이션 핵심 패키지
    │   ├── __init__.py             # 패키지 초기화
    │   ├── __main__.py             # python -m budget_app 진입점[cite: 1]
    │   ├── models.py               # Transaction, Budget 데이터 모델 (dataclass)[cite: 1]
    │   ├── decorators.py           # 공통 데코레이터 (예외/로깅/시간측정)[cite: 1]
    │   ├── storage.py              # 파일 I/O 및 스트리밍 저장소 관리[cite: 1]
    │   ├── services.py             # CRUD 및 비즈니스 검증 로직[cite: 1]
    │   └── cli.py                  # CLI 인수 파싱 및 콘솔 UI 포맷터[cite: 1]
    └── tests/                      # 자동화 테스트 스위트
        ├── __init__.py
        └── test_app.py             # unittest 기반 단위 및 통합 테스트

---

## 🏛 3. 계층별 모듈 및 공개 API 명세[cite: 1]

애플리케이션은 **Model -> Storage -> Service -> CLI** 계층 구조로 책임을 분리했습니다[cite: 1].

| 계층 (Layer) | 파일명 | 클래스 / 주요 함수 | 책임 및 주요 계약[cite: 1] |
| :--- | :--- | :--- | :--- |
| **Model** | `models.py` | `Transaction`<br>`Budget` | 데이터 구조 정의, 필드 유효성 타입 정의, 딕셔너리 직렬화/역직렬화 계약 (`to_dict`, `from_dict`)[cite: 1] |
| **Storage** | `storage.py` | `StorageManager` | 3대 JSONL 파일 영구 저장, `yield` 스트리밍 로드, 원자적 교체 및 `.bak` 백업 보존[cite: 1] |
| **Service** | `services.py` | `BudgetService` | 비즈니스 검증, 유일 ID 발급, 통계 집계, 카테고리 일괄 대체, CSV 입출력 트랜잭션[cite: 1] |
| **Decorator** | `decorators.py` | `@handle_cli_errors`<br>`@log_execution`<br>`@measure_time` | 스택트레이스 숨김 및 종료코드 제어, 디버그 로깅 출력, 실행 시간(ms) 측정[cite: 1] |
| **CLI** | `cli.py` | `run_cli()` | `argparse` 기반 옵션 파싱, 대화형(`input()`) UI 흐름 제어, 콘솔 테이블 문자열 정렬 포맷팅[cite: 1] |

---

## 💾 4. 영구 저장소 정책 및 포맷 비교[cite: 1]

### 저장 파일 위치 및 초기화 정책[cite: 1]
- **저장 위치**: 기본 경로는 `./data/`이며, 실행 시 `--data-dir <경로>` 옵션으로 변경 가능합니다[cite: 1].
- **초기 실행**: 저장 폴더나 파일이 없는 경우 자동 생성되며, `categories.jsonl`이 비어 있는 경우 `식비`, `교통`, `월급`, `주거`, `여가`, `기타` 기본 카테고리가 자동 생성됩니다[cite: 1].

### 저장 포맷 비교: JSON Lines vs CSV[cite: 1]

| 비교 항목 | JSON Lines (`.jsonl`) [내부 저장 채택][cite: 1] | CSV (`.csv`) [외부 교환 채택][cite: 1] |
| :--- | :--- | :--- |
| **스트리밍 적합성** | 개별 라인이 독립된 JSON 객체이므로 라인 단위 읽기/쓰기가 직관적 | 필드 내 개행 문자가 포함될 경우 단순 라인 분리 불가 |
| **스키마 유연성** | 태그 리스트(`tags`) 등 다차원 데이터를 표준적으로 직렬화 가능 | 다중 태그 표현 시 내부 구분자(쉼표 등) 파싱 필요 |
| **장애 격리성** | 특정 행 손상 시에도 다른 레코드에 영향 없이 해당 행만 스킵 가능 | 헤더 손상 또는 컬럼 개수 불일치 시 파서 전체 실패 위험 |
| **호환 및 편집성** | 텍스트 에디터 확인은 용이하나 일반 스프레드시트 호환성 낮음 | Excel, Google Sheets 등 일반 스프레드시트 도구에서 즉시 열람 및 편집 가능 |

---

## 🔒 5. 데이터 보안, 백업 및 예산 알림 정책[cite: 1]

- **파일 보안 및 권한**: 데이터 디렉터리(`data/`) 및 파일은 실행 계정 권한(Unix 기준 `0600` / `0700` 권장)으로 보호됩니다.
- **백업 보존 전략**: 거래 내역 수정/삭제 시 기존 원본을 `transactions.jsonl.bak`으로 백업 후 원자적 교체를 진행합니다[cite: 1].
- **예산 초과 알림 정책**: `summary` 실행 시 설정 예산 대비 지출 사용률(%)을 출력하며, 100% 초과 시 `[경고: 예산 초과! 콘솔 알림]` 문구를 표기합니다[cite: 1].
- **종료 코드(Exit Code) 정책**:
  - `0`: 정상 실행 완료[cite: 1]
  - `1`: 사용자 입력 오류, 유효성 검증 실패, 비즈니스 규칙 위반 (스택트레이스 차단, 원인 및 해결 힌트 출력)[cite: 1]
  - `2`: 예기치 않은 런타임 시스템 예외

---

## ⚡ 6. 100k+ 대용량 데이터 발생 시 병목 분석 및 아키텍처 개선안

1. **Top-N 정렬 병목 (CPU 및 메모리)**
   - *현상*: 전체 레코드를 메모리에 적재 후 정렬 시 $O(N \log N)$ 소요 및 메모리 스파이크 발생.
   - *현 구현 최적화*: `heapq.nlargest` 기반 상위 N개($O(N \log K)$) 힙 스트리밍 적용 완료.
   - *추후 개선안*: 연/월 단위 폴더 파티셔닝(`data/YYYY/MM/`) 도입.
2. **선형 탐색 병목 ($O(N)$ 디스크 I/O)**
   - *현상*: ID 조회나 키워드 검색 시 10만 줄 전체 순차 스캔 필요.
   - *추후 개선안*: `TX-ID -> Byte Offset` 인덱스 파일(`transactions.idx`) 구축 또는 SQLite/DuckDB 마이그레이션.
3. **파일 전체 재작성 병목 (수정/삭제 시)**
   - *현상*: 1건 수정 시에도 10만 건 전체 재기록 발생.
   - *추후 개선안*: Append-Only 로그 아키텍처 및 주기적 Compaction(압축) 프로세스 도입.

---

## 🚀 7. 실행 방법 및 실제 터미널 실행 로그[cite: 1]

실제 환경에서 주요 기능을 순차적으로 실행하여 검증한 실제 터미널 입출력 로그입니다[cite: 1].

### 1단계. 거래 내역 추가 (`add` - 지출 및 수입)[cite: 1]
대화형 프롬프트를 통해 지출과 수입 내역을 순차 등록하고 고유 식별자(`TX-XXXXXX`)를 발급받습니다[cite: 1].

    % python -m budget_app add
    --- 거래 내역 추가 (대화형) ---
    날짜(YYYY-MM-DD): 2026-09-04
    타입(income/expense): expense
    카테고리: 식비
    금액(양수): 12000
    메모(선택): 점심
    태그(쉼표로 구분, 없으면 엔터): 점심,외식
    [저장 완료] id=TX-000001

    % python -m budget_app add
    --- 거래 내역 추가 (대화형) ---
    날짜(YYYY-MM-DD): 2026-09-05
    타입(income/expense): income
    카테고리: 월급
    금액(양수): 100000
    메모(선택): 장학금
    태그(쉼표로 구분, 없으면 엔터): 장학금
    [저장 완료] id=TX-000002

### 2단계. 거래 목록 최신순 조회 (`list`)[cite: 1]
스트리밍 방식으로 최신 거래부터 테이블 정렬 포맷으로 출력합니다[cite: 1].

    % python -m budget_app list
    TX-000002 | 2026-09-05 | income  | 월급       |   100000원 | 장학금          [장학금]
    TX-000001 | 2026-09-04 | expense | 식비       |    12000원 | 점심            [점심, 외식]

### 3단계. 예산 필수 인자 누락 검증 및 설정 (`budget set`)[cite: 1]
필수 인자 누락 시 argparse 표준 도움말이 출력되며, 정상 입력 시 월별 예산이 등록됩니다[cite: 1].

    # 필수 인자 누락 시 안내[cite: 1]
    % python -m budget_app budget set
    usage: python -m budget_app budget set [-h] --month MONTH --amount AMOUNT
    python -m budget_app budget set: error: the following arguments are required: --month, --amount

    # 정상 예산 설정 등록[cite: 1]
    % python -m budget_app budget set --month 2026-09 --amount 500000
    [저장 완료] 2026-09 예산 500000원

### 4단계. 월별 요약 및 예산 사용률 조회 (`summary`)[cite: 1]
총 수입, 총 지출, 잔액과 설정 예산 대비 지출 사용률(%) 및 카테고리 TOP 순위를 집계합니다[cite: 1].

    % python -m budget_app summary --month 2026-09
    총 수입: 100,000원
    총 지출: 12,000원
    잔액: 88,000원
    예산: 500,000원 (사용률 2.4%)
    지출 TOP 1
    1) 식비 12,000원

### 5단계. 조건별 거래 검색 (`search`)[cite: 1]
카테고리 필터링 및 메모 키워드 검색을 제너레이터 스트리밍으로 지연 평가하여 출력합니다[cite: 1].

    # 카테고리 조건 검색[cite: 1]
    % python -m budget_app search --category 식비
    TX-000001 | 2026-09-04 | expense | 식비       |    12000원 | 점심            [점심, 외식]

    # 키워드 질의 검색[cite: 1]
    % python -m budget_app search --q 점심
    TX-000001 | 2026-09-04 | expense | 식비       |    12000원 | 점심            [점심, 외식]

### 6단계. 데코레이터 동작 검증 (`@measure_time`)[cite: 1]
`BUDGET_DEBUG=1` 환경변수 활성화 시 데코레이터에 의한 밀리초 단위 실행 시간 측정이 출력됩니다[cite: 1].

    % BUDGET_DEBUG=1 python -m budget_app list 
    [DEBUG] 'list_transactions' 실행 소요 시간: 0.10ms
    TX-000002 | 2026-09-05 | income  | 월급       |   100000원 | 장학금          [장학금]
    TX-000001 | 2026-09-04 | expense | 식비       |    12000원 | 점심            [점심, 외식]

---

## 📊 8. CSV 가져오기 / 내보내기 스키마[cite: 1]

UTF-8 인코딩 및 첫 줄 헤더를 필수로 포함합니다[cite: 1].

| Column | Required | Type / Description |
| :--- | :---: | :--- |
| `date` | Y | `YYYY-MM-DD` 형식 날짜[cite: 1] |
| `type` | Y | `income` 또는 `expense`[cite: 1] |
| `category` | Y | 등록된 카테고리명[cite: 1] |
| `amount` | Y | 양의 정수 (1원 이상)[cite: 1] |
| `memo` | N | 메모 문자열 (선택)[cite: 1] |
| `tags` | N | 쉼표(`,`)로 구분된 태그 목록 (선택)[cite: 1] |

*명령어 예시:*[cite: 1]
    # 특정 월 내보내기[cite: 1]
    python -m budget_app export --out export_202609.csv --month 2026-09

    # 기본 가져오기 (오류 행 스킵 모드)[cite: 1]
    python -m budget_app import --from data.csv

    # 트랜잭션 가져오기 (단 1건이라도 오류 시 전체 롤백)
    python -m budget_app import --from data.csv --strict

---

## 🧪 9. 자동화 테스트 실행

표준 라이브러리 `unittest`를 기반으로 거래 CRUD, 카테고리 방어 및 일괄 대체, 트랜잭션 임포트 롤백 기능을 검증합니다.

    python -m unittest discover tests