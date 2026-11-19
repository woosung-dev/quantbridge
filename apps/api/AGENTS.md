# Backend Rules (FastAPI + SQLModel)

> 코드가 말하지 못하는 것만 적는다([ADR-047](../../docs/adr/047-agent-rules-as-enforcer-table.md)). 예제는 실물을 본다 —
> 조립 표준 = `src/<도메인>/dependencies.py`, task 표준 = `src/tasks/backtest.py`, commit-spy 표준 = `tests/*/test_*commits*.py`.
> 어느 규칙을 무엇이 집행하는지는 맨 아래 표에 있다. 절 번호는 옮기지 않는다 — 코드 주석과 테스트 오류 문구가 인용한다.

## 1. Tech Stack

스택 정본은 `pyproject.toml` 과 루트 `AGENTS.md` §2 다. BE 고유 사항:

- 서버 배포는 GHCR 이미지 + `tools/scripts/deploy.sh` 다(§7). Object Storage 와 Vector DB 는 쓰지 않는다.
- LLM 키는 `core/config.py` 가 갖고, 어느 provider 를 쓸지는 `LLM_PROVIDER_ORDER` 가 정한다. 전부 미설정이면
  LLM 엔드포인트만 503 이고 결정론 브리핑·백테스트는 그대로 돈다.

## 2. 핵심 제약 사항 (Strict Rules)

**Pydantic V2** — `BaseSettings` 는 `pydantic_settings` 에서 import 한다. `.dict()` 대신 `.model_dump()`,
`@root_validator` 대신 `@model_validator(mode="after")` 를 쓴다.

**100% 비동기 SQLModel** — `session.exec()` 을 쓰지 않는다. `await session.execute(select(...))` 뒤
`.scalars().all()` 또는 `.scalar_one_or_none()` 을 쓴다. N+1 은 `options(selectinload(...))` 로 막는다.

**SecretStr** — API 키·DB 패스워드는 `SecretStr` 로 받고 쓸 때 `.get_secret_value()` 를 부른다.

**Decimal-first 금융 숫자** — 가격·수량·수익률·레버리지는 `Decimal` 이다(float 금지). 합산은
`Decimal(str(a)) + Decimal(str(b))` 로 한다. float 공간에서 합산한 뒤 변환하면 오차가 이미 들어가 있다.

### JWT 검증 — JWKS 공개 키 ([ADR-034](../../docs/adr/034-auth-self-host-better-auth.md))

백엔드는 인증 시크릿을 쥐지 않는다. 검증기는 `src/realtime/auth.py` 한 곳이고 HTTP 와 WebSocket 이 공유한다.
새 검증 경로를 만들지 않는다.

- 알고리즘은 EdDSA 하나로 고정한다. 목록을 넓히면 알고리즘 혼동 표면이 열린다.
- `iss`/`aud` 는 `settings.better_auth_url` 이다. FE 의 `BETTER_AUTH_URL` 과 어긋나면 전건 401 이다.
- 사용자 행은 첫 인증 요청에서 생긴다(JIT). 웹훅이 없다 — `users.auth_subject` = JWT `sub`.
- `python-jose` 는 EdDSA 를 지원하지 않아 쓸 수 없다. `pyjwt[crypto]` 를 쓴다.

## 3. Architecture — 3-Layer (Router / Service / Repository)

**`AsyncSession` 은 Repository 만 보유한다.**

```
[domain]/
├── router.py        # HTTP 전용
├── service.py       # 비즈니스 로직 (AsyncSession 보유 금지)
├── repository.py    # DB 접근 전담 (AsyncSession 유일 보유자)
├── schemas.py       # Pydantic V2 입출력
├── models.py        # SQLModel 테이블
├── dependencies.py  # Depends() 조립 (repo → service)
└── exceptions.py    # 도메인 예외
```

