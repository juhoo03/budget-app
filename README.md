# 💰 Budget App

Python 표준 라이브러리만을 활용하여 구현한 파일 기반 콘솔 가계부 애플리케이션입니다.

거래 내역, 카테고리, 월별 예산을 파일에 영구 저장하며,
Generator 기반 스트리밍 처리와 Atomic File Replacement를 적용했습니다.

---

## 🎯 Project Goal

이 프로젝트는 단순한 콘솔 가계부 구현을 넘어 Python 표준 라이브러리를 활용하여
실제 애플리케이션에서 필요한 데이터 저장, 계층 분리, 예외 처리,
데이터 무결성 등을 직접 구현하는 것을 목표로 합니다.

주요 목표:

- 파일 기반 영구 저장소 설계
- JSONL 데이터 포맷 활용
- Generator 기반 스트리밍 처리
- CRUD 및 Service Layer 분리
- Decorator Pattern을 활용한 공통 예외 처리
- Atomic File Replacement를 통한 데이터 무결성 확보
- CLI 애플리케이션 설계
- CSV Import / Export
- 입력값 및 비즈니스 규칙 검증

---

## ✨ 주요 기능

- 거래 추가 / 조회 / 검색 / 수정 / 삭제
- 카테고리 추가 / 조회 / 삭제
- 월별 예산 설정
- 월별 수입 / 지출 / 잔액 요약
- 지출 카테고리 TOP N 분석
- 기간 / 카테고리 / 타입 / 키워드 / 태그 검색
- CSV Import / Export
- 사용자 친화적인 예외 처리
- 모든 명령어 `--help` 지원

---

## 🛠️ 기술 스택

| 기술 | 용도 |
|---|---|
| Python 3.10+ | 애플리케이션 구현 |
| `argparse` | CLI 명령어 및 옵션 처리 |
| `dataclasses` | 데이터 모델 정의 |
| `json` | JSONL 직렬화 / 역직렬화 |
| `csv` | CSV Import / Export |
| `tempfile` | 임시 파일 생성 |
| `os.replace()` | 원자적 파일 교체 |
| Generator | 스트리밍 데이터 처리 |

외부 라이브러리를 사용하지 않고 Python Standard Library만으로 구현했습니다.

---

## 📂 Project Structure

    my_project/
    ├── README.md
    ├── data/
    │   ├── transactions.jsonl
    │   ├── categories.jsonl
    │   └── budgets.jsonl
    └── budget_app/
        ├── __init__.py
        ├── __main__.py
        ├── models.py
        ├── decorators.py
        ├── storage.py
        ├── services.py
        └── cli.py

### 파일별 역할

| 파일 | 역할 |
|---|---|
| `__init__.py` | Python 패키지 초기화 |
| `__main__.py` | `python -m budget_app` 실행 진입점 |
| `models.py` | `Transaction`, `Budget` 등의 데이터 모델 정의 |
| `decorators.py` | 공통 예외 처리 및 로깅 |
| `storage.py` | JSONL 파일 저장 / 조회 및 스트리밍 처리 |
| `services.py` | CRUD 및 비즈니스 규칙 처리 |
| `cli.py` | CLI 명령어 파싱 및 사용자 인터페이스 |

애플리케이션은 **CLI → Service → Storage** 구조로 계층을 분리했습니다.

    ┌───────────────┐
    │      CLI      │
    │    cli.py     │
    └───────┬───────┘
            │
            ▼
    ┌───────────────┐
    │   Services    │
    │  services.py  │
    └───────┬───────┘
            │
       ┌────┴────┐
       ▼         ▼
    Models    Storage
                 │
                 ▼
               JSONL

---

# 🚀 Getting Started

## Requirements

- Python 3.10+
- Python Standard Library
- 별도의 패키지 설치 불필요

Python 버전 확인:

    python --version

프로젝트 상위 디렉터리에서 실행합니다.

    python -m budget_app

전체 도움말:

    python -m budget_app --help

