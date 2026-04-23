# dart-noti 설계 문서

## 1. 개요

DART(금융감독원 전자공시시스템) OpenAPI를 폴링하여 관심 종목의 새 공시가 등록되면 Telegram 메시지로 알림을 발송하는 애플리케이션입니다.

---

## 2. DART API 분석

### 2.1 공식 API 정보

- **베이스 URL**: `https://opendart.fss.or.kr/api/`
- **인증**: 40자 API 키 (`crtfc_key` 쿼리 파라미터)
- **응답 형식**: JSON 또는 XML 선택 가능
- **공시 목록 엔드포인트**: `GET /api/list.json`

**주요 쿼리 파라미터:**

| 파라미터 | 설명 | 예시 |
|----------|------|------|
| `crtfc_key` | API 인증키 | 40자 문자열 |
| `corp_code` | 고유 종목 코드 | `00126380` |
| `bgn_de` | 시작일 | `20240101` |
| `end_de` | 종료일 | `20241231` |
| `pblntf_ty` | 공시 유형 | `A`, `B`, ... `J` |
| `page_no` | 페이지 번호 | `1` |
| `page_count` | 페이지당 건수 (최대 100) | `100` |
| `sort` | 정렬 기준 | `date` |
| `sort_mth` | 정렬 방향 | `desc` |

### 2.2 요청 한도 (Rate Limit)

| 구분 | 한도 |
|------|------|
| 분당 최대 요청 수 | **1,000건** |
| 초과 시 조치 | 서비스 이용 제한 (에러 코드 020) |
| 1회 조회 최대 건수 | 100건 (page_count) |

**안전한 폴링 주기 계산:**

감시 종목 N개를 폴링할 때 분당 요청 수:

```
분당 요청 수 = N × (60 / 폴링 주기(초))
```

| 종목 수 | 폴링 주기 | 분당 요청 수 | 여유율 |
|---------|----------|-------------|--------|
| 10개    | 60초     | 10건        | 99%    |
| 50개    | 60초     | 50건        | 95%    |
| 100개   | 60초     | 100건       | 90%    |
| 500개   | 60초     | 500건       | 50%    |
| 10개    | 300초    | 2건         | 99.8%  |

→ **권장 폴링 주기: 300초 (5분)**, 종목 수 무관하게 안전.  
→ 실시간성이 중요하다면 60초도 수백 종목까지는 안전.

### 2.3 폴링 vs RSS 비교

DART 웹사이트(`dart.fss.or.kr`)는 **비공식 RSS 피드**를 제공합니다.

- **RSS 엔드포인트**: `https://dart.fss.or.kr/api/todayRSS.xml`
- **인증**: 불필요
- **응답 구조** (item 예시):

```xml
<item>
  <title>(코스닥)알엔티엑스 - [기재정정]주요사항보고서(전환사채권발행결정)</title>
  <link>https://dart.fss.or.kr/api/link.jsp?rcpNo=20260423001234</link>
  <category>코스닥</category>
  <pubDate>Thu, 23 Apr 2026 09:12:00 GMT</pubDate>
  <guid>https://dart.fss.or.kr/api/link.jsp?rcpNo=20260423001234</guid>
  <dc:creator>알엔티엑스</dc:creator>
  <dc:date>2026-04-23T09:12:00Z</dc:date>
</item>
```

| 항목 | REST API 폴링 (OpenDart) | RSS 폴링 (dart.fss.or.kr) |
|------|--------------------------|--------------------------|
| 지원 여부 | ✅ 공식 지원 | ⚠️ 비공식 (변경 위험) |
| 인증 | API 키 필요 | 불필요 |
| 요청 수 | **종목 수만큼 N회/폴링** | **1회/폴링** |
| Rate Limit | 분당 1,000건 | 명시 없음 (부담 없음) |
| 종목 필터링 | API 레벨 (`corp_code`) | **클라이언트에서 종목명 매칭** |
| 공시 범위 | 날짜 범위 지정 가능 | **당일 공시만** |
| 구현 복잡도 | 보통 | 단순 (`feedparser`) |
| 안정성 | 높음 | 낮음 (비공식 URL) |

**결론: RSS + REST API 하이브리드 방식 채택**