- **Router** — HTTP 수신·스키마 검증·service 호출만 한다. DB 나 로직이 들어오면 테스트가 HTTP 를 지나야만 돈다.
- **Service** — 비즈니스 로직과 트랜잭션 경계를 갖는다. `AsyncSession` 을 import 하지 않고 Repository 만 생성자로 받는다.
  세션을 쥐면 DB 없이 단위 테스트를 못 한다.
- **Repository** — `AsyncSession` 을 유일하게 보유하고 DB 접근만 한다. `commit()` 은 service 가 요청할 때만 한다.
- **Dependencies** — `Depends()` 조립의 유일한 자리다. service 와 repository 는 `Depends` 를 import 하지 않는다.

**commit 보장** — service 의 mutation 메서드마다 `tests/<domain>/test_*_commits.py` 에 AsyncMock spy 회귀를 1건 둔다
(`repo.commit.assert_awaited_once()`). `get_async_session()` 은 autocommit 이 꺼져 있어 명시 commit 이 없으면 요청 종료 시
ROLLBACK 되는데, `db_session` 픽스처 통합 테스트는 트랜잭션 안 read-your-writes 로 통과해 버린다. service 에
`repo.save|update|delete` 를 더한 PR 은 같은 PR 에 commit-spy 를 넣는다. `commit=False` 경로는 `assert_not_called()` 로 검증한다.

- 여러 repo 를 묶는 service 는 `dependencies.py` 에서 같은 session 으로 조립하고 한 번만 commit 한다.
- 조립 지점은 `dependencies.py` 외에 하나 더 있다. `trading/code_risk_composition.py` 의 `build_code_risk_executor` 가
  HTTP·Celery·WS 워커가 같은 실행기를 쓰도록 한 곳에서 조립한다. service 가 세션을 쥐는 것이 아니라 조립 함수만 쥔다.
- 「AsyncSession 금지」의 등재된 예외는 `trading/services/order_service.py` 하나다. `begin_nested()` SAVEPOINT 와 outer
  `commit()` 두 용도로만 세션을 받는다. 새 예외가 필요하면 코드보다 이 줄을 먼저 늘린다.
- `tasks/` 가 세션을 쥐는 것(트랜잭션 경계)은 허용된다. 금지되는 것은 Repository 를 우회한 조회다.

### ★ 이 표준을 따르지 않는 디렉터리 (예외 — 위반이 아니다)

`src/` 하위가 전부 도메인 모듈은 아니다. 아래는 의도된 예외다. 여기 없는 디렉터리를 7파일 표준에서 벗어나게
만들려면 먼저 이 표에 줄을 더한다.

| 디렉터리 | 무엇인가 | 왜 3-Layer 가 아닌가 |
| --- | --- | --- |
| `market_data/` | OHLCV provider(CCXT·Timescale·fixture) 공급 | 공개 REST 가 없는 내부 전용 subdomain 이다([도메인 개요](../../docs/domain/domain-overview.md)). 다른 도메인이 라이브러리로 쓴다 |
| `realtime/` | WS 라우터 + JWT/JWKS 검증기(`auth.py`) + 연결 manager | 검증기는 도메인이 아니라 횡단 관심사다. 원장은 `auth/` 가 갖는다 |
| `health/` | `/healthz`·`/livez` | 상태 프로브다. 소유 엔티티가 없다 |
| `tasks/` | Celery task entrypoint | HTTP 표면이 아니다. prefork-safe 규칙은 §9 |
| `scripts/` | 운영 entrypoint helper | `python -m src.scripts.*` 로 실행한다. 테스트·dogfood 스크립트는 `apps/api/scripts/`(앱 루트)에 둔다 |
| `strategy/narrative/` | [ADR-040] 해설 층 LLM 클라이언트 | DB 세션을 쥐지 않는다. 결정론 브리핑은 `StrategyService` 가 갖고 여기는 LLM 왕복만 한다 |
| `strategy/python_runtime/` | 내부 오프라인 연구용 프로토콜·격리 transport·청산 계산 | 서비스 API·Celery 와 연결하지 않는다([ADR-045]). 소스 실행은 `infra/python-runner/` 의 gVisor 이미지 안에서만 한다 |
| `strategy/code_runtime/` | [ADR-046] 생성 전략의 언어 중립 프로토콜·격리 adapter·공통 백테스트 | DB 세션을 갖지 않는 실행 라이브러리다. Pine/Python/TypeScript 는 gVisor 실행기에서만 돈다. 주문 권한은 trading 이 갖는다 |
| `python_strategy/` | 미사용 연구 원장의 모델 선언 | 기존 DB·마이그레이션 이력 보존 전용이다([ADR-045]) |
| `common/` · `core/` | 기술 기반 · 설정 | 도메인이 아니다 |

