# 함정 — 환경·셸·거짓 red

> **진입점은 [`gates-and-traps.md`](./gates-and-traps.md) 다** — 이 파일은 그 §3 함정을 2026-08-21 에 주제별로 나눈 조각이다
> ([ADR-038](../adr/038-docs-top-level-by-question.md) 후속 · 원문 = `git show 9e91809c:docs/development/gates-and-traps.md`).
> **다루는 것:** 로컬 환경·셸·캐시·린트가 게이트를 거짓 red/green 으로 만드는 조건.
> 규율은 ADR-026 ④ 그대로 — 서술만, 지시 금지. 새 함정은 날짜·회차·실측을 적고, 정본 절차가 바뀌면 여기도 같은 PR 에서 고친다.

---

## 환경

- ★★**`pnpm install` 이 `ERR_PNPM_LOCKFILE_BREAKING_CHANGE` 로 죽으면 코드가 아니라 셸이 문제다**
  (2026-08-16 [ADR-036]). 도구 버전 SSOT 가 루트 `mise.toml` 로 옮기면서 `apps/web/package.json` 의
  `packageManager` 를 지웠다 — 그래서 **mise 가 안 걸린 셸**은 corepack 기본값 pnpm **8.15.9** 로
  떨어지고, 그것이 `apps/web/pnpm-lock.yaml`(lockfileVersion **9.0**)을 못 읽는다.
  실측: mise 없이 `pnpm -v` = 8.15.9 → `--frozen-lockfile` **rc=1** / mise shim PATH 에서 9.12.0 → **rc=0**.
  ⇒ 고치는 법은 `brew install mise && mise install` 그리고 `eval "$(mise activate zsh)"` 다.
  ★**`--force` 로 락파일을 다시 쓰지 마라** — CI 의 `frozen-lockfile` 게이트와 정면 충돌한다.
  락파일은 멀쩡하고 틀린 것은 그것을 읽는 pnpm 버전이다.
  ★~~`make` 타깃과 git 훅은 안전하다(`Makefile:15`, `.husky/pre-commit`, `.husky/pre-push`).
  노출되는 것은 **터미널에서 맨손으로 `pnpm`·`uv` 를 칠 때**뿐이다.~~ → **2026-08-17 [BL-785] 이
  절반을 반증했다.** 훅 2종은 그대로 안전하고 `Makefile` 은 [ADR-036] 이 없앴지만, **게이트
  스크립트가 노출돼 있었다** — `final-gates.sh` 가 `uv`·`pnpm`·`node` 를 PATH 로 부르고 있었고,
  그래서 pnpm 8 셸에서는 **lockfile diff 가 0 인 브랜치도 `CI frozen-lockfile` 이 red** 였다.
  증상이 「내 PR 이 lockfile 을 깼다」로 오인된다. ⇒ 로컬 스크립트 5종이 이제
  `tools/scripts/lib/mise-shim-path.sh` 를 소싱해 shim 을 PATH 앞에 세우고,
  `tools/scripts/tool-pin-audit.sh` 가 재유입을 막는다(`final-gates` 의 「도구 핀 감사」).
  ★**서버에서 도는 `soak-*.sh` 6종은 면제다** — 그 환경에 mise 가 있는지 확인된 바 없다.
  ★**워크스페이스가 아니다** — 루트 `package.json` 은 husky 전용이고 `pnpm-workspace.yaml` 이 없다.
  FE 설치는 반드시 `cd apps/web` 에서 한다.
