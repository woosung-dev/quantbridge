# Backend Rules (FastAPI + SQLModel)

---

## 1. Tech Stack

| 항목            | 기술                                                       |
| --------------- | ---------------------------------------------------------- |
| Framework       | FastAPI (100% Async)                                       |
| ORM             | SQLModel + SQLAlchemy 2.0 (`asyncpg`)                      |
| Validation      | Pydantic V2 + `pydantic-settings`                          |
| Package Manager | `uv`                                                       |
| Database        | PostgreSQL + **TimescaleDB hypertable** (OHLCV 시계열)     |
| Cache / Broker  | Redis (Celery broker + 락 / 캐시)                          |
| Async Worker    | Celery (prefork pool, `_WORKER_LOOP` 통일 — §9)            |
| Auth            | Better Auth JWT 를 JWKS 로 검증 (`pyjwt[crypto]`, ADR-034) |
| Exchange SDK    | CCXT (Bybit / OKX / Binance 등 데모·라이브)                |
| LLM             | `anthropic` 우선 + `google-genai` fallback (§4 convert)    |
| 시크릿 암호화   | API 키는 AES-256 (Fernet) 암호화 저장                      |
| 배포            | Docker compose (개발) / TBD (프로덕션 H2+)                 |

> **참고**: LLM 호출부는 `strategy/convert/service.py` **한 곳**이고, 키는 `core/config.py` 의
> `anthropic_api_key` / `gemini_api_key` 다 (미설정 시 convert 엔드포인트 비활성). Object Storage /
> Vector DB 는 사용하지 않는다.
>
> ★**2026-08-22 정정** — 종전 문장은 「본 프로젝트는 백엔드에서 LLM SDK 를 사용하지 않는다. Pine Script
> 변환 등 AI 보조는 frontend → backend HTTP API 만 거쳐 진행한다」였고 **거짓이었다**. 같은 줄에서
> `Async Worker` 의 `§8` 포인터도 `§9`(Celery prefork-safe)로 고쳤다 — §8 은 폴더 구조다.

---

## 2. 핵심 제약 사항 (Strict Rules)

### Pydantic V2 필수 패턴

- `BaseSettings`는 반드시 `pydantic_settings`에서 임포트 (pydantic 내부 금지)
- `.dict()` 대신 `.model_dump()`, `.model_dump_json()`
- `@root_validator` 대신 `@model_validator(mode="after")`

### 100% 비동기 SQLModel

- `session.exec()` 절대 금지
- `await session.execute(select(...))` 후 `.scalars().all()` 또는 `.scalar_one_or_none()`
- N+1 방지: `options(selectinload(...))`

### SecretStr

- API 키, DB 패스워드 등 → `SecretStr` 타입 (★인증 시크릿은 이제 백엔드에 없다 — ADR-034)
- 사용 시 `.get_secret_value()`

### Decimal-first 금융 숫자

- 가격 / 수량 / 수익률 / 레버리지 등은 `Decimal` 사용 (float 금지).
- 합산 시 `Decimal(str(a)) + Decimal(str(b))` — float 공간 합산 후 변환 금지 (Sprint 4 D8 교훈).

### JWT 검증 — JWKS 공개 키 ([ADR-034](../../docs/adr/034-auth-self-host-better-auth.md))

★**백엔드는 인증 시크릿을 쥐지 않는다.** 검증기는 `src/realtime/auth.py` **한 곳**이고
HTTP·WebSocket 이 그것을 공유한다. 새 검증 경로를 만들지 마라.

```python
# realtime/auth.py — 요지
signing_key = PyJWKClient(settings.jwks_url, cache_keys=True).get_signing_key_from_jwt(token)
payload = jwt.decode(token, signing_key.key, algorithms=["EdDSA"],
                     issuer=issuer, audience=issuer,
                     options={"require": ["exp", "sub", "iss", "aud"]})
```