`trading/` 은 예외가 아니라 확장이다. `service.py`/`repository.py` 가 `services/`·`repositories/` 디렉터리로 분해돼 있고
`websocket/` 서브패키지를 더 갖는다.

## 4. QuantBridge 도메인 고유 규칙

| 영역 | 규칙 |
| --- | --- |
| Pine Script 변환 | `exec()` / `eval()` 을 쓰지 않는다. 인터프리터(`pine_v2`) 또는 sandbox 로 간다(ADR-003) |
| Pine 미지원 함수 | 하나라도 있으면 전체를 "Unsupported" 로 돌려준다. 부분 실행은 틀린 결과를 낸다 |
| 백테스트·최적화 | Celery 비동기로만 돈다. API 핸들러에서 직접 실행하지 않는다. 결과는 `result_jsonb` 컬럼에 둔다 |
| 거래소 API Key | AES-256(`Fernet`)으로 암호화해 저장한다. 평문 컬럼을 만들지 않는다 |
| OHLCV 시계열 | TimescaleDB hypertable(`ts.ohlcv`)에 둔다 |
| 실시간 가격 | `ws_stream` 별도 queue + prefork worker 다. `docker-compose.yml` 의 ws-stream 서비스가 정본이다 |
| LLM 산출물 | 판정에 쓰지 않는다. 실행 가능·미지원·degraded 판정은 결정론 층(AST·coverage)이 독점한다([ADR-040]). 근거 줄(`pine_lines`)이 없는 LLM 문장은 서버가 버린다 |
| 관측 metric | 업무 결과를 보고하는 `try`·`except` 본문에서 metric mutation 을 raw 로 두지 않는다. `record_metric_safely` 계열로 감싼다. metric 예외가 그 handler 로 흘러 체결을 취소 실패로 기록한 적이 있다 |

## 5. 스트리밍 응답

SSE 를 쓰지 않는다. 진척률은 §6 의 폴링 또는 WebSocket(`realtime/`)이 낸다.

## 6. 비동기 장기 작업 패턴

수초 이상 걸리는 작업(백테스트·최적화·스트레스 테스트)은 HTTP 응답을 막지 않는다. `202 Accepted` 와 task id 를 돌려주고
클라이언트는 polling 또는 WebSocket 으로 상태를 본다. 진행 상태는 DB `status` 컬럼이 갖는다. task entry 규칙은 §9 다.

## 7. DB 마이그레이션 (Alembic)

- `models.py` 를 바꾸면 마이그레이션을 생성해 검토한 뒤 같은 커밋에 넣는다.
- downgrade 는 `-x allow_destructive=1` 이 있어야 돈다. `_test` 접미 DB 만 자동으로 통과한다.
  이 경로로 로컬 개발 DB 가 지워진 적이 있다. 먼저 `mise run db-snapshot` 을 친다.
- 데이터·컬럼 삭제는 2단계로 배포한다 — 코드에서 사용을 멈춘 다음 배포에서 지운다.
- enum value 를 더하거나 뺄 때는 downgrade 안에서 enum swap 패턴을 쓴다([LESSON-066]). 값은 처음부터 uppercase 로 둔다.