- ★★**BE pytest 는 격리 포트(5433/6380)를 쓴다 — `mise run up` 으로 올린 기본 스택(5432/6379)에서는 안 돈다.**
  `apps/api/.env.local` 의 `DATABASE_URL`·`TEST_DATABASE_URL`·`REDIS_URL` 이 전부 격리 포트를 가리킨다.
  기본 스택에서 돌리면 **`6 failed / 604 errors`** 가 나는데 실패의 정체는 `asyncio/base_events.py` 의
  `OSError`(연결 실패)이고, `test_migrations.py` 가 `sqlalchemy.exc.OperationalError` 로 먼저 눈에 띄어
  **코드 회귀처럼 보인다**(2026-08-08 실측, 13분을 버렸다). ⇒ **게이트가 red 면 코드를 의심하기 전에
  「내가 그 게이트를 올바른 환경에서 돌렸나」를 먼저 물어라.**
  ★워커를 띄우고 싶지 않으면 `DC="docker compose --project-directory . -f infra/compose/docker-compose.yml -f infra/compose/docker-compose.isolated.yml"; $DC up -d db redis`
  로 **두 서비스만** 올려라 (★`--project-directory .` 를 빼면 프로젝트명·볼륨이 `infra/compose` 기준으로
  파생돼 기존 볼륨이 고아가 된다 — ADR-029). 기본/격리는 `container_name` 이 같아 **동시 운영이
  불가능하다** — 갈아탈 때는 먼저 `$DC stop db redis && $DC rm -f db redis` 로 비워라.
- **BE pytest 는 `.env.local` 을 통째로 source 해야 한다.**
  ```bash
  set -a; source .env.local; set +a
  ```
  개별 export 금지. `DATABASE_URL` 만 있으면 `tests/test_migrations.py` 의 `downgrade(base)` 가 **개발 DB 를 향했다** — 실제로 주문 17행과 암호화된 API 키가 전소한 적이 있다.
  ★**2026-08-10 [BL-451] 이후 그 폴백은 사라졌다.** 판정 SSOT 는 `apps/api/tests/_db_guard.py` 이고 루트 `tests/conftest.py::pytest_configure` 가 **세션 최상단**에서 판정한다. `TEST_DATABASE_URL` 없이 `DATABASE_URL` 만 있으면 폴백이 아니라 **rc=3 으로 세션이 끝난다**. 그래도 3-env 를 함께 넣어라 — 가드는 「막는다」이지 「돌게 한다」가 아니다.
  ★**종전 문장 「`_assert_disposable_database` 가 막는다」는 절반만 참이었다.** 그 가드는 `tests/test_migrations.py` 파일 안에만 있었고, 같은 판정의 사본이 `tests/real_broker/conftest.py` 에 있었지만 그 파일은 **그 디렉터리를 수집할 때만** 로드됐다. 실측 — `DATABASE_URL`(개발 DB) 하나만 있는 셸에서 `pytest tests/trading/` 이 **rc=0 으로 1088건을 수집**했고, 그 경로의 세션 픽스처는 `SQLModel.metadata.drop_all` 을 돈다.
- **수동 `alembic downgrade` 는 개발 DB 를 향했다.** ★2026-08-10 이후 `apps/api/alembic/env.py` 가 **downgrade 만** 골라 막는다(`upgrade` 는 통과 — 안 그러면 `mise run migrate`·entrypoint·CI 가 함께 죽는다). 정당한 롤백은 `alembic -x allow_destructive=1 downgrade <rev>`.
  ★**이 가드가 못 보는 표면이 하나 있다** — `command.downgrade(cfg, ...)` 처럼 파이썬에서 직접 부르면 `config.cmd_opts` 가 `None` 이라 방향을 알 수 없다. 그 표면은 pytest 쪽 가드가 덮는다.