- 알고리즘은 **EdDSA 하나로 고정**한다 — 목록을 넓히면 알고리즘 혼동 표면이 열린다.
- `iss`/`aud` 는 `settings.better_auth_url` 이다. FE 의 `BETTER_AUTH_URL` 과 어긋나면 **전건 401**.
- 사용자 행은 첫 인증 요청에서 생긴다(JIT). 웹훅이 없다 — `users.auth_subject` = JWT `sub`.
- `python-jose` 는 **EdDSA 미지원**이라 쓸 수 없다(실측). `pyjwt[crypto]` 를 쓴다.

---

## 3. Architecture — 3-Layer (Router / Service / Repository)

**핵심: `AsyncSession` 은 Repository 만 보유한다.**

```
[domain]/
├── router.py        # HTTP 전용 (10줄 이하)
├── service.py       # 비즈니스 로직 (AsyncSession 보유 금지)
├── repository.py    # DB 접근 전담 (AsyncSession 유일 보유자)
├── schemas.py       # Pydantic V2 입출력
├── models.py        # SQLModel 테이블
├── dependencies.py  # Depends() 조립 (repo → service)
└── exceptions.py    # 도메인 예외
```

- **Router** — HTTP 수신·스키마 검증·service 호출만. **이유:** DB/로직이 들어오면 테스트가 HTTP 를 통과해야만 돌아간다
- **Service** — 비즈니스 로직 + 트랜잭션 경계. `AsyncSession` **import 금지**. Repository 만 생성자 주입.
  **이유:** 세션을 쥐면 DB 없이 단위 테스트가 불가능해진다
- **Repository** — `AsyncSession` 유일 보유. DB 접근만. `commit()` 은 **service 요청으로만**
- **Dependencies** — `Depends()` 조립의 유일한 위치. service/repository 에 `Depends` import 금지

★**commit 보장 의무** ([LESSON-019] — 같은 결함이 3회 재발) — service mutation 메서드마다
`tests/<domain>/test_*_commits.py` 에 **AsyncMock spy 회귀 1건 필수**(`repo.commit.assert_awaited_once()`).
**이유:** `get_async_session()` 은 autocommit OFF 라 명시 commit 이 없으면 요청 종료 시 ROLLBACK 인데,
`db_session` 픽스처 통합 테스트는 conftest 트랜잭션 안에서 read-your-writes 로 **통과해 버린다**(false-positive).

★**여러 repo 를 묶는 service** 는 `dependencies.py` 에서 **동일 session** 으로 조립하고 **한 번만 commit** 한다.

### ★ 이 표준을 따르지 않는 디렉터리 (예외 — 위반이 아니다)

`src/` 하위 전부가 도메인 모듈은 아니다. 아래는 **의도된 예외**이고, 여기에 없는 디렉터리를
7파일 표준에서 벗어나게 만들려면 먼저 이 표에 줄을 추가해라.

| 디렉터리            | 무엇인가                                                  | 왜 3-Layer 가 아닌가                                                                                                                                                                                        |
| ------------------- | --------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `market_data/`      | OHLCV provider(CCXT·Timescale·fixture) 공급               | **공개 REST 가 없는 내부 전용 subdomain**(`CONTEXT.md` Data Context). `main.py` 에 마운트되지 않고 `backtest`·`optimizer`·`stress_test`·`tasks`·`trading` 이 라이브러리로 쓴다. router/service/schemas 없음 |
| `realtime/`         | WS 라우터 + **JWT/JWKS 검증기**(`auth.py`) + 연결 manager | 검증기는 도메인이 아니라 횡단 관심사다. 원장은 `auth/` 가 갖는다                                                                                                                                            |
| `health/`           | `/healthz`·`/livez`                                       | 상태 프로브. 소유 엔티티가 없다                                                                                                                                                                             |
| `tasks/`            | Celery task entrypoint                                    | HTTP 표면이 아니다. prefork-safe 규칙은 §9                                                                                                                                                                  |
| `scripts/`          | 운영 entrypoint helper (`run_alembic_with_lock`)          | `python -m src.scripts.*` 로 실행. 테스트·dogfood 스크립트는 여기가 아니라 `apps/api/scripts/`(앱 루트)                                                                                                     |
| `common/` · `core/` | 기술 기반 · 설정                                          | 도메인이 아니다                                                                                                                                                                                             |