마이그레이션이 도는 자리는 환경마다 다르다.

- **로컬** — Docker entrypoint 의 `api` 롤이 `alembic upgrade head` 를 자동 실행한다.
- **CI** — backend pytest 의 스키마는 세션 픽스처의 `drop_all`+`create_all` 이라 마이그레이션을 지나지 않는다.
  `strategy-journey` 잡과 nightly 워크플로는 `alembic upgrade head` 를 돌린다. nightly 가 깨지면 마이그레이션도 원인 후보다.
- **서버** — API 는 호스트 uvicorn systemd 유닛이라 entrypoint 를 지나지 않는다. DDL 은 사람이
  `tools/scripts/deploy.sh --migrate <sha>` 로 친다. 자동 배포는 이미지의 `alembic heads` 가 DB 와 다르면 멈추고
  텔레그램으로 알린다 — 새 코드가 옛 스키마 위에서 도는 경로는 없다([ADR-043]). 절차 = [`backend-deploy.md`](../../docs/operations/backend-deploy.md)

## 8. 백엔드 폴더 구조

구조는 `ls src` 가 정본이다. 이름만 봐서는 틀리기 쉬운 것:

- 조립 전용 디렉터리(`api/`)는 없다. `main.py` 의 `create_app()` 이 라우터를 조립하고 `/api/v1` 프리픽스를 붙인다.
- 7파일은 필수 코어이지 상한이 아니다. 도메인은 `engine/`·`providers/`·`dispatcher.py`·`serializers.py` 같은 부속 모듈을 더 갖는다.
- JWT 검증기는 `auth/` 가 아니라 `realtime/auth.py` 에 있다. `auth/` 는 사용자 원장과 탈퇴를 갖는다.
- `strategy/pine/` 은 v1 잔해가 아니라 공유 타입 모듈이다(`ParseOutcome`·`PineError`·`SignalResult`). 신규 코드는 넣지 않는다.
- `src` 는 설치되는 패키지가 아니다. import 는 CWD 가 `apps/api`(컨테이너 `/app`)라는 사실에 의존하고, 그 사실은
  `pyproject.toml` `pythonpath` · `alembic.ini` `prepend_sys_path` · `Dockerfile` `WORKDIR` 이 함께 세운다.
  디렉터리 이름 `src` 를 바꾸면 이 셋과 `docker-entrypoint.sh`·compose 의 `uvicorn src.main:app`·`celery -A src.tasks` 가 함께 깨진다.

## 9. Celery prefork-safe 패턴

**task entry 는 `asyncio.run(coro)` 대신 `run_in_worker_loop(coro)` 를 쓴다.** `asyncio.run()` 은 task 마다 새 loop 를
만들고, module-level async 상태와 만나면 2번째 task 부터 `RuntimeError("Future attached to a different loop")` 로
조용히 실패한다.

- engine 수명은 task 단위다. `create_worker_engine_and_sm()` 뒤 `finally: await engine.dispose()` 를 둔다.
  loop 를 통일해도 connection pool stale 누수는 남는다.
- `run_in_worker_loop` 를 중첩해 부르지 않는다. 이미 도는 loop 안에서 부르면 `RuntimeError` 다.
- module-level 에 `asyncio.Semaphore/Lock/Event/Queue` 를 두지 않는다. 필요하면 가드의 allowlist 에 이유와 함께 더한다.
- fire-and-forget alert 는 `track_pending_alert(task)` 로 등록한다. `_PENDING_ALERTS` 를 직접 조작하면 gauge 가 어긋난다.
- 수명이 요청보다 긴 `create_task` 에는 `add_done_callback` 을 붙인다. 아무도 `await` 하지 않는 task 의 예외는 저장된 채
  아무도 읽지 않는다. 콜백에서 예외를 로그와 metric 으로 올리고 기다리는 쪽을 깨울 event 를 set 한다. 콜백 자신은
  raise 하지 않는다. private WS supervisor 가 죽고도 lease 를 쥔 채 침묵해 failover 를 막은 적이 있다([BL-837]).
  표준 = `trading/websocket/bybit_private_stream.py` 의 `_on_supervisor_done`.

