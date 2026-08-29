# Backend Rules (FastAPI + SQLModel)

## 1. Tech Stack

스택 정본은 **루트 `AGENTS.md` §2** 다. 여기 적는 것은 거기에 없는 BE 고유 사항뿐이다.
- **배포** — Docker compose(개발) / 서버 소크 스택(§7). Object Storage · Vector DB 는 쓰지 않는다.
- **LLM 키** — `core/config.py` 의 `anthropic_api_key` / `openai_api_key` / `gemini_api_key`.
  ★어느 것을 쓸지는 **`LLM_PROVIDER_ORDER`** 가 정한다(쉼표 목록, 앞에서부터 시도, 키 없으면 건너뜀).
  전부 미설정이면 LLM 엔드포인트만 503 이고 결정론 브리핑·백테스트는 그대로 돈다
- **시크릿 암호화** — 거래소 API 키는 AES-256(`Fernet`) 저장(§4)

## 2. 핵심 제약 사항 (Strict Rules)

**Pydantic V2** — `BaseSettings` 는 반드시 `pydantic_settings` 에서 임포트(pydantic 내부 금지) ·
`.dict()` 대신 `.model_dump()`/`.model_dump_json()` · `@root_validator` 대신 `@model_validator(mode="after")`

**100% 비동기 SQLModel** — `session.exec()` 절대 금지 · `await session.execute(select(...))` 후
`.scalars().all()` 또는 `.scalar_one_or_none()` · N+1 방지는 `options(selectinload(...))`

**SecretStr** — API 키·DB 패스워드 등은 `SecretStr` 타입, 사용 시 `.get_secret_value()`
(★인증 시크릿은 이제 백엔드에 없다 — ADR-034)

**Decimal-first 금융 숫자** — 가격·수량·수익률·레버리지는 `Decimal`(float 금지). 합산은
`Decimal(str(a)) + Decimal(str(b))` — float 공간에서 합산한 뒤 변환하지 마라 (Sprint 4 D8 교훈)

### JWT 검증 — JWKS 공개 키 ([ADR-034](../../docs/adr/034-auth-self-host-better-auth.md))

★**백엔드는 인증 시크릿을 쥐지 않는다.** 검증기는 `src/realtime/auth.py` **한 곳**이고
HTTP·WebSocket 이 그것을 공유한다. **새 검증 경로를 만들지 마라** — 코드는 그 파일을 봐라.

- 알고리즘은 **EdDSA 하나로 고정**한다 — 목록을 넓히면 알고리즘 혼동 표면이 열린다.
- `iss`/`aud` 는 `settings.better_auth_url` 이다. FE 의 `BETTER_AUTH_URL` 과 어긋나면 **전건 401**.
- 사용자 행은 첫 인증 요청에서 생긴다(JIT). 웹훅이 없다 — `users.auth_subject` = JWT `sub`.
- `python-jose` 는 **EdDSA 미지원**이라 쓸 수 없다(실측). `pyjwt[crypto]` 를 쓴다.

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
`db_session` 픽스처 통합 테스트는 트랜잭션 안 read-your-writes 로 **통과해 버린다**(false-positive).
★**PR 리뷰 의무** — `git diff -- '*service.py'` 에 `repo.save|repo.update|repo.delete` 가
추가·수정되면 **같은 PR 에 commit-spy 테스트가 있는지** 본다. atomic 옵션(`commit=False`)은
`assert_not_called()` 로 명시 검증한다.

★**여러 repo 를 묶는 service** 는 `dependencies.py` 에서 **동일 session** 으로 조립하고 **한 번만 commit** 한다.

★**「AsyncSession 금지」의 등재된 예외는 하나뿐이다** — `trading/services/order_service.py` 가
`begin_nested()` SAVEPOINT 와 outer `commit()` 을 위해 세션을 생성자로 받는다(`:64`). 그 두 용도 밖으로
세션을 쓰지 마라. 회귀 = `tests/trading/test_order_service_dispatch_snapshot.py` 가 `session.commit` 을 spy 한다.
**새 예외를 만들려면 코드가 아니라 이 줄을 먼저 늘려라.** 게이트 = `tests/common/test_repository_boundary_guard.py`
(경계 밖 `select(` · `repo.session` 리치스루 · 경계 밖 raw SQL 실행 **3축**).