각 명령어별 도움말도 확인할 수 있습니다.

    python -m budget_app add --help
    python -m budget_app list --help
    python -m budget_app search --help
    python -m budget_app budget --help
    python -m budget_app summary --help
    python -m budget_app category --help
    python -m budget_app update --help
    python -m budget_app delete --help
    python -m budget_app export --help
    python -m budget_app import --help

---

# 📋 Usage

## 1. 거래 추가

대화형 프롬프트를 통해 거래 정보를 입력합니다.

    python -m budget_app add

### 실행 예시

    --- 거래 내역 추가 (대화형) ---
    날짜(YYYY-MM-DD): 2024-01-15
    타입(income/expense): expense
    카테고리: food
    금액(양수): 15000
    메모(선택): 점심 식사
    태그(쉼표로 구분, 없으면 엔터): meal,런치
    [저장 완료] id=TX-000001

거래가 저장되면 `TX-000001`과 같은 고유 ID가 생성됩니다.

---

## 2. 거래 목록 조회

    python -m budget_app list

기본적으로 최근 거래 10건을 조회합니다.

조회 개수 지정:

    python -m budget_app list --limit 5

거래 데이터는 Generator를 통해 순차적으로 읽습니다.

---

## 3. 거래 검색

기간, 카테고리, 타입, 메모, 태그 등을 기준으로 검색할 수 있습니다.

### 기간 + 카테고리

    python -m budget_app search \
      --category food \
      --from 2024-01-01 \
      --to 2024-01-31

### 메모 키워드

    python -m budget_app search --q 점심

### 태그

    python -m budget_app search --tag meal

---

## 4. 예산 설정

월별 지출 목표 예산을 설정합니다.

    python -m budget_app budget set \
      --month 2024-01 \
      --amount 500000

설정된 예산은 `budgets.jsonl`에 저장되며,
월별 요약에서 예산 사용률과 초과 여부를 확인할 수 있습니다.

---

## 5. 월별 요약

특정 월의 수입, 지출, 잔액 및 지출 상위 카테고리를 확인합니다.

    python -m budget_app summary \
      --month 2024-01 \
      --top 3

### 출력 예시

    총 수입: 3,000,000원
    총 지출: 215,000원
    잔액: 2,785,000원
    예산: 500,000원 (사용률 43.0%)

    지출 TOP 3
    1) rent 150,000원
    2) food 45,000원
    3) transport 20,000원

---

## 6. 카테고리 관리

카테고리 목록 조회, 추가, 삭제를 지원합니다.

### 목록 조회

    python -m budget_app category list

### 카테고리 추가

    python -m budget_app category add health

### 카테고리 삭제

    python -m budget_app category remove health

현재 거래에서 사용 중인 카테고리는 삭제할 수 없도록 검증합니다.

---

## 7. 거래 수정

기존 거래의 특정 필드를 수정할 수 있습니다.

    python -m budget_app update \
      --id TX-000001 \
      --amount 18000 \
      --memo "점심(특식)"

필요한 필드만 지정하여 부분 수정할 수 있습니다.

---

## 8. 거래 삭제

거래 ID를 지정하여 특정 거래를 삭제합니다.

    python -m budget_app delete \
      --id TX-000001

수정 및 삭제 작업은 Atomic File Replacement 방식으로 처리합니다.

---

# 💾 Data Storage

기본 데이터 저장 위치는 `./data/`입니다.

    data/
    ├── transactions.jsonl
    ├── categories.jsonl
    └── budgets.jsonl

`--data-dir` 옵션을 사용하여 저장 위치를 변경할 수 있습니다.

    python -m budget_app --data-dir ./my-data

### JSONL을 사용하는 이유

각 거래를 하나의 JSON 객체로 저장하는 JSON Lines 형식을 사용합니다.

    {"id": "TX-000001", "date": "2024-01-15", ...}
    {"id": "TX-000002", "date": "2024-01-16", ...}

레코드 단위로 데이터를 처리할 수 있기 때문에
Generator 기반 스트리밍 처리에 적합합니다.

---

# ⚡ Generator Streaming