- ★**파괴적 작업 전에 찍어라 — `mise run db-snapshot`.** `.backups/<db>-<ts>.dump` 로 나온다(gitignore). 복원은 `mise run db-restore FILE=… TO=<대상 DB>` 이고 **`TO` 에 기본값이 없다** — 기본값을 개발 DB 로 두는 편의가 곧 이 항목이 막으려는 사고다. 2026-08-10 실측: 덤프 2.15MB → 임시 DB 복원에서 orders 823 · 암호화 API 키 2/2 가 왕복했다.
- ★★**`alembic check` 는 「migration 으로만 만든 DB」에 대고 재는 것이 정본이다** (2026-08-17 [BL-782]).
  이 레포에는 스키마를 만드는 경로가 둘이다 — `alembic upgrade head` 와 `SQLModel.metadata.create_all`
  (pytest 픽스처). **둘의 결과가 갈릴 수 있고 실제로 갈렸다.** 그래서 「어느 DB 에 대고 재는가」를
  정하지 않으면 같은 명령이 환경마다 다른 답을 낸다 — [BL-770] 이 「`alembic check` rc=0 이 처음」
  이라 닫은 측정이 그 예다. 그것은 **개발 DB** 에 대한 것이었고, 개발 DB 는 `create_all` 이력이
  섞여 있어 `trading.funding_rates.exchange` 가 이미 enum 이었다(2026-08-17 실측: 개발 DB 는
  head `20260816_0001` 인데 그 컬럼이 `exchangename`, migration 계보로만 만들면 `varchar(32)`).
  **판정 기준을 migration-only 로 두는 이유는 하나다 — migration 이 프로덕션 스키마를 만드는
  유일한 경로**이므로, 그 DB 에서의 drift 만이 배포에서 실제로 터진다.
  ⇒ 정본 판정은 게이트의 **`CI fresh DB alembic`** 축이다(throwaway `quantbridge_ci_repro_test` 에
  `alembic upgrade head` → `alembic check`). 손으로 재려면 같은 절차를 밟아라 —
  **개발 DB 나 pytest DB 에 대고 잰 rc 는 이 질문의 답이 아니다.**
  ★파이프를 붙이지 마라. `alembic check` 는 실패 시 **rc=255** 다(1 이 아니다).
  ```bash
  DB=quantbridge_alembic_check_test
  docker exec quantbridge-db psql -U quantbridge -d postgres -qc "DROP DATABASE IF EXISTS $DB;"
  docker exec quantbridge-db psql -U quantbridge -d postgres -qc "CREATE DATABASE $DB;"
  cd apps/api; set -a; . ./.env.local; set +a
  export DATABASE_URL="postgresql+asyncpg://quantbridge:password@localhost:5433/$DB" TIMESCALE_URL="$DATABASE_URL"
  uv run alembic upgrade head > /tmp/up.log 2>&1; echo "upgrade rc=$?"
  uv run alembic check   > /tmp/ck.log 2>&1; echo "check   rc=$?"
  ```
- **`test_migrations.py` 가 `DuplicateColumn` 으로 실패하면 대개 코드 결함이 아니다.** conftest 의 `SQLModel.metadata.create_all` 이 신규 컬럼을 이미 만들어둔 상태에서 `alembic_version` 만 stale 인 경우다. `downgrade base → upgrade head` 로 재구축하면 풀린다.
- compose 는 항상 두 파일을 겹쳐 쓴다. worker 만 재시작할 때는 **`--no-deps`** 를 붙여라.
  ```bash
  docker compose -f infra/compose/docker-compose.yml -f infra/compose/docker-compose.isolated.yml ... --no-deps
  ```
- Docker VM 디스크가 차면 Postgres 가 무한 크래시 루프에 빠진다. **`docker builder prune -f` 만 안전**하다 (볼륨·이미지 prune 금지).
- ★**워커는 `apps/api/src` 를 `/app/src` 로 bind-mount + watchfiles 로 문다.** 작업 중인 코드가 실거래 세션에 **즉시** 반영된다. 관측에는 유용하지만(수정 전후를 실데이터로 잡을 수 있다) **변이 스크립트를 돌리기 전에는 워커를 멈춰라** — 문법을 깨는 변이면 평가가 예외로 죽고 세션이 자동 비활성화된다.
  ★★**변이 스크립트만의 문제가 아니다. 평범한 여러-단계 편집도 같은 함정이다.** 호출부를 먼저 넣고 헬퍼를 나중에 정의하는 순간, 그 **사이**에 watchfiles 가 중간 상태를 물어 `NameError` 로 평가가 죽고 세션이 fail-closed 비활성화된다. 2026-07-27 실측 — 활성 라이브 세션이 `live_signal_run_live_crash / NameError: name '_pending_fills_blocked_by_session' is not defined` 로 종료됐다(포지션·미체결은 0이라 피해는 없었다). **라이브 경로 모듈(`event_loop.py` / `strategy_state.py` / `tasks/live_signal.py`)을 편집할 때는 활성 세션이 없는지 먼저 확인하거나 beat 를 멈춰라.** 편집이 원자적일 거라고 가정하지 마라.