★**코드 예제는 문서가 아니라 실물을 봐라** — 조립 표준 = `src/<도메인>/dependencies.py`, commit-spy
표준 = `tests/*/test_*commits*.py`. **이유:** 문서 안의 예제는 낡지만 실물은 CI 가 지킨다.

### ★ 이 표준을 따르지 않는 디렉터리 (예외 — 위반이 아니다)

`src/` 하위 전부가 도메인 모듈은 아니다. 아래는 **의도된 예외**이고, 여기 없는 디렉터리를 7파일
표준에서 벗어나게 만들려면 먼저 이 표에 줄을 추가해라.

| 디렉터리 | 무엇인가 | 왜 3-Layer 가 아닌가 |
| --- | --- | --- |
| `market_data/` | OHLCV provider(CCXT·Timescale·fixture) 공급 | **공개 REST 가 없는 내부 전용 subdomain**(`CONTEXT.md` Data Context). `main.py` 에 마운트되지 않고 `backtest`·`optimizer`·`stress_test`·`tasks`·`trading` 이 라이브러리로 쓴다. router/service/schemas 없음 |
| `realtime/` | WS 라우터 + **JWT/JWKS 검증기**(`auth.py`) + 연결 manager | 검증기는 도메인이 아니라 횡단 관심사다. 원장은 `auth/` 가 갖는다 |
| `health/` | `/healthz`·`/livez` | 상태 프로브. 소유 엔티티가 없다 |
| `tasks/` | Celery task entrypoint | HTTP 표면이 아니다. prefork-safe 규칙은 §9 |
| `scripts/` | 운영 entrypoint helper (`run_alembic_with_lock`) | `python -m src.scripts.*` 로 실행. 테스트·dogfood 스크립트는 여기가 아니라 `apps/api/scripts/`(앱 루트) |
| `strategy/narrative/` | [ADR-040] 해설 층 LLM 클라이언트 | **DB 세션을 안 쥔다** — `convert/` 와 같은 형태(repository·models 없음). 결정론 브리핑은 `StrategyService` 가 갖고 여기는 LLM 왕복만 한다 |
| `common/` · `core/` | 기술 기반 · 설정 | 도메인이 아니다 |

`trading/` 은 예외가 아니라 **확장**이다 — `service.py`/`repository.py` 가 `services/`·`repositories/`
디렉터리로 분해돼 있고, 그 밖에 `websocket/` 서브패키지를 갖는다.

## 4. QuantBridge 도메인 고유 규칙

| 영역 | 규칙 |
| --- | --- |
| Pine Script 변환 | `exec()` / `eval()` 절대 금지 — 인터프리터 패턴(`pine_v2`) 또는 sandbox (ADR-003) |
| Pine 미지원 함수 | 1개라도 포함 시 전체 "Unsupported" 반환 — 부분 실행 금지 (잘못된 결과 방지) |
| 백테스트/최적화 | 반드시 Celery 비동기. API 핸들러 직접 실행 금지. 결과는 `result_jsonb` 컬럼 |
| 거래소 API Key | AES-256(`Fernet`) 암호화 후 DB 저장. 평문 컬럼 금지 |
| OHLCV 시계열 | TimescaleDB hypertable(`ts.ohlcv`) 에 저장. 일반 PostgreSQL 테이블 사용 금지 |
| 실시간 가격 | 백엔드는 `ws_stream` 별도 queue + prefork worker (`docker-compose.yml` ws-stream 서비스가 정본) |
| LLM 산출물 | **판정에 쓰지 마라** — 실행 가능·미지원·degraded 판정은 결정론 층(AST·coverage)이 독점한다([ADR-040]). LLM 문장은 근거 줄(`pine_lines`)이 없으면 **서버가 버린다** |
| 관측 metric | 업무 **결과를 보고하는** `try` 본문·`except` 본문에서 metric mutation 을 raw 로 두지 마라 — `record_metric_safely` / `_count_safely` / `_touch_safely` 로 감싼다. **이유:** metric 실패 예외가 그 handler 로 흘러 **체결을 취소 실패로 오기록**하거나 계정 스윕을 중단시킨다(2026-08-24 실측 4건) |