`trading/` 은 예외가 아니라 **확장**이다 — `service.py`/`repository.py` 가 파일이 아니라
`services/`·`repositories/` 디렉터리로 분해돼 있고, 그 밖에 `websocket/` 서브패키지를 갖는다.

★**PR 리뷰 의무** — `git diff -- '*service.py'` 에 `repo.save|repo.update|repo.delete` 가
추가·수정되면 **같은 PR 에 commit-spy 테스트가 있는지** 본다. atomic 옵션(`commit=False`)은
`assert_not_called()` 로 명시 검증한다.

★**코드 예제는 문서가 아니라 실물을 봐라** — `apps/api/src/<도메인>/dependencies.py` **8개** ·
commit-spy 표준 = `apps/api/tests/*/test_*commits*.py` **9개**. **이유:** 문서 안의 예제는 낡지만
실물은 CI 가 지킨다. 새 도메인은 가장 가까운 기존 도메인을 복사해서 시작해라.

## 4. QuantBridge 도메인 고유 규칙

| 영역             | 규칙                                                                                                                                                                  |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Pine Script 변환 | `exec()` / `eval()` 절대 금지 — 인터프리터 패턴 (`pine_v2`) 또는 sandbox 사용 (ADR-003).                                                                              |
| Pine 미지원 함수 | 1개라도 포함 시 전체 "Unsupported" 반환 — 부분 실행 금지 (잘못된 결과 방지).                                                                                          |
| 백테스트/최적화  | 반드시 Celery 비동기. API 핸들러 직접 실행 금지. 결과는 `result_jsonb` 컬럼.                                                                                          |
| 거래소 API Key   | AES-256 (`Fernet`) 암호화 후 DB 저장. 평문 컬럼 금지.                                                                                                                 |
| OHLCV 시계열     | TimescaleDB hypertable (`ts.ohlcv`) 에 저장. 일반 PostgreSQL 테이블 사용 금지.                                                                                        |
| 실시간 가격      | WebSocket + Zustand 캐시 (frontend). 백엔드는 `ws_stream` 별도 queue + prefork worker (Sprint 24 BL-012 prefork 복귀 — `docker-compose.yml` ws-stream 서비스가 정본). |
| 관측 metric      | 업무 **결과를 보고하는** `try` 본문·`except` 본문에서 metric mutation 을 raw 로 두지 마라 — `record_metric_safely` / `_count_safely` / `_touch_safely` 로 감싼다. 이유: metric 실패 예외가 그 handler 로 흘러 **체결을 취소 실패로 오기록**하거나 계정 스윕을 중단시킨다(2026-08-24 실측 4건).       |

---

## 5. 스트리밍 응답

레포는 SSE 를 **쓰지 않는다** — 2026-08-22 실측으로 `apps/api/src` 에 `StreamingResponse` **0건** ·
`text/event-stream` **0건**이다. 진척률은 §6 의 폴링 또는 WebSocket(`realtime/`)이 낸다.
예제는 지웠고 절 번호는 외부 참조(`docs/lessons.md`·`status.md`) 때문에 당기지 않는다.

---

## 6. 비동기 장기 작업 패턴

수초 이상 걸리는 작업(백테스트, 최적화, 스트레스 테스트)은 HTTP 응답을 블로킹하지 않는다.

task entry 의 코드 정본은 **§9.1**(`run_in_worker_loop` 의무)이고 실물 reference 는
`apps/api/src/tasks/backtest.py` 다. 상태 조회는 평범한 GET 라우터라 §3 패턴 그대로다.

**원칙:**

- 장기 작업은 `202 Accepted` + task id 반환
- 클라이언트는 polling 또는 WebSocket으로 상태 확인
- DB에 `status` 컬럼으로 진행 상태 관리 (`pending | running | completed | failed | cancelled`)
- 실시간 진척률은 Redis pub/sub + WebSocket 으로 전송 (필요 시)

