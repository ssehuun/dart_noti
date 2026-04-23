# dart-noti

DART(금융감독원 전자공시) 공시를 모니터링하고, 새 공시 발생 시 Telegram으로 알림을 보내는 파이썬 애플리케이션입니다.

## 요구사항

- Python 3.12
- [uv](https://docs.astral.sh/uv/) (패키지 및 가상환경 관리)
- DART OpenAPI 키: [opendart.fss.or.kr](https://opendart.fss.or.kr) 에서 발급
- Telegram Bot Token: [@BotFather](https://t.me/BotFather) 에서 발급
- Telegram Chat ID: 알림을 받을 채팅방 ID

## 설치

```bash
# 저장소 클론
git clone <repo-url>
cd dart_noti

# Python 버전 고정 및 가상환경 생성
uv python pin 3.12
uv sync

# 환경변수 설정
cp .env.example .env
# .env 파일을 열어 DART_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID 입력
```

## 환경변수

`.env.example` 참고:

| 변수명 | 필수 | 설명 |
|--------|------|------|
| `DART_API_KEY` | ✅ | DART OpenAPI 인증키 (40자) |
| `TELEGRAM_BOT_TOKEN` | ✅ | Telegram Bot 토큰 |
| `TELEGRAM_CHAT_ID` | ✅ | 알림 수신 채팅방 ID |
| `WATCH_CORP_CODES` | ✅ | 감시할 종목 corp_code 목록 (쉼표 구분) |
| `WATCH_DISCLOSURE_TYPES` | | 감시할 공시 유형 (기본: 전체, 예: `A,B`) |
| `POLL_INTERVAL_SECONDS` | | 폴링 주기 초 (기본: `300`) |
| `STORE_PATH` | | 발송 이력 저장 경로 (기본: `data/seen.json`) |

### 공시 유형 코드 (`WATCH_DISCLOSURE_TYPES`)

| 코드 | 유형 |
|------|------|
| `A` | 정기공시 |
| `B` | 주요사항보고 |
| `C` | 발행공시 |
| `D` | 지분공시 |
| `E` | 기타공시 |
| `F` | 외부감사 관련 |
| `G` | 펀드공시 |
| `H` | 자산유동화 |
| `I` | 거래소공시 |
| `J` | 공정위공시 |

### corp_code 조회 방법

```python
import dart_fss as dart

dart.set_api_key("YOUR_DART_API_KEY")
corp_list = dart.get_corp_list()

# 종목명으로 검색
samsung = corp_list.find_by_corp_name("삼성전자", exactly=True)[0]
print(samsung.corp_code)  # 예: 00126380
```

## 실행

```bash
# 직접 실행
uv run python -m dart_noti.main

# 또는 스크립트 엔트리포인트 사용 (pyproject.toml에 정의된 경우)
uv run dart-noti
```

## 개발

```bash
# 개발 의존성 포함 설치
uv sync --group dev

# 테스트 실행
uv run pytest

# 특정 테스트만 실행
uv run pytest tests/test_dart_service.py -v
```

## 프로젝트 구조

```
dart_noti/
├── pyproject.toml
├── .python-version
├── .env.example
├── README.md
├── docs/
│   └── design.md           # 설계 문서
├── src/
│   └── dart_noti/
│       ├── __init__.py
│       ├── main.py         # 진입점
│       ├── config.py       # 환경변수 기반 설정
│       ├── scheduler.py    # asyncio 폴링 루프
│       ├── services/
│       │   ├── dart.py     # dart-fss 래핑
│       │   └── telegram.py # Telegram 알림 발송
│       ├── models/
│       │   └── disclosure.py
│       └── store/
│           └── seen.py     # 발송 이력 관리 (중복 방지)
├── data/                   # 런타임 데이터 (gitignore)
│   └── seen.json
└── tests/
    ├── conftest.py
    ├── test_dart_service.py
    └── test_telegram_service.py
```

## 주의사항

- DART OpenAPI 요청 한도는 **분당 1,000건**입니다. 기본 폴링 주기(300초)는 이 한도를 크게 밑돕니다.
- `data/seen.json` 은 `.gitignore`에 추가하세요 (개인 공시 수신 이력).
- `.env` 파일은 절대 커밋하지 마세요.