- ★**`codex exec -s workspace-write` 의 쓰기 루트 = 호출 시점 cwd.** 다른 디렉터리에서 부르면 대상 밖 파일 패치가 권한 거부되고 **0건 변경**으로 조용히 끝난다. 호출 전에 `pwd` 로 리포 루트를 확인해라. 그리고 `codex exec` 는 10분을 넘길 수 있어 Bash 상한(600000ms)에 걸리는데, **그때도 파일은 이미 쓰여 있을 수 있다** — 죽었다고 재실행하기 전에 `git status` 부터 봐라.
- ★**codex 샌드박스는 격리 Postgres(5433)에 못 붙는다.** 실DB 테스트가 `PermissionError` 로 `errors` 에 잡힌다. **메인 세션이 다시 돌려야 진짜 결과가 나온다**(실측: codex "7 errors" → 메인에서 282 passed). 그리고 **codex 자기보고를 재검증해라** — "gates-and-traps 에 승격했다" 고 보고했지만 파일이 미변경인 사례가 있었다.
- ★★★**`mise run up` / `mise run up-isolated` 는 세션을 만들지 않지만 `is_active` 로 남아 있던 세션을 되살린다.** 그리고 그 부활한 세션은 소크와 **같은 Bybit demo 계정**에 붙는다. 2026-08-07 실측 — 로컬 세션 `fcf1dcbe`(08:52 생성)가 13:52 의 `mise run up` 으로 부활해 16:44 까지 발주했고, 서버 소크 세션 `39484a2c` 를 `position_divergence` 로 죽였다. ★★**그런데 `is_active` 를 끄는 것만으로는 부족하다** — 이미 **체결된 포지션**은 그대로 남는다. 2026-08-08 재부검 실측: 로컬은 `mise run up` **전인** 07:42·07:50·08:10·08:51·09:03 에 이미 체결했고, 로컬 워커가 멈춰 있던 09:23~13:53 구간에도 서버가 09:35·09:36·09:37 에 `category=exchange_only engine_position=0.0 exchange_position=0.029` 를 관측했다 — 그 0.029 는 로컬 `541c6ee1`(09:03:53 buy 0.029)의 포지션이다. **호스트를 세워도 포지션은 계정에 남아 계속 발산을 만든다.** ⇒ **로컬 스택을 켜야 하면 ⑴ 켜기 전에 `live_signal_sessions` 의 `is_active` 를 끄고 ⑵ 거래소가 실제로 flat 인지(`FLAT=YES` **AND** resting 조건부 0) 확인해라.** 판정 도구 = `apps/api/scripts/live_session_admin.py status` 의 `FLAT=` · `RESTING_CONDITIONAL=` · `EXCLUSIVE=` 세 줄. ⇒ 원장만 읽으면 되는 경우엔 스택 전체 대신 `docker compose up -d db` 로 **db 서비스 하나만** 올려라 — 워커가 없으므로 세션 부활도 발주도 구조적으로 불가능하다.
- ★**워커 로그 follow 는 `tools/scripts/soak-logs-follow.sh` 가 정본이다** — `--install` 은 systemd user unit(+`loginctl enable-linger`) / macOS launchd 로 승격하고, `--status` 가 유닛 생존과 로그 나이를 답한다. ★**`nohup` 판(`.soak/logs/follow.sh`)은 ssh 세션·재부팅을 못 넘는다** — 같은 `LOG_FILE` 에 둘이 붙으면 줄이 섞이므로 `--install` 전에 `pgrep -f 'soak/logs/follow.sh'` 로 옛 프로세스를 먼저 죽여라.
- ★**서버 게이트는 언제나 `ssh <서버> 'bash -lc "…"'` 로 불러라.** 비로그인 셸엔 PATH 에 `uv` 가 없어 phantom 분류기가 실패하고 그 구간이 커버리지에서 잘려나간다(2026-08-07 실측 8분 손실).
- ★**서버 `psql` 은 SQL 을 파일로 넣어라** — `scp` → `docker cp` → `psql -f`. 따옴표가 ssh · `bash -lc` · `docker exec` 로 3중 중첩되면 ssh 를 넘어가면서 깨진다(2026-08-08 재현).
- ★**`.metrics` 는 프로세스 역할 + 컨테이너 id 로 파일이 갈린다.** 파일명은 `counter_<role>-<HOSTNAME>-<pid>.db` 이고 `<role>` 은 `worker`/`api`/`beat`/`wsstream`/`optheavy`, `<HOSTNAME>` 은 컨테이너 id 다(`apps/api/src/common/metrics_multiproc.py:105-107` 이 접두사를 만든다). 디렉터리는 마운트라 **죽은 컨테이너의 파일이 그대로 남는다.** ⇒ **전 PID 합산은 「지금 창」의 값이 아니다** — 2026-08-08 실측에서 `engine_only_suppressed` 합산 89 중 **15** 가 이전 컨테이너 것이었다. 창 값을 원하면 현재 컨테이너 id 로 먼저 걸러라.

