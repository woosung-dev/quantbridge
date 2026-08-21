# Step 0: waitlist-services

## 읽어야 할 파일

- `apps/api/src/waitlist/token_service.py` (104줄) — **대상 ①** (HMAC 초대 토큰)
- `apps/api/src/waitlist/email_service.py` (135줄) — **대상 ②** (Resend 발송)
- `apps/api/src/waitlist/service.py` (113줄) — **대상 ③** (도메인 조립)
- `apps/api/src/waitlist/exceptions.py` — `DuplicateEmailError` · `WaitlistNotFoundError` ·
  `EmailSendError` · `InviteTokenInvalidError` · `InviteTokenExpiredError` (**이름을 파일에서 확인해라**)
- `apps/api/tests/waitlist/test_invite_token.py` — 기존 토큰 테스트. **먼저 읽고 겹치는 축은 겨누지 마라**
- `apps/api/tests/waitlist/test_waitlist_commits.py` · `test_email_from_address_wiring.py` — 기존 커버 범위

## 배경

★★**착수 전 CONTROL 이 전량 스위트 커버리지로 쟀다 (2026-08-21 · `concurrency=greenlet,thread` 교정본):**

```
src/waitlist/token_service.py   58 stmt   8 missed   85%   50, 75-76, 81-82, 90-91, 97
src/waitlist/email_service.py   46 stmt   8 missed   80%   62-66, 85, 109-112, 115
src/waitlist/service.py         53 stmt  10 missed   80%   75-78, 86-90, 104-107
```

★★★**미커버 26줄이 거의 전부 「실패 경로」다 — 그리고 토큰 쪽은 보안 경계다.**

| 모듈            | 미커버가 무엇인가                                                                                                                                                         |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `token_service` | ★**위조 토큰 거부 갈래 4종이 전부 미커버**: 구조 오류(75-76) · base64 오류(81-82) · JSON 오류(90-91) · **타입 오류(97)** + 짧은 secret 거부(50)                           |
| `email_service` | 영구 실패 4xx → `EmailSendError`(62-66) · 빈 API key → `ValueError`(85) · retryable/transport → `EmailSendError`(109-112) · **소유한 client 를 `finally` 에서 닫기**(115) |
| `service`       | **`IntegrityError` race → rollback + `DuplicateEmailError`**(75-78) · 초대 토큰 검증 후 DB 부재 → `WaitlistNotFoundError`(86-90) · `admin_list`(104-107)                  |

⇒ **지금 `verify()` 의 서명 대조 뒤 갈래들을 지워도, 그리고 `_send_once` 의 4xx 처리를 지워도 스위트는 초록이다.**

★**착수 전 CONTROL 실측 — 구조 (세 모듈을 직접 읽어 확인했다):**

| 축                            | 관측                                                                                                                                                                                                                                                                                                                                               |
| ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `InviteTokenService.__init__` | `not secret or len(secret) < 16` → `ValueError("WAITLIST_TOKEN_SECRET must be at least 16 characters")`                                                                                                                                                                                                                                            |
| `issue(email, *, now=None)`   | email 을 **`strip().lower()`** · `nonce = secrets.token_urlsafe(16)` · `exp = ts + ttl` · payload JSON 은 **`separators=(",",":")` + `sort_keys=True`** · 반환 = `"{b64(payload)}.{b64(sig)}"`                                                                                                                                                     |
| `verify(token, *, now=None)`  | `token.split(".", 1)` 실패 → `InviteTokenInvalidError` / b64 decode `(ValueError, TypeError)` → 같은 예외 / **`hmac.compare_digest` 불일치** → 같은 예외 / JSON decode 실패 → 같은 예외 / **`email`·`nonce` 가 `str` 이 아니거나 `exp` 가 `int` 가 아니면** → 같은 예외 / `current >= exp` → **`InviteTokenExpiredError`**(만료는 **다른 예외**다) |
| `EmailService.__init__`       | `not api_key` → `ValueError("Resend API key is empty")`. `client=None` 이면 **자기가 만들고 `finally` 에서 `aclose()`**                                                                                                                                                                                                                            |
| `_send_once`                  | `_is_retryable_status(...)` → `_RetryableError` / `status_code >= 400` → `EmailSendError` / 아니면 `response.json()`                                                                                                                                                                                                                               |
| `send_invite_email`           | `_RetryableError` → `EmailSendError(detail=str(exc))` · `httpx.TransportError` → `EmailSendError(detail=f"Transport error: {exc}")`                                                                                                                                                                                                                |
| `WaitlistService.__init__`    | `repo` · `email_service` · `token_service` · `config` **키워드 주입** — 전부 fake 로 바꿀 수 있다                                                                                                                                                                                                                                                  |
| `WaitlistService` 실패 갈래   | `repo.create/commit` 이 `IntegrityError` → **`repo.rollback()` 후 `DuplicateEmailError`** / `verify_invite_token` 은 `token_service.verify(token)` **먼저**, 그 다음 `repo.find_by_invite_token(token)` 이 `None` 이면 `WaitlistNotFoundError`                                                                                                     |