거래 데이터를 한 번에 모두 메모리에 올리는 대신
Generator를 사용하여 순차적으로 읽습니다.

    def stream_transactions():
        with open("transactions.jsonl", encoding="utf-8") as file:
            for line in file:
                yield transaction

이를 통해 거래 데이터가 많아져도 전체 데이터를 메모리에 적재하지 않고 처리할 수 있습니다.

---

# 🔒 Atomic File Replacement

거래 수정 및 삭제 시 기존 파일을 직접 수정하지 않습니다.

임시 파일에 변경된 데이터를 먼저 작성한 후
`os.replace()`를 사용하여 기존 파일을 교체합니다.

    기존 파일
       │
       ▼
    임시 파일 생성
       │
       ▼
    변경된 데이터 작성
       │
       ▼
    os.replace()
       │
       ▼
    새로운 파일

사용하는 주요 API:

    tempfile.NamedTemporaryFile
    os.replace

이 방식을 통해 파일을 수정하는 도중 프로그램이 종료되더라도
기존 파일이 중간 상태로 변경되는 문제를 줄일 수 있습니다.

---

# 🛡️ Exception Handling

잘못된 입력이나 파일 처리 과정에서 오류가 발생하더라도
내부 스택트레이스를 그대로 노출하지 않습니다.

데코레이터를 통해 사용자에게 이해하기 쉬운 오류 메시지를 제공합니다.

    [오류] 존재하지 않는 카테고리입니다: coffee
    [힌트] 먼저 'category add coffee' 명령으로 카테고리를 추가해주세요.

공통 예외 처리 로직을 데코레이터로 분리하여
각 CLI 명령에서 일관된 오류 처리가 이루어지도록 구성했습니다.

---

# 📊 CSV Import / Export

대량의 거래 데이터를 CSV 파일로 가져오거나 내보낼 수 있습니다.

## CSV Format

| Column | Required | Description |
|---|:---:|---|
| `date` | Y | `YYYY-MM-DD` 형식 |
| `type` | Y | `income` 또는 `expense` |
| `category` | Y | 등록된 카테고리 |
| `amount` | Y | 1 이상의 양의 정수 |
| `memo` | N | 메모 |
| `tags` | N | 쉼표로 구분된 태그 |

## Export

### 특정 월

    python -m budget_app export \
      --out export_202401.csv \
      --month 2024-01

### 특정 기간

    python -m budget_app export \
      --out export_range.csv \
      --from 2024-01-01 \
      --to 2024-01-15

## Import

    python -m budget_app import \
      --from import_data.csv

Import 과정에서 다음 항목을 검증합니다.

- 필수 컬럼 존재 여부
- 날짜 형식
- 거래 타입
- 카테고리 존재 여부
- 금액 형식

---

# 📋 Command Summary

| Command | 기능 |
|---|---|
| `add` | 거래 추가 |
| `list` | 거래 목록 조회 |
| `search` | 거래 검색 |
| `budget set` | 월별 예산 설정 |
| `summary` | 월별 요약 |
| `category list` | 카테고리 조회 |
| `category add` | 카테고리 추가 |
| `category remove` | 카테고리 삭제 |
| `update` | 거래 수정 |
| `delete` | 거래 삭제 |
| `export` | CSV 내보내기 |
| `import` | CSV 가져오기 |

---

# 🔄 기본 사용 흐름

처음 사용하는 경우 다음 순서로 사용할 수 있습니다.

    # 1. 도움말 확인
    python -m budget_app --help

    # 2. 카테고리 확인
    python -m budget_app category list

    # 3. 필요한 카테고리 추가
    python -m budget_app category add health

    # 4. 거래 추가
    python -m budget_app add

    # 5. 거래 목록 확인
    python -m budget_app list

    # 6. 월별 예산 설정
    python -m budget_app budget set \
      --month 2024-01 \
      --amount 500000

    # 7. 월별 리포트 확인
    python -m budget_app summary \
      --month 2024-01 \
      --top 3

---

## 📄 License

개인 학습 및 포트폴리오 목적으로 제작되었습니다.