## 셸·게이트가 거짓 red 를 내는 경로 (2026-07-28)

- ★★**Bash 도구의 cwd 는 호출 간 유지된다.** `cd apps/api && set -a; . ./.env.local; set +a; uv run pytest` 를 **두 번째로** 부르면 `cd apps/api` 가 실패하고 `&&` 때문에 **`set -a` 가 안 돈다.** env 가 export 되지 않아 `localhost:5432` 로 붙고 대량 에러가 난다 — 코드 결함처럼 보이는 거짓 red 다. **절대경로로 `cd` 해라.**
- ★★**부분 선택 실행은 격리가 깨진다.** `pytest tests/tasks/x.py tests/trading/ tests/strategy/` 조합에서 **30건이 실패**했지만 같은 테스트를 단건으로 돌리면 통과하고 **전체 스위트도 통과**한다. 판정 권위는 **전체 스위트**다.
- ★★★**파이프에 넣은 게이트의 종료 코드는 파이프 **끝** 명령의 것이다.** `playwright … | tail -40`
  의 rc 0 은 tail 의 성공이고, 그 뒤에 `2 failed` 가 숨어 있었다(2026-08-10 실측 — 하마터면 baseline
  을 「전건 통과」로 적을 뻔했다). ⇒ **게이트는 파일로 받고(`> /tmp/g.txt; echo $?`) 출력을 읽어라.**
  ★**zsh 에서 `${PIPESTATUS[0]}` 는 빈 문자열이다** — zsh 의 배열은 소문자 `pipestatus` 이고 1-기반이라
  `${pipestatus[1]}` 이 첫 명령이다. bash 관용구를 그대로 쓰면 **아무 값도 안 나오는데 조용하다.**
- ★★**zsh 는 `$VAR` 를 단어분리하지 않는다(`SH_WORD_SPLIT` off) — 변이 판정이 통째로 무효가 된다.**
  `T="a.test.ts b.test.ts"; vitest run $T` 는 **한 인자**로 들어가 vitest 가 아무것도 매치하지 못하고,
  `grep "Tests"` 가 침묵해 **「전부 초록」처럼 보인다**(2026-08-10 실측: 변이 3건의 판정이 공백이었다).
  ⇒ **배열로 써라** — `T=(a.test.ts b.test.ts); vitest run "${T[@]}"`. 위 `$ARGS` 항목과 같은 뿌리이고
  **이번엔 셸이 아니라 판정을 삼켰다.**
- ★**`pnpm test --outputFile=…` 은 pnpm 이 인자를 삼킨다** — 리포터 옵션이 vitest 에 도달하지 않고
  파일이 안 생긴다. `pnpm exec vitest run --outputFile=…` 로 **pnpm 을 우회**해라.
- ★**`rm -rf` 는 권한에서 거부될 수 있다**(2026-08-09·08-10 연속 3회). 대안은 스크래치패드로
  `mv` 해 격리하는 것이고, 결과는 같다. **cwd 착오로 「캐시 없음」이라 오판한 적이 있으니 절대경로로 재라.**