★**`EmailService` 는 `httpx.AsyncClient` 를 주입받을 수 있다** — 모듈 docstring 이
「테스트는 `httpx.MockTransport` 주입해 실 네트워크 호출 없이 검증」이라 적어 뒀다. **그 방식을 써라.**

## 작업

`apps/api/tests/waitlist/test_waitlist_service_failures.py` **하나**를 신설한다.
세 모듈을 한 파일에서 다룬다(초대 흐름 하나의 세 조각이다). **DB 0개 · 네트워크 0개.**
`WaitlistService` 는 fake repo/email/token 을 주입하고, `EmailService` 는 `MockTransport` 를 쓴다.

### 최소한 이 열을 덮어라 (케이스 ≥10)

1. ★★★**위조 토큰 거부 4종** — ⑴ `.` 이 없는 문자열 ⑵ base64 로 못 읽는 조각
   ⑶ 서명은 맞지만 payload 가 JSON 이 아닌 경우 ⑷ **JSON 은 맞지만 `exp` 가 문자열**(타입 검사).
   **넷 다 `InviteTokenInvalidError`** 다. ★⑶⑷ 는 **같은 secret 으로 직접 서명해서** 만들어라 —
   그래야 서명 검사를 통과한 뒤의 갈래에 도달한다
2. ★★★**다른 secret 으로 서명한 토큰이 거부된다** — `hmac.compare_digest` 축.
   ★**이것과 ⑴은 다른 줄이다** — 둘 다 넣어라
3. ★★**만료는 `InviteTokenExpiredError` 로 갈린다** — `now` 를 `exp` 이상으로 주면 **Invalid 가 아니라
   Expired** 다. ★**두 예외가 구별되는지**가 축이다(하나로 합치는 변이를 잡는다)
4. ★**`exp` 경계** — `now == exp` 는 만료(`current >= exp`), `now == exp - 1` 은 통과.
   ★**`now` 인자를 써라** — 벽시계에 의존하면 간헐 red 다
5. ★★**round-trip** — `issue` 한 토큰을 `verify` 하면 email 이 **`strip().lower()` 된 형태**로 돌아온다
6. ★★**짧은/빈 secret 으로 `InviteTokenService` 를 만들면 `ValueError`** — 15자와 빈 문자열 둘 다
7. ★★★**`_send_once` 의 4xx 영구 실패 → `EmailSendError`** — `MockTransport` 로 400 을 주고,
   **retryable 상태코드에서는 다른 경로(`_RetryableError`)로 가는지**도 재라.
   ★**어떤 상태코드가 retryable 인지는 `_is_retryable_status` 를 열어 확인해라**
8. ★★**retryable / transport 오류가 둘 다 `EmailSendError` 로 접힌다** — `detail` 문자열이
   서로 다른지 재라(`Transport error:` 접두). ★**원 예외가 `__cause__` 로 붙는지**도 재라
9. ★★**client 를 안 넘기면 `EmailService` 가 만들고 닫는다** — `client` 주입 시에는 **닫지 않는다**.
   ★**발송이 실패해도 닫는지**(`finally`) 재라 — 이것이 115줄이다