```
RSS 폴링 (1건/N초)
  └─ 전체 공시 수신 → 관심 종목명으로 클라이언트 필터링 → Telegram 발송

REST API (보조)
  └─ 앱 시작 시 corp_code ↔ corp_name 매핑 테이블 구축 (초기 1회)
  └─ RSS에서 누락된 공시 보완 필요 시 (향후 확장)
```

- 평상시에는 RSS 1회 요청으로 모든 종목 커버 → API 소모 최소화
- 종목 식별은 RSS `<title>` 또는 `<dc:creator>` 필드의 종목명으로 매칭
- `rcpNo`(link URL에서 추출)를 고유 ID로 사용해 중복 방지
- RSS URL이 변경될 경우 REST API 전용으로 fallback

---

## 3. 아키텍처

### 3.1 레이어 구조

```
┌─────────────────────────────────────────────┐
│                  main.py                     │  진입점 / 시그널 핸들링
└────────────────────┬────────────────────────┘
                     │
┌────────────────────▼────────────────────────┐
│               scheduler.py                  │  asyncio 폴링 루프
└──────┬──────────────────────────┬───────────┘
       │                          │
┌──────▼──────┐            ┌──────▼──────────┐
│ rss.py      │            │  telegram.py     │
│ (RSS 파싱)  │            │  (알림 발송)     │
└──────┬──────┘            └─────────────────┘
       │
┌──────▼──────┐     ┌──────────────────────┐
│ seen.py     │     │ dart.py              │
│ (중복 방지) │     │ (초기 corp 매핑 로드) │
└─────────────┘     └──────────────────────┘
```

### 3.2 데이터 흐름

```
[앱 시작 - 1회]
    └─► [dart.py] load_corp_map(watch_corp_codes)
            └─ dart-fss로 corp_code → corp_name 매핑 테이블 구축

[scheduler] 매 N초마다
    │
    ├─► [rss.py] fetch_and_parse()
    │       └─ https://dart.fss.or.kr/api/todayRSS.xml 요청
    │       └─ feedparser로 파싱 → Disclosure 모델 리스트 반환
    │
    ├─► corp_name으로 관심 종목 필터링 (corp_map 사전 참조)
    │
    ├─► [seen.py] filter_unseen(disclosures)
    │       └─ 이미 발송한 rcp_no 제거
    │
    ├─► [telegram.py] send_notification(disclosure) × 새 공시 수
    │
    └─► [seen.py] mark_seen(rcp_nos)
            └─ JSON 파일에 발송 완료 ID 저장
```

### 3.3 컴포넌트 상세

#### `config.py`
- `pydantic-settings` 기반으로 `.env` 파일에서 설정 로드
- 타입 안전한 설정 모델 (런타임 전 유효성 검사)

```python
class Settings(BaseSettings):
    dart_api_key: str              # corp 매핑 초기 로드용 (dart-fss)
    telegram_bot_token: str
    telegram_chat_id: str
    watch_corp_codes: list[str]    # "00126380,00164779" → ["00126380", "00164779"]
    poll_interval_seconds: int = 300
    store_path: Path = Path("data/seen.json")
```

#### `services/rss.py`
- `https://dart.fss.or.kr/api/todayRSS.xml` 폴링
- `feedparser` 로 파싱 → `Disclosure` 모델 리스트 반환
- `<title>` 또는 `<dc:creator>` 필드로 종목명 추출
- link URL에서 `rcpNo` 추출 → 중복 방지 ID로 사용

#### `services/dart.py`
- 앱 시작 시 `dart-fss`로 `corp_code` → `corp_name` 매핑 테이블 1회 로드
- RSS 파싱 결과의 종목명과 매핑 테이블을 대조하여 관심 종목 여부 판단

#### `services/telegram.py`
- `python-telegram-bot` 비동기 클라이언트 래핑
- 공시 내용을 Telegram Markdown 메시지로 포맷팅
- 발송 실패 시 재시도 로직 (최대 3회)

#### `store/seen.py`
- 발송 완료 공시의 `rcp_no` (접수번호)를 JSON 파일에 영속화
- 재시작 후에도 중복 발송 방지
- 오래된 이력은 설정된 보존 기간(기본 90일) 이후 자동 정리

#### `models/disclosure.py`
- RSS 파싱 결과를 정규화한 Pydantic 모델