- ★★★**병렬 fan-out 이 0행을 냈고, 그것을 조용하게 만든 것은 내가 붙인 `2>/dev/null` 이었다**
  (2026-08-12 branch-debris, 두 경로로 각각 한 번씩). ⑴ **zsh 의 `export` 는 `-f` 를 옵션으로 받지
  않는다** — bash 관용구 `export -f probe; xargs -I{} bash -c 'probe "$@"' _ {}` 를 쓰면 zsh 가
  **함수 정의를 stdout 으로 출력**하고(실측: `f () {` / `echo hi`) 결과는 **0행**이다.
  ⑵ 고쳐 쓴 `xargs -P 6 -d '\n'` 의 `-d` 는 **GNU 전용**이고 macOS(BSD) xargs 는 무시가 아니라
  **`xargs: invalid option -- d` 로 죽는다**(실측). ★**두 번 다 실제로는 시끄러웠다** — 내가
  `2>/dev/null` 로 stderr 를 버려서 조용해 보였을 뿐이다.
  ⇒ **함수를 export 하지 말고 스크립트 파일로 빼라**, `-d` 대신 `-I{}`(개행 구분) 를 써라,
  **fan-out 의 stderr 를 버리지 마라**(파일로 받아 읽어라), 그리고 **`[ "$(wc -l < out)" -eq "$N" ]`
  가드를 걸어라** — 이번에 0행을 성공으로 읽지 않게 막은 것은 그 가드 하나뿐이었다.
  「전건 조회했다」는 보고가 **아무것도 조회하지 않은 것**일 수 있다.

## 린트가 잡는 문자

- **RUF003** — 주석 안의 `×`(MULTIPLICATION SIGN) 와 `−`(MINUS SIGN) 가 ruff 를 깬다. ASCII `x` 와 `-` 를 써라. 네 번 재발했다. `tests/` · `tools/scripts/` · `alembic/versions/` 는 면제지만 `src/` 는 아니다.
- **디자인 캐논 em-dash 래칫** — `apps/web/src/__tests__/design-canon-source.test.ts` 가 노출 산문의 `—` 를 **파일별 정확 카운트로 양방향 동결**한다. 늘어도 줄어도 RED 다. `EM_DASH_ALLOWLIST` 를 올리지 말고 **문구에서 빼라**.
  ★ 이 래칫은 **FE 소스만 스캔한다.** 서버가 보내 화면에 렌더되는 문자열은 안 잡히므로 백엔드 문자열은 사람이 지켜야 한다.
  ★★**주석은 안 센다** — `stripComments` 로 지운 뒤 세고 `__tests__` 는 제외한다(2026-08-10 코드 대조).
  종전에 돌던 「FE 주석에 `—` 금지」는 **현행 코드에 거짓**이다. 잡히는 것은 **JSX/문자열 산문**뿐이고,
  양옆이 둘 다 비단어인 고립 `—`(`<td>—</td>` 같은 자리표시자)도 정당하다.
- **`@typescript-eslint/consistent-type-imports`** — 인라인 `import("@playwright/test").Page` 형태의
  타입 주석이 **금지**다. pre-commit 에서만 물리므로 `tsc --noEmit` 초록을 근거로 넘기지 마라.
  상단에서 `import { type Page } from "…"` 로 받아라.
- **`docs-audit` 이 세는 것은 낱말이 아니라 구문 `다음 행동 =` 이다.** 그리고 **인라인 백틱 안은
  건너뛴다**(`docs-audit.sh:317-322`) — 규칙을 설명하는 문장이 규칙 자신을 인용해야 하기 때문이다.
  ⇒ 규칙을 인용할 때는 **문장을 비틀지 말고 백틱으로 감싸라.** 취소선(`~~`) 안도 세지 않는다.
  ★종전 메모의 「인용문도 센다」는 **낡았다**(2026-08-10 코드 대조로 반증).