10. ★**빈 api_key → `ValueError("Resend API key is empty")`**
11. ★★★**`WaitlistService` 의 `IntegrityError` race** — fake repo 의 `create` 또는 `commit` 이
    `IntegrityError` 를 던지면 **`rollback()` 이 불리고 `DuplicateEmailError`** 가 나온다.
    ★**rollback 이 실제로 await 됐는지** 단언해라 — 그것이 이 갈래의 핵심이다
12. ★★**`verify_invite_token` 이 토큰은 유효한데 DB 에 없으면 `WaitlistNotFoundError`** —
    그리고 **토큰 검증이 DB 조회보다 먼저**인지 재라(유효하지 않은 토큰이면 repo 가 **0회** 불린다)

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/waitlist/test_waitlist_service_failures.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/waitlist/test_waitlist_service_failures.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 10
cd apps/api && uv run --env-file .env.local pytest tests/waitlist -q
cd apps/api && uv run ruff check tests/waitlist/test_waitlist_service_failures.py && uv run ruff format --check tests/waitlist/test_waitlist_service_failures.py
```

★2번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 **rc=4**(CONTROL 실측 2026-08-21).
★`--env-file .env.local` 을 빼지 마라 — DB 가드가 rc=3 으로 거부한다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. ★최종 판정은 러너가 재실행해 내린다 —
   `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 케이스 수와 **기존 `test_invite_token.py` 와 겹친 축**, ⑺의 retryable 상태코드 집합을 남겨라.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- ★**`src/waitlist/` 의 대상 3모듈을 수정하지 마라.** 이유: 이 회차의 계약은 「테스트만 추가하고 대상
  소스는 0줄 변경」이다. **토큰 검증에서 결함을 발견하면 고치지 말고 `status:"blocked"` +
  `blocked_reason`** 으로 멈춰라 — 보안 경계는 사람 diff 를 거쳐야 한다
- ★★**진짜 Resend API 를 부르지 마라(네트워크 0).** 이유: 실 메일이 나가고 비용이 든다.
  `httpx.MockTransport` 를 주입해라 — 모듈 docstring 이 그 방식을 지정하고 있다
- ★★**DB 픽스처(`db_session`·`client`)를 요청하지 마라.** 이유: `WaitlistService` 는 repo 를 **키워드로
  주입**받으므로 fake 로 충분하고, 픽스처를 요청하면 세션 엔진이 생성돼 8 lane 이 DB 를 함께 친다.
  ★**`src/waitlist/repository.py` 는 이 lane 의 대상이 아니다**
- ★**`src/waitlist/schemas.py` 를 겨누지 마라** — 이 lane 의 대상이 아니다(필요하면 **쓰기만** 해라)
- ★★**`xfail(strict=True)` 를 쓰지 마라. 이유:** 「제품 코드가 지금 틀렸다」를 원장에 박는 주장인데
  **AC·변이·사람 diff 세 층이 전부 통과시킨다**([LESSON-121]). 근거는 `summary` 에 적고 테스트는 지금 동작을 고정해라
- ★**재지 않은 값을 단언하지 마라.** 이유: step 의 산문은 세션에게 AC 와 구별되지 않는다([LESSON-122]).
  예외 클래스 이름 · `_is_retryable_status` 의 상태코드 집합 · `WaitlistService` 생성자 인자는
  **각 파일을 열어 확인**하고 써라
- ★**시각을 하드코딩하지 마라** — `issue`/`verify` 는 `now` 인자를 받는다. 벽시계에 의존하면 간헐 red 다
- ★**`tests/waitlist/` 의 기존 6파일을 수정하지 마라** — 이 lane 소유가 아니다
- ★**`conftest.py`(루트·`tests/waitlist/`) · `pyproject.toml` · `shards.json` 무변경**(8 lane 동시 실행 — 병합 충돌)
- **공용 헬퍼 모듈을 만들지 마라** — fake repo/transport 는 이 테스트 파일 안에 둬라
- **새 pytest 마커를 쓰지 마라** — `--strict-markers` 라 `pyproject.toml` 을 함께 고쳐야 하고 그것이 공유 파일이다
- `docs/**` · `phases/**` 무변경. 다른 lane 의 테스트 파일을 만들지 마라
- 커밋하지 마라(커밋은 러너 소관)