```python
class Disclosure(BaseModel):
    rcp_no: str        # 접수번호 (rcpNo 쿼리 파라미터에서 추출)
    corp_name: str     # 회사명 (dc:creator)
    corp_code: str     # 고유 종목 코드 (corp_map 역조회)
    market: str        # 시장 구분 (코스닥/유가/기타, category 필드)
    report_nm: str     # 보고서명 (title에서 파싱)
    rcept_dt: datetime # 접수일시 (pubDate)
    url: str           # 공시 상세 URL (link)
```

---

## 4. 폴링 전략 상세

### 4.1 폴링 흐름

```
앱 시작
 │
 ├─ 초기화: dart-fss로 corp_code → corp_name 매핑 테이블 구축 (1회)
 │
 └─ 루프:
      ├─ RSS 피드 1회 요청 (전체 당일 공시 수신)
      ├─ 관심 종목명으로 클라이언트 필터링
      ├─ seen.py로 중복 제거
      ├─ 새 공시 → Telegram 발송
      ├─ 발송 완료 rcp_no 저장
      └─ poll_interval초 대기
```

### 4.2 RSS vs REST API 요청 수 비교

| 방식 | 종목 10개 | 종목 100개 | 종목 500개 |
|------|----------|-----------|-----------|
| REST API 폴링 | 10건/폴링 | 100건/폴링 | 500건/폴링 |
| **RSS 폴링** | **1건/폴링** | **1건/폴링** | **1건/폴링** |

RSS 방식은 종목 수와 무관하게 폴링당 1건만 요청합니다.

**300초 주기 기준 분당 요청 수:**
- REST API (100종목): 100 × (60/300) = **20건/분**
- RSS: 1 × (60/300) = **0.2건/분**

### 4.3 에러 처리 및 백오프

| 에러 상황 | 처리 방식 |
|----------|----------|
| RSS 네트워크 타임아웃 | 지수 백오프 후 재시도 (최대 3회) |
| RSS URL 변경/장애 | 로그 경고 + REST API fallback |
| API 키 오류 (에러 010) | 앱 종료 + 로그 |
| Telegram 발송 실패 | 재시도 3회, 실패 시 로그만 기록 |

---

## 5. 폴더 구조

```
dart_noti/
├── pyproject.toml
├── .python-version          # "3.12"
├── .env.example
├── .env                     # (gitignore)
├── .gitignore
├── README.md
├── docs/
│   └── design.md            # 이 문서
├── src/
│   └── dart_noti/
│       ├── __init__.py
│       ├── main.py          # 진입점: 설정 로드, 스케줄러 시작, 시그널 처리
│       ├── config.py        # pydantic-settings 설정 모델
│       ├── scheduler.py     # asyncio 폴링 루프
│       ├── services/
│       │   ├── __init__.py
│       │   ├── dart.py      # dart-fss 래핑, 공시 조회
│       │   └── telegram.py  # Telegram Bot API 래핑
│       ├── models/
│       │   ├── __init__.py
│       │   └── disclosure.py
│       └── store/
│           ├── __init__.py
│           └── seen.py      # 발송 이력 영속화
├── data/                    # 런타임 데이터 (gitignore)
│   └── seen.json
└── tests/
    ├── conftest.py
    ├── test_dart_service.py
    └── test_telegram_service.py
```

---

## 6. 의존성

| 패키지 | 역할 | 비고 |
|--------|------|------|
| `dart-fss` | DART OpenAPI 래핑 | 초기 corp 매핑 로드용 |
| `xml.etree.ElementTree` | RSS 파싱 | stdlib, 추가 의존성 없음 |
| `python-telegram-bot` | Telegram Bot API | 비동기 지원 (`v20+`) |
| `pydantic-settings` | 환경변수 기반 설정 | 타입 검증 포함 |
| `loguru` | 구조화 로깅 | 설정 간편 |
| `pytest` | 테스트 | dev 의존성 |
| `pytest-asyncio` | 비동기 테스트 | dev 의존성 |

---

## 7. 확장 고려사항 (현재 범위 외)

- **웹훅 모드**: Telegram Bot을 polling 대신 webhook으로 운영 (VPS 필요)
- **다중 채팅방**: 종목별로 다른 Telegram 채팅방에 발송
- **공시 유형별 필터링**: 사용자별 관심 공시 유형 설정
- **DB 스토리지**: 발송 이력을 JSON 대신 SQLite로 관리 (대규모 이력)
- **모니터링**: Prometheus 메트릭 노출, Grafana 대시보드