## 5. 스트리밍 응답

레포는 SSE 를 **쓰지 않는다**(`apps/api/src` 에 `StreamingResponse`·`text/event-stream` **0건**). 진척률은 §6 의 폴링 또는 WebSocket(`realtime/`)이 낸다.

## 6. 비동기 장기 작업 패턴

수초 이상 걸리는 작업(백테스트·최적화·스트레스 테스트)은 HTTP 응답을 블로킹하지 않는다. task entry
의 코드 정본은 **§9**(`run_in_worker_loop` 의무), 실물은 `src/tasks/backtest.py` 다. 상태 조회는
평범한 GET 라우터라 §3 패턴 그대로다.

- 장기 작업은 `202 Accepted` + task id 를 반환하고, 클라이언트는 polling 또는 WebSocket 으로 상태를 본다
- 진행 상태는 DB `status` 컬럼(`pending | running | completed | failed | cancelled`).
  실시간 진척률은 Redis pub/sub + WebSocket (필요 시)

## 7. DB 마이그레이션 (Alembic)

- `models.py` 를 바꾸면 **반드시** 마이그레이션을 생성해 검토 후 커밋에 포함한다
  (`alembic revision --autogenerate` → `alembic upgrade head`)
- ★**downgrade 는 `-x allow_destructive=1` 이 필수다** — 그냥 치면 `SystemExit` 로 죽는다
  (`alembic/env.py` 가 downgrade 만 골라 막는다. `_test` 접미 DB 만 자동 통과).
  **이유:** 2026-07-25 에 이 경로로 로컬 개발 DB 가 전소했다. 먼저 `mise run db-snapshot`
- 데이터/컬럼 삭제는 **2단계 배포**: ⑴ 코드에서 사용 중단 → ⑵ 다음 배포에서 삭제
- **enum value 추가/제거**는 downgrade 안 enum swap 패턴 의무 ([LESSON-066]) — 처음부터 uppercase

**어디서 도는가** — 세 환경이 전부 다르다:

- **로컬** — Docker entrypoint 의 `api` 롤이 `alembic upgrade head` 를 자동 실행
- **CI** — [ADR-037] 이후 alembic 을 **어디서도 돌지 않는다**(pytest 스키마 = 세션 픽스처의
  `drop_all`+`create_all`). `alembic check` 게이트 복귀는 재입힘 규칙 경유
- **서버 소크 스택** — compose 에 **api 롤이 없고** 실제 API 는 호스트 uvicorn systemd 유닛이라
  entrypoint 를 지나지 않는다. **DDL 은 `soak-stack.sh migrate --confirm` 으로 사람이 승인해
  적용한다** — 빼먹으면 새 코드가 옛 스키마 위에서 돈다([BL-743]).
  절차 정본 = [`backend-deploy.md`](../../docs/operations/backend-deploy.md)

## 8. 백엔드 폴더 구조