배선 상세와 allowlist 갱신 절차 = [`celery-prefork.md`](../../docs/development/celery-prefork.md).

## 10. 검사기가 무엇을 보는지 증명해라 ([LESSON-092])

초록은 「통과했다」가 아니라 「내가 본 것 중에는 없었다」만 말한다. 검사기를 만들거나 고치면 변이로 판별한다.

1. 앵커가 1건인가. 0건이면 못 심었고 2건 이상이면 어디가 바뀌었는지 모른다.
2. 치환이 파일에 들어갔는가. sha256 스냅샷으로 심고 되돌린다(`git checkout` 을 쓰지 않는다).
3. 그 줄을 실행하는 입력이 테스트 집합에 있는가. 분기 조건에 기본값이 아닌 설정(feature flag·env)이 걸려 있으면
   그것을 명시로 켜는 케이스를 1건 이상 둔다.

- 판정 명령에 파이프를 붙이지 않는다(루트 `AGENTS.md` §5).
- 주석에 적는 근거 문장도 잰다. 「기본값이 X 라서 이 분기를 지난다」는 코드로 확인한 뒤 쓴다.

전문 = [`docs/lessons.md`](../../docs/lessons.md) 의 LESSON-092 절.

## 규칙 ↔ 집행

집행기가 있는 규칙은 그 테스트·lint 가 정본이다. 「없음」인 규칙을 다시 어기게 되면 집행기를 만든다(루트 `AGENTS.md` §4).

| 규칙 | 집행 | 스코프 |
| --- | --- | --- |
| §2 SecretStr · §4 `exec`/`eval` 금지 | `ruff` `S` | `src` 전체. `S` 는 하드코딩 시크릿의 일부 문자열 패턴만 본다 |
| §3 Repository 밖 DB 접근 | `tests/common/test_repository_boundary_guard.py` | `src`(`tasks/` 포함) — 경계 밖 `select(` · `repo.session` 리치스루 · raw SQL 실행 · `session.get(Model, …)` |
| §3 Router 가 repository 생성·세션 보유 | `tests/trading/test_router_layer_boundary.py` | `src/*/router.py` |
| §4 metric mutation 보호 | `tests/common/test_metric_guard_census.py` | 파일 안 census 에 등재된 자리 |
| §7 downgrade 차단 · `DATABASE_URL` 폴백 차단 | `alembic/env.py` · `tests/conftest.py` · `tests/test_destructive_db_guard.py` | `_test` 접미가 아닌 DB |
| §7 모델이 metadata·alembic 에 등록됨 | `tests/test_metadata_table_coverage.py` | 테이블을 선언하는 모듈 전부 |
| §9 task 의 `asyncio.run()` | `tests/tasks/test_no_asyncio_run_in_tasks.py` | `src/tasks/*.py` |
| §9 module-level loop-bound 객체 | `tests/tasks/test_no_module_level_loop_bound_state.py` | `src/tasks/*.py` · `src/common/*.py` · `src/trading/services/*.py` |
| `.env.example` 계약 | `tests/common/test_env_example_contract.py` | Settings 키 · raw `os.environ` 읽기 |
| §2 Pydantic V2 · `session.exec()` · Decimal-first | 없음 | — |
| §3 `AsyncSession` import · `Depends` import(service·repository) | 없음(위 경계 가드는 사용 형태만 본다) | — |
| §3 commit-spy · 단일 commit | 없음 — PR 리뷰 | — |
| 그 밖의 §4 · §9 규칙 | 확인하지 않았다 — 집행기를 찾으면 이 표에 줄을 더한다 | — |