---

## 7. DB 마이그레이션 (Alembic)

```bash
# 마이그레이션 생성
alembic revision --autogenerate -m "add backtest_kind column"

# 마이그레이션 적용
alembic upgrade head

# 롤백 — ★`-x allow_destructive=1` 이 **필수**다. 그냥 치면 SystemExit 로 죽는다.
#   `alembic/env.py:106-125` 가 downgrade 만 골라 막는다(`_test` 접미 DB 만 자동 통과).
#   2026-07-25 에 이 경로로 로컬 개발 DB 가 전소한 뒤 세운 가드다. 먼저 `mise run db-snapshot`.
alembic -x allow_destructive=1 downgrade -1
```

> ★**서버 소크 DB 는 별개다** — DDL 은 매번 명시 승인이고 집행 도구는 `soak-stack.sh migrate` 다.
> 절차 정본 = [`backend-deploy.md`](../../docs/operations/backend-deploy.md).

### 규칙

- `models.py` 변경 시 **반드시** Alembic 마이그레이션 생성
- 마이그레이션 파일은 커밋에 포함 (자동 생성 후 검토)
- 로컬은 Docker entrypoint 의 `api` 롤이 `alembic upgrade head` 를 자동 실행한다.
  ★CI 는 [ADR-037] 이후 alembic 을 어디서도 돌지 않는다(pytest 스키마 = 세션 픽스처의
  drop_all+create_all). `alembic check` 게이트 복귀는 재입힘 규칙 경유.
  ★**프로덕션(서버 소크 스택)은 아니다** — compose 6서비스에 **api 롤이 없고**
  (celery 계열은 `command:` override 로 롤 분기를 우회한다) 실제 API 는 호스트 uvicorn
  systemd 유닛이라 entrypoint 를 지나지 않는다. **DDL 은 `soak-stack.sh migrate --confirm`
  으로 사람이 승인해 적용한다** — 이것을 빼먹으면 새 코드가 옛 스키마 위에서 돈다
  ([BL-743] · 2026-08-18 codex 적대 리뷰가 이 줄의 거짓을 잡았다).
- 데이터 삭제/컬럼 삭제는 **2단계 배포**: (1) 코드에서 사용 중단 → (2) 다음 배포에서 삭제
- **enum value 추가/제거**: downgrade 안 enum swap 패턴 의무 (LESSON-066) — 처음부터 uppercase 채택, 이후 enum value 추가 시 alembic 안 양방향 안전 검증

---

## 8. 백엔드 폴더 구조

```
apps/api/src/
├── main.py         # create_app() — 라우터 조립 · 미들웨어 · 예외 핸들러 · lifespan
│                   #   ★조립 전용 디렉터리(api/)는 없다. /api/v1 프리픽스는 여기서 붙인다
├── [domain]/       # 3-Layer 도메인 (router/service/repository/schemas/models/dependencies/exceptions)
│   #   backtest · stress_test · optimizer · strategy · trading · waitlist · auth
│   #   (exchange 는 trading 으로 통합 — ADR-018)
├── auth/           # 사용자 원장 + 탈퇴. ★JWT 검증기는 realtime/auth.py
├── strategy/
│   ├── convert/    # 지표 변환 서브도메인 (자체 router — prefix 는 /strategies 공유)
│   └── pine_v2/    # Pine Script v2 인터프리터 (SSOT — interpreter / stdlib / coverage)
├── trading/
│   ├── services/   # ★단일 파일이 아니라 디렉터리로 분해됨
│   ├── repositories/
│   └── websocket/  # Bybit private/public 스트림 + 재조정
├── market_data/    # 내부 전용 subdomain — 공개 REST 없음 (§3 예외 표)
├── realtime/       # WS 라우터 + JWT/JWKS 검증기 + 연결 manager
├── health/         # /healthz · /livez
├── tasks/          # Celery task entrypoints (prefork-safe pattern — §9)
├── scripts/        # 운영 entrypoint helper (python -m src.scripts.*)
├── common/         # 기술 기반 — database · exceptions · redis_client · redlock
│                   #   metrics · rate_limit · logging_config · alert(Slack) · telegram_alert
└── core/
    └── config.py   # 전 도메인 Settings (pydantic-settings)
```