```
apps/api/src/
├── main.py         # create_app() — 라우터 조립 · 미들웨어 · 예외 핸들러 · lifespan
│                   #   ★조립 전용 디렉터리(api/)는 없다. /api/v1 프리픽스는 여기서 붙인다
├── [domain]/       # 3-Layer 7파일 도메인 — backtest · stress_test · optimizer · strategy
│                   #   · trading · waitlist · auth (exchange 는 trading 으로 통합 — ADR-018)
│                   # ★7파일은 **필수 코어**이지 상한이 아니다. 실제로 7개 도메인 전부가 부속
│                   #   모듈을 더 갖는다 — 통용되는 확장 형태는 `engine/`(backtest·optimizer·
│                   #   stress_test) · `providers/`(market_data) · `dispatcher.py`/`serializers.py`
├── auth/           # 사용자 원장 + 탈퇴. ★JWT 검증기는 realtime/auth.py
├── strategy/
│   ├── convert/    # 지표 변환 서브도메인 (자체 router — prefix 는 /strategies 공유)
│   ├── narrative/  # [ADR-040] 해설 층 LLM 클라이언트 (§3 예외 표)
│   ├── pine/       # ★v1 잔해가 아니라 **공유 타입 모듈**이다 — `ParseOutcome`·`PineError`·
│   │               #   `SignalResult` 를 `backtest/engine/{types,v2_adapter}.py` 가 import 한다.
│   │               #   이름만 v1 을 가리킨다. 신규 코드는 여기에 넣지 마라
│   └── pine_v2/    # Pine Script v2 인터프리터 (SSOT — interpreter / stdlib / coverage / runtime/)
├── trading/
│   ├── services/   # ★단일 파일이 아니라 디렉터리로 분해됨
│   ├── repositories/
│   └── websocket/  # Bybit private/public 스트림 + 재조정
├── market_data/    # 내부 전용 subdomain — 공개 REST 없음 (§3 예외 표)
├── realtime/       # WS 라우터 + JWT/JWKS 검증기 + 연결 manager
├── health/         # /healthz · /livez
├── tasks/          # Celery task entrypoints (prefork-safe pattern — §9)
├── scripts/        # 운영 entrypoint helper (python -m src.scripts.*)
├── common/         # 기술 기반 — database · exceptions · redis_client · redlock · metrics
│                   #   · rate_limit · logging_config · alert(Slack) · telegram_alert
└── core/
    └── config.py   # 전 도메인 Settings (pydantic-settings)
```

> `src` 는 **설치되는 패키지가 아니다** — import 가능성은 CWD 가 `apps/api`(컨테이너 `/app`)라는
> 사실에 의존하고, 그 사실은 `pyproject.toml` `pythonpath=["."]` · `alembic.ini`
> `prepend_sys_path=.` · `Dockerfile` `WORKDIR` 셋이 함께 세운다. **디렉터리 이름 `src` 를 바꾸면
> 이 셋과 `docker-entrypoint.sh`·compose 의 `uvicorn src.main:app`·`celery -A src.tasks` 가 함께 깨진다.**

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

★배선 상세·allowlist 갱신 절차·signal 훅 전문 = [`celery-prefork.md`](../../docs/development/celery-prefork.md).

## 10. 검사기가 무엇을 보는지 증명해라 ([LESSON-092])

**초록은 「통과했다」가 아니라 「내가 본 것 중에는 없었다」만 말한다.**

**변이 판별 절차 3층** — 가운데를 빼면 무증거다:
1. **앵커가 1건인가** (0건이면 못 심었고, 2건 이상이면 어디가 바뀌었는지 모른다)
2. **치환이 파일에 들어갔는가** (sha256 스냅샷으로 심고 되돌려라 — `git checkout` 금지)
3. ★**그 줄을 실행하는 입력이 테스트 집합에 있는가** — 분기 조건에 기본값이 아닌 설정
   (feature flag·env)이 걸려 있으면 그것을 **명시로 켜는 케이스**를 최소 1건 둬라

★**판정 명령에 파이프를 붙이지 마라** — `uv run pytest ... | tail -3` 은 pytest 가 아니라 **tail 의 rc** 를 읽는다.
rc 를 먼저 잡고 텍스트는 나중에 잘라라. (이 레포에서 10회 이상 재발했다.)

★**주석에 적는 근거 문장도 실측 대상이다** — 「기본값이 X 라서 이 분기를 지난다」는 코드로 확인한 뒤 써라.

★전문(행위 동결·페이크 제약축·가드 배치 §10.1) = [`docs/lessons.md`](../../docs/lessons.md) 의 LESSON-092 절.