- **`[BL-NNN]` 바로 뒤에 괄호로 설명을 붙이면 깨진 링크가 된다.** 그 괄호가 링크 타깃으로 읽혀
  `docs-audit` 이 잡는다(실측 4건 RC=1). 설명은 **괄호 밖으로** 빼라 — `[BL-693] 전부 P3`.
  ★**이 항목을 쓰다가 그 게이트에 물렸다** — 위반 예시를 그대로 적었더니 예시가 곧 위반이었다.
  함정을 문서화할 때는 **위반형을 리터럴로 쓰지 말고 서술해라.**

## 언어·타입

- **`bool("false") is True`** — TradingView alert 은 문자열 불리언을 보낸다. 명시 화이트리스트로 방어해라.
- **`getattr(x, "f", False)`** 는 미구현 필드를 정상 False 로 위장한다.

## 게이트가 **거짓 red** 를 내는 경로 (2026-07-27 live-conditional-hardening)

- ★**dev 서버의 Turbopack CSS 캐시는 오래 살아남고, e2e 는 그 stale 자산을 검사한다.** `PLAYWRIGHT_BASE_URL=http://localhost:3100` 은 **실행 중인 dev 서버**를 재사용하므로, 그 서버가 옛 CSS 를 서빙하면 이미 고친 캐논이 다시 red 로 나온다. 거짓 그린만 조심할 게 아니다.
  - **판별법 = 세 층 대조.** ① 소스(`globals.css`) ② 프로덕션 빌드(`.next/static/chunks/*.css`) ③ **dev 서버가 실제로 서빙하는 것**. ③만 다르면 캐시다.
  - 서빙본 확인은 CSSOM 이 아니라 **원문 fetch** 로 해라 — `document.styleSheets` 순회는 inline sheet 를 놓치거나 `cssRules` 접근이 막힐 수 있어 "매치 규칙 0개" 같은 오답을 준다. `fetch(sheet.href).then(r => r.text())` 후 정규식으로 규칙을 찾아라.
  - 실측 — 소스·프로덕션 빌드에는 `.pager-nums{flex-wrap:wrap}` 이 있고 dev 서빙본에는 **없었다**. 프로덕션 빌드를 별도 포트에 띄워 재실행하니 그 캐논이 통과했다.
  - **이 함정의 4차 재발이다.** 앞선 세 번은 "고쳐도 적용이 안 된다" 는 인상으로 나타났다.
  - ★★**5차 재발 (2026-08-11 ledger-truth) — 그리고 「재기동뿐」이 불완전함이 실측으로 드러났다.**
    같은 커밋에서 `e2e design-canon` 이 **PASS → 5 failed** 로 뒤집혔다(코드 변경 0 · frontend diff 0 ·
    `:3100` 은 200). 오래 띄워 둔 dev 서버의 `.next` 가 **1.5GB** 였다.
    **원인을 분리해 쟀다** — 처음엔 재기동과 캐시 제거를 **같이** 해서(42 passed) 무엇이 고쳤는지
    몰랐다. 그래서 스테일 캐시를 되돌리고 **재기동만** 다시 했다:

    | 조건                               | 결과                     |
    | ---------------------------------- | ------------------------ |
    | 오래 띄운 서버 + 스테일 캐시 1.5GB | **5 failed**             |
    | **재기동만** (같은 스테일 캐시)    | **1 failed / 41 passed** |
    | 재기동 + 캐시 제거                 | **42 passed**            |

    ⇒ **재기동이 5건 중 4건을 고치고, 마지막 1건은 캐시 제거가 필요했다.** 남은 1건은
    `design-canon-calibration.spec.ts:121`(라이트 2벌 캘리브레이션)이다. 재기동 후 초록을 보고
    「캐시는 무관」이라 결론내면 다음 사람이 같은 1건에 걸린다.

  - ★★**복구 절차 — 순서가 전부다** (2026-08-17 [BL-795] 로 통합. 종전 「복구 = 재기동뿐,
    지우지 말고 재기동해라」는 **폐기한다** — 그 문장은 2026-07-27 관측 1점에서 나왔고
    위 5차 재발 표가 반증했다. 「지우지 마라」의 진짜 근거는 **살아 있는 서버 밑에서** 지우면
    `routes-manifest.json` ENOENT 로 그 서버가 500 을 낸다는 것이지, 캐시가 무해하다는 것이 아니다):
    1. **재기동만** 먼저 — dev 서버를 죽이고 다시 띄운 뒤 같은 명령을 돌린다. 2026-07-27 에는
       코드 변경 0으로 **64/1 → 65-0** 이 됐고, 2026-08-11 에는 5건 중 4건이 이걸로 풀렸다.
    2. 그래도 남으면 **서버가 죽은 상태에서** 캐시를 치운다 — `rm -rf apps/web/.next`.
       삭제보다 `mv` 로 격리하는 편이 가역적이다. 경로는 **절대경로**로 재라(2026-08-09 에 cwd
       착오로 「캐시 없음」이라는 거짓 판정을 한 이력이 있다 — 실제 372MB 였다).
    3. 치운 뒤 다시 띄운다.

    ★**증상이 「stale 자산」이 아니라 「컴파일이 안 끝난다」로 나타나면 1번을 건너뛰고 2번으로
    가라** — [BL-795] 축이다(`setup` 단계에서 `/sign-in` goto 120초 초과 · next-server CPU 0.0%).
    구분식은 [`traps-ci-e2e.md`](./traps-ci-e2e.md) §「e2e 가 게이트에서만 red 일 때」의 두 축 표에 있다.
    ★**크기로 판정하지 마라.** `mise run fe` 의 1GB 경고선은 [BL-650] 이 「정책이 아니라 관측
    장치, 근거는 두 점뿐 — 인용 금지」라고 못박은 값이다.

