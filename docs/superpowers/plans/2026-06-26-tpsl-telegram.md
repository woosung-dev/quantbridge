<!-- Wave 0 W2 — TelegramAlertService 구현 plan (SlackAlertService 미러, 순수 additive) -->

# Wave 0 W2 — TelegramAlertService (critical alert mirror)

## 목표

Kill Switch / 주문-stuck / WS-orphan 등 critical 이벤트를 텔레그램으로 알리는 `TelegramAlertService` 를 추가한다. 기존 `SlackAlertService`(`common/alert.py`) 를 미러링하되 Telegram Bot API `sendMessage` 로 발송한다. **순수 additive** — `alert.py` / 6 call site / 주문 경로 무수정.

## 제약 (worker-telegram.prompt + spec SSOT § W2)

- demo-only / 실자금 0. `SecretStr` 사용(평문 금지).
- `.env.example` 미등재 환경변수 코드 참조 금지 → 신규 `TELEGRAM_*` 는 `.env.example` 에 먼저 등재.
- migration 0. 신규 Celery task 0.
- 신규 파일 첫줄 한국어 역할주석. 사고/문서 한국어, 네이밍/커밋 영어.
- fan-out(Slack+Telegram 동시) 배선은 **하지 않음** — Orchestrator 후처리 (disjoint 유지).
- TDD 정석(test-first). `tests/common/test_alert.py` 의 `httpx.MockTransport` 패턴 미러.

## 파일 (touch 집합 = `common/` + `core/config.py` + `.env.example` + `tests/common/`)

| 파일 | 변경 |
|------|------|
| `backend/src/common/telegram_alert.py` | **신규** — `TelegramAlertService` + `send_telegram_critical_alert()` |
| `backend/src/core/config.py` | additive — `telegram_bot_token: SecretStr \| None` + `telegram_chat_id: str \| None` + validator |
| `.env.example` | additive — `TELEGRAM_BOT_TOKEN=` + `TELEGRAM_CHAT_ID=` |
| `backend/tests/common/test_telegram_alert.py` | **신규** — MockTransport 미러 |

## 설계 결정

### Telegram Bot API 형태
- 엔드포인트: `https://api.telegram.org/bot<TOKEN>/sendMessage`
- payload: `{"chat_id": <chat_id>, "text": "<severity emoji> [severity] title\nmessage\n<context k:v>"}`
- severity → 이모지: critical=🔴 / warning=🟠 / info=🟢 (Slack 의 color 미러).
- Slack 은 `attachments[].color` 로 severity 를 표기하나 Telegram 은 색 필드 부재 → 텍스트 prefix 이모지로 미러.

### Slack 미러 1:1 대응
- per-call `httpx.AsyncClient`(test 시 inject) — fork-safe.
- module-level `asyncio.Semaphore(8)` burst 상한 — **단, alert.py 의 `_SEND_SEMAPHORE` 와 별도 인스턴스**. §9.2 audit gate 가 신규 module-level Semaphore 를 검출 → allowlist 등재 필요 (아래 참조).
- `asyncio.wait_for(timeout=15s)` stuck 방지.
- `_cap_context` — Telegram `text` 4096자 한도이나 Slack helper 와 동일 cap(20 keys × 500 chars) 재사용 위해 alert.py 의 `_cap_context` 를 import (중복 정의 회피).
- token/chat_id 미설정 → silent skip(False, raise X).
- 503 retry once / 4xx 즉시 fail / RetryError·HTTPError catch → False.

### config validator
- `telegram_bot_token`: 빈 값 → None. 형식 검증 = `<digits>:<alphanumeric>` (BotFather 토큰 형식 `123456789:ABC-DEF...`). Slack 의 prefix 검증 미러.
- `telegram_chat_id`: `str | None`(빈 값 → None). 숫자/`@channel` 양식 모두 허용이라 형식 강제 안 함.

### §9.2 module-level async state audit gate
`tests/tasks/test_no_module_level_loop_bound_state.py` 가 `src/common/*.py` 의 신규 module-level `asyncio.Semaphore` 를 검출할 수 있다. alert.py 만 스캔 대상이면 무관하나, 스캔 범위에 telegram_alert.py 포함 시 `_ALLOWLIST` 에 `("src.common.telegram_alert", "_SEND_SEMAPHORE")` 등재 + §9.2 사유 1줄 필요. **구현 전 audit gate 스캔 범위 확인.**

## TDD 시퀀스

1. RED: `test_telegram_alert.py` 작성 — 성공(200)/미설정-silent-skip/503-retry/4xx-fail/persistent-503/타임아웃/convenience helper/payload 형태.
2. config.py 에 `telegram_bot_token`/`telegram_chat_id` + validator 추가 (test fixture 가 의존).
3. `telegram_alert.py` 구현 → GREEN.
4. `.env.example` 등재.
5. audit gate 스캔 범위 확인 → 필요 시 allowlist 등재.
6. self-verify: `ruff check . && mypy src/ && pytest tests/common -q`. alert.py 회귀 0 확인.

## 검증 (self-verify)
```
cd backend && uv run ruff check . && uv run mypy src/ && python -m pytest tests/common -q
```
- telegram MockTransport test green + alert.py 기존 test 회귀 0.

## 커밋 단위
1. `feat(common): TelegramAlertService (critical alert mirror)` — telegram_alert.py + config + .env.example + tests 일괄(단일 additive 기능 단위).