> `src` 는 **설치되는 패키지가 아니다** — `pyproject.toml` 에 `[build-system]` 이 없고
> `[tool.uv] package = false` 다. import 가능성은 CWD 가 `apps/api`(컨테이너 `/app`)라는 사실에
> 의존하고, 그 사실은 `pyproject.toml` `pythonpath=["."]` · `alembic.ini` `prepend_sys_path=.` ·
> `Dockerfile` `WORKDIR` 셋이 함께 세운다. **디렉터리 이름 `src` 를 바꾸면 이 셋과
> `docker-entrypoint.sh`·compose 의 `uvicorn src.main:app`·`celery -A src.tasks` 가 함께 깨진다.**

---

## 9. Celery prefork-safe 패턴

**모든 task entry 는 `asyncio.run(coro)` 대신 `run_in_worker_loop(coro)` 를 쓴다.**
**이유:** `asyncio.run()` per task + module-level async state 조합은 2번째 task 부터
`RuntimeError("Future attached to a different loop")` 로 **조용히 실패**한다(asyncpg 콜백이 1번째 loop 에 stale bound).

```python
@shared_task(name="domain.task_name")
def task_entry(payload: str) -> dict:
    from src.tasks._worker_loop import run_in_worker_loop
    return run_in_worker_loop(_async_impl(payload))
```

- **engine 수명은 task 단위** — `create_worker_engine_and_sm()` 후 `finally: await engine.dispose()`.
  **이유:** loop 통일과 별개로 connection pool stale 누수가 남는다. 표준 = `src/tasks/backtest.py`
- **nested `run_in_worker_loop` 금지** — 이미 도는 loop 안에서 호출하면 `RuntimeError`(침묵 fallback 없음)
- **module-level `asyncio.Semaphore/Lock/Event/Queue` 추가 시 PR 리뷰 의무** —
  게이트 = `tests/tasks/test_no_module_level_loop_bound_state.py`. allowlist 는 현재 1건
- **fire-and-forget alert 는 `track_pending_alert(task)`** — `_PENDING_ALERTS` 직접 조작 금지(gauge 동기화 누락)

★배선 상세·allowlist 갱신 절차·signal 훅 전문 = [`docs/development/celery-prefork.md`](../../docs/development/celery-prefork.md).

## 10. 검사기가 무엇을 보는지 증명해라 ([LESSON-092])

**초록은 「통과했다」가 아니라 「내가 본 것 중에는 없었다」만 말한다.**

**변이 판별 절차 3층** — 가운데를 빼면 무증거다:
1. **앵커가 1건인가** (0건이면 못 심었고, 2건 이상이면 어디가 바뀌었는지 모른다)
2. **치환이 파일에 들어갔는가** (sha256 스냅샷으로 심고 되돌려라 — `git checkout` 금지)
3. ★**그 줄을 실행하는 입력이 테스트 집합에 있는가** — 분기 조건에 기본값이 아닌 설정
   (`fill_timing`·feature flag·env)이 걸려 있으면 그것을 **명시로 켜는 케이스**를 최소 1건 둬라

★**판정 명령에 파이프를 붙이지 마라** — `uv run pytest ... | tail -3` 은 pytest 가 아니라 **tail 의 rc** 를 읽는다.
rc 를 먼저 잡고 텍스트는 나중에 잘라라. (이 레포에서 10회 이상 재발했다.)

★**주석에 적는 근거 문장도 실측 대상이다** — 「기본값이 X 라서 이 분기를 지난다」는 코드로 확인한 뒤 써라.

★전문(행위 동결·페이크 제약축·가드 배치 §10.1) = [`docs/lessons.md`](../../docs/lessons.md) 의 LESSON-092 절.