- ★**프로덕션 빌드로 e2e:authed 를 대신 돌리면 다른 것이 깨진다.** 그 suite 는 로컬 dev 전용이다(빌드 타임 env·`e2e/global.setup.ts` 가 발급하는 storageState 전제). 프로덕션 실행은 **"코드가 맞다" 의 증명**으로만 쓰고, 게이트 숫자는 dev 서버를 재기동한 뒤 다시 재라.

## 캐시·주기 (2026-07-27 live-conditional-hardening)

- ★**새 Redis 캐시 키를 만들면 "누가 이 키를 지우는가" 를 같은 PR 에서 답하라.** 계정 스코프 포지션 캐시를 넣으면서 무효화 경로를 안 만들었고, 기존 세션 키 삭제는 **활성 세션 순회**라 활성 0건이면 아무것도 안 지웠다 — 그런데 그 기능이 존재하는 이유가 정확히 "활성 세션 0건" 상태였다. 결과는 청산 직후 15초 동안 **닫은 포지션이 살아 있는 청산 버튼과 함께 다시 렌더**.
  - ★**React Query invalidate 는 서버 캐시를 지우지 않는다.** 쿼리 키를 잘 배치해도 재조회가 서버 TTL 캐시에 적중하면 낡은 값이 그대로 온다. "무효화는 이미 맞다" 를 쓰기 전에 **양쪽 층을 다 확인**하라.
  - ★**dogfood 통과가 커버리지가 아니다.** 이 결함은 dogfood 를 통과했다 — 청산 후 확인까지 30초 넘게 걸려 15초 TTL 창을 못 밟았을 뿐이다.
- ★**"tick 간격" 을 상수의 근거로 삼기 전에 그 tick 이 실제로 언제 도는지 읽어라.** 라이브 평가는 beat 가 60초마다 fire 하지만 `no_new_bar` 조기 return 때문에 reconcile 은 **bar 마다**(1m/5m/15m/1h) 돈다. 60초를 전제로 잡은 3분 게이트는 1h 세션에서 보호값이 0이었다.
- ★**나이로 "사라졌다" 를 판정하지 마라.** 주문의 나이(`submitted_at`)와 부재의 나이는 다른 값이다. 조건부 주문은 정의상 오래 resting 한다. 부재는 **거래소에 직접 물어**(`fetch_order`) terminal 인지 확인하는 것이 유일하게 옳다.
