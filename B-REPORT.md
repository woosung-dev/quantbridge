# 레인 β 보고 — [BL-785] 게이트 도구 버전 핀 · [BL-782] `alembic check` 의 정본 DB

브랜치 `stage/bl785-782-gatepins` · 워크트리 슬롯 4 · 2026-08-17.
**두 항목 모두 수용 기준을 전부 충족했다.** push·PR 은 안 했다(계약대로).

---

## 무엇이 됐나

**[BL-785]** — 로컬에서 도는 스크립트 5종이 이제 `mise.toml` 핀을 따른다. 낡은 `pnpm`(8.15.9)을
PATH 앞에 세운 셸에서 **수리 전에는 `CI frozen-lockfile` 이 red, 수리 후에는 green** 이다.
재유입은 새 게이트 「도구 핀 감사」가 막고, 그 감사기 자신의 판별력은 하네스 13케이스가 잰다.

**[BL-782]** — `alembic check` 의 정본은 **migration 으로만 만든 DB** 라고 정하고 문서에 적었다.
그 기준으로 남아 있던 **유일한 drift 1건**(`trading.funding_rates.exchange`)을 migration 으로 닫았고,
게이트 `CI fresh DB alembic` 이 `upgrade head` 뒤에 `alembic check` 까지 돈다.

---

## 이 회차가 반증한 것

**⑴ [BL-770] 의 「`alembic check` rc=0 이 처음」은 측정 대상 DB 에 의존한 참이었다.**
2026-08-17 실측 — 개발 DB 는 head `20260816_0001` 인데 `trading.funding_rates.exchange` 가 이미
`exchangename` 이다. 같은 head 를 **migration 계보로만** 만들면 `varchar(32)` 다. 개발 DB 에는
`create_all` 이력이 섞여 있어서다. 즉 같은 명령이 DB 마다 다른 답을 냈고, 그 사실을 아무도
적어두지 않아 판정 기준 자체가 없었다.

**⑵ `gates-and-traps.md` 의 「`make` 타깃과 git 훅은 안전하다 — 노출되는 것은 터미널에서
맨손으로 칠 때뿐이다」가 절반 거짓이었다.** 훅 2종은 실제로 안전했지만 **게이트 스크립트가
노출돼 있었고**, `Makefile` 은 [ADR-036] 이 이미 없앤 파일이었다. 그 문장을 정정했다.

**⑶ 내 수리가 만든 회귀를 표적 테스트가 못 봤다.** `docs-audit.sh` 에 핀을 넣자
`docs-audit-test.sh` 가 fixture 트리에 `lib/` 를 안 옮겨 **19케이스가 전부 rc=1** 이 됐다.
`tool-pin-audit` 표적 테스트 13건은 전부 초록이었고, 잡은 것은 **게이트 전량 실행**이다.
(선례가 이미 있었다 — `soak-watch-test.sh:142` 가 2026-08-16 에 같은 자리를 같은 방법으로 고쳤다.)

**⑷ 전량 pytest 의 대량 `E` 도 내 변경이 아니라 낡은 테스트 DB 였다.** 1회차 실행이 1%부터
`E` 를 쏟아내 [BL-782] 회귀처럼 보였다. 실제 원인은 `quantbridge_w4_test` 에 남아 있던 이전
스키마 상태이고, 증상은 teardown 의
`ALTER TABLE strategies DROP CONSTRAINT fk_strategies_strategy_version_id_strategy_versions` 실패다
(`create_all` 이 아는 metadata 로는 그 잔존 FK 를 못 지운다). DB 를 재생성하니 사라졌다 —
`tests/trading` **1116 passed rc=0**. ★게이트가 red 면 코드를 의심하기 전에 환경을 먼저 물어라는
`gates-and-traps.md` §환경의 항목이 그대로 재현됐다. ★그리고 그 재생성이 **다음 항목을 드러냈다** —
낡은 DB 가 가리고 있던 것이 있었다.

**⑸ 전량 pytest 의 2건 실패는 내 것이 아니었고, 「기준선 4759 green」은 낡은 DB 에서만 참이었다.**
`tests/test_migrations.py` 의 `test_alembic_roundtrip`·`test_strategy_version_migration_backfills_
existing_backtests` 가 `downgrade base` 의 `DROP TABLE auth_jwks` 에서 죽었다. **대조군으로 확정** —
내 migration 파일을 빼고 fresh DB 에서 전량을 다시 돌렸더니 **같은 2건이 같은 이유로 실패**했다
(`4757 passed` 로 숫자까지 같다).

기전: `src/auth/better_auth_tables.py` 가 `auth_*` 5테이블을 `SQLModel.metadata` 에 등록하는데
**그 파일을 import 하는 곳이 `alembic/env.py` 하나뿐**이었다(전수 grep). `tests/conftest.py::
bootstrap_test_schema` 는 `create_all` 로 스키마를 만든 뒤 `alembic_version` 을 **생 SQL 로** head
stamp 하므로 env.py 가 안 실린다 ⇒ fresh DB 에서는 그 5테이블이 **안 만들어진 채 head 로 기록된다.**
그 뒤 `test_migrations.py` 의 첫 `command.upgrade()` 가 env.py 를 실어 테이블을 metadata 에
등록하고, 이어지는 `downgrade base` 가 없는 테이블을 지우려다 죽는다.
★**이전에 migration 이 돈 DB 에는 그 테이블이 남아 있어 통과한다** — 그래서 원장의 「BE 4759 passed」는
거짓이 아니라 **더러운 DB 에서 잰 값**이다. 이 자리의 병이 [BL-782] 와 같은 병(`create_all` 경로 ≠
migration 경로)이고 층만 다르다 — 저기는 컬럼 타입, 여기는 테이블 존재.

수리 = `tests/conftest.py` 에 import 한 줄 + 그 자리의 근거 주석. **두 BL 어느 쪽도 아니므로 아침에
별건으로 판단해라**(새 BL 후보). 고치지 않으면 fresh DB 에서 AC-8 이 구조적으로 불가능하다.

**⑹ 감사기 초판이 두 형태를 통째로 놓쳤다.** `timeout 120 uv run python`(레포에 3곳)과
히어독 안 `shutil.which("node")`(1곳). 둘 다 하네스 케이스로 고정했다(②③). 또 초판의 핀 판정이
「파일에 그 문자열이 있으면 핀」이라, **자기 자신의 「고치는 법」 안내문이 자기를 핀으로 만들었다** —
명령 위치 판정으로 바꾸고 하네스 케이스 ④ 로 고정했다.

---

## 수용 기준별 판정

### AC-1 — 핀 밖 직접 호출 0건 ✅

★**「0건」의 정의를 먼저 적는다.** 수리를 `mise exec --` 가 아니라 **PATH 핀**으로 했으므로
(계약이 허용한 두 갈래 중 후자, `.husky/*` 선례) `uv run ruff check .` 이라는 **문자열은 그대로
남는다**. 재는 것은 텍스트 0건이 아니라 **핀 밖 0건** — 그 스크립트가 도구를 부르는데 핀이 없는가다.

판정 명령(다음 사람이 그대로 재실행하면 된다):

```bash
tools/scripts/tool-pin-audit.sh           # rc=0 = 위반 0건. 사람이 읽는 표까지 인쇄한다
tools/scripts/tool-pin-audit.sh --list    # 위반 경로만. 출력 0줄 + rc=0 이 「0건」이다
```

실측 2026-08-17 — `--list` **출력 0줄 · rc=0**. 대상은 `tools/scripts/**/*.sh` **41개**
(그중 `lib/` 3개) + `.husky/pre-commit`·`pre-push` **2개** = **43개**.

| 분류               | 개수   | 파일                                                                                                                                                       |
| ------------------ | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 핀 있음            | 7      | `final-gates.sh` · `worktree-bootstrap.sh` · `docs-audit.sh` · `bybit-smoke.sh` · `nightly-real-broker-local.sh` · `.husky/pre-commit` · `.husky/pre-push` |
| 서버 실행이라 면제 | 4      | `soak-gate.sh` · `soak-stack.sh` · `soak-restart.sh` · `soak-observe.sh` (AC-4)                                                                            |
| 호출 0건           | 나머지 | `e2e-authed-repro.sh` 는 이미 전 호출이 `mise exec --` 라 이 축에서 0건이다                                                                                |

수리 대상은 **5종**이었다(훅 2종은 이미 인라인 핀을 갖고 있었다). 착수 시 레인 파일이 준
시작점 목록에서 갈라진 곳:

- `e2e-authed-repro.sh` — **이미 고쳐져 있었다**(`:91`·`:102`·`:131` 이 `mise exec --`). 나머지 6줄은 주석·안내문.
- `docs-audit.sh` — 목록에 있었고 **실재했다**. 단 형태가 셸 호출이 아니라 python 히어독 안
  `shutil.which("node")` 라 셸 grep 으로는 안 잡힌다.
- `soak-watch.sh`·`soak-logs-follow.sh` — 도구 호출 **0건**이다(주석뿐). 면제 목록에는 남겨 뒀다.
- `worktree-bootstrap.sh` — 실호출은 4곳(`:339` `uv run alembic` · `:354`·`:356` `pnpm install` ·
  `:357` `uv sync`). 나머지는 안내문 히어독.

### AC-2 — 음성 대조 (이 항목의 핵심) ✅

가짜 도구 3종(`pnpm`·`uv`·`node`, 각각 `echo 8.15.9` 후 `exit 1`)을 임시 디렉터리에 두고
`PATH` **앞에** 붙인 뒤, 같은 게이트를 **수리 전 코드**와 **수리 후 코드**로 각각 돌렸다.

|            | 코드                   | 명령                                          | `CI frozen-lockfile` | 전체 rc |
| ---------- | ---------------------- | --------------------------------------------- | -------------------- | ------- |
| **대조군** | `origin/main`(핀 없음) | `--run ac2-control --pre-pr --allow-dirty`    | **FAIL**             | **1**   |
| **처리군** | 이 브랜치(핀 있음)     | `--run ac2-fake-tools --pre-pr --allow-dirty` | **PASS**             | **0**   |

대조군은 `git show origin/main:tools/scripts/final-gates.sh` 를 `tools/scripts/` 안에 임시로 두고
돌렸다 — `ROOT` 가 `dirname $0/../..` 라 같은 트리를 봐야 조건이 같다. 판정 후 삭제했다.

★**이 대조가 재는 축은 `pnpm` 하나다.** 이 브랜치의 diff 가 `apps/api` 를 건드리기 전이라
영역 판정이 `fe_diff=0 be_diff=0` 이었고, 그래서 `uv`·`node` 를 쓰는 게이트(BE ruff·mypy·
FE typecheck 등)는 두 실행 모두 `skip` 이었다. **`uv`·`node` 축은 이 대조로 증명되지 않았다** —
증명된 것은 [BL-785] 가 실제로 보고한 증상 그 자체(`CI frozen-lockfile`)다.
`uv` 축은 마감 게이트에서 별도로 확인했다(아래 §마감).

★전제 확인 — 내 셸의 PATH `pnpm` 은 원래 **9.12.0**(프로필이 shim 을 앞에 세운다)이다.
즉 「지금 내 셸에서는 괜찮다」가 성립하는 셸이었고, 그래서 가짜 도구를 **일부러 앞에 세우는**
이 조작이 없으면 이 항목은 아무것도 증명하지 못했다.

### AC-3 — 잔존 감시 ✅

`tools/scripts/tool-pin-audit.sh`(감사기) + `tools/scripts/tool-pin-audit-test.sh`(하네스 13케이스).
배선 3곳 — `final-gates.sh` 의 「도구 핀 감사」와 「도구 핀 감사 하네스」(영역 판정과 무관하게
항상 돈다), 그리고 `mise run gate-harnesses`(13종 → **14종**).

감사기가 가르는 축 — 「부르는가」와 「이름이 있는가」는 다르다:

| 잡는다                                        | 안 잡는다                       |
| --------------------------------------------- | ------------------------------- |
| 명령 위치 호출 (`cd x && pnpm test`)          | 주석 (`# pnpm test 를 돈다`)    |
| 래퍼 뒤 호출 (`timeout 120 uv run …`)         | 안내문 (`echo "… && pnpm e2e"`) |
| 인터프리터 히어독 안 (`shutil.which("node")`) | 사용법 히어독 본문              |
| 핀을 **언급만** 한 파일 (거짓 핀)             | `mise exec -- pnpm build`       |

감사기 자신의 fail-closed: 판정기가 훼손되면 rc=**3** 으로 죽는다(「판정 불가」를 「통과」로
번역하지 않는다). 하네스 케이스 ⑬ 이 그것을 잰다.

### AC-4 — 서버에서 도는 스크립트는 안 고쳤다 ✅

**6종. 한 줄도 안 고쳤다.** 감사기가 면제 사유와 함께 인쇄한다(`SERVER_SCRIPTS`).

| 스크립트              | 서버 경로 근거                                                | 도구 호출 |
| --------------------- | ------------------------------------------------------------- | --------- |
| `soak-gate.sh`        | `docs/status.md:107` — `ssh truewords-oracle 'bash -lc "…"'`  | 3         |
| `soak-stack.sh`       | `docs/reference/operations/ci-cd.md:254` — 「(SSH)」          | 3         |
| `soak-restart.sh`     | 서버 소크 재기동 8단계                                        | 2         |
| `soak-observe.sh`     | 서버 일일 원장 대조                                           | 1         |
| `soak-watch.sh`       | 서버 systemd user timer (`soak-watch.timer`, `status.md:360`) | 0         |
| `soak-logs-follow.sh` | 서버 systemd user unit (`gates-and-traps.md`)                 | 0         |

★근거는 헤더 주석이 아니라 **`docs/status.md` 와 `docs/reference/operations/`** 에 있었다.
레인 파일이 「`soak-*.sh` 헤더 주석이 적고 있다」고 했지만 헤더에는 없다.

★**확인하지 못한 것** — 서버에 mise 가 있는지. 접속 금지라 확인할 방법이 없었다. 그래서
「없을 수도 있으니 안 고친다」가 아니라 **「모르니 안 고친다」**가 이 결정의 정확한 근거다.

### AC-5 — 판정 기준이 문서로 확정됐다 ✅

`docs/reference/operations/gates-and-traps.md` §3 함정 → 환경, `test_migrations.py` 항목 바로 앞.
새 파일은 안 만들었다. 담은 것: 정본 = migration-only DB · 그 이유(migration 이 프로덕션 스키마를
만드는 유일한 경로) · [BL-770] 이 왜 다른 답을 냈는지의 실측 · 손으로 재는 절차 · **rc 는 1 이
아니라 255** 라는 것.

게이트와의 관계도 확정했다 — **정본 판정은 `CI fresh DB alembic` 축이다.** 그래서 그 게이트에
`alembic check` 를 붙였다. 문서만 쓰고 아무도 안 돌리면 죽은 기준이 된다(LESSON-078).

**CI 에도 붙였다** — `.github/workflows/ci.yml` `backend` 잡의 `alembic upgrade head` 바로 뒤.
그 잡의 `quantbridge_test` 는 서비스 컨테이너가 만들고 migration 이 유일한 스키마 생성 경로라
정의상 정본 DB 다. 로컬에만 붙이면 게이트 이름(「CI 전용 스텝 재현」)이 거짓이 되고, PR 이 실제로
막히는 자리에서는 이 판정이 안 돈다.
★**이 한 스텝은 CI 가 돌기 전까지 미검증이다.** 초록을 기대하는 근거는 셋이다 — CI 서비스
이미지가 로컬과 **같은** `timescale/timescaledb:2.14.2-pg15` 이고, migration 계보가 같으며,
같은 이미지의 migration-only DB 에서 내가 rc=0 을 실측했다. `ci.yml` 은 파싱 검증만 했다
(`yaml.safe_load` → `backend` 잡에 두 스텝이 순서대로 들어감).

### AC-6 — migration-only DB 에서 `alembic check` rc=0 ✅

```
DB=quantbridge_bl782_test (CREATE DATABASE 직후, alembic upgrade head 만 적용)
upgrade rc=0
check   rc=0          "No new upgrade operations detected."
```

파이프 없이 `rc=$?` 로 받았다. 게이트 본문(`CI fresh DB alembic`)을 그대로 떼어 돌린 것도
**rc=0** 이다(`quantbridge_ci_repro_test`).

downgrade 왕복도 확인했다 — `exchangename` → `character varying(32)` → `exchangename`,
세 단계 모두 rc=0 이고 `pg_attribute` 로 타입을 직접 읽어 확인했다.

### AC-7 — 음성 대조 (수리 전에는 red) ✅

같은 절차를 **수리 전 코드**에서 밟았다.

```
check rc=255
Detected type change from VARCHAR(length=32) to Enum('bybit','binance','okx', name='exchangename')
  on 'funding_rates.exchange'
FAILED: New upgrade operations detected:
  [('modify_type', 'trading', 'funding_rates', 'exchange', …, VARCHAR(length=32),
    Enum('bybit','binance','okx', name='exchangename'))]
```

사유가 정확히 `trading.funding_rates.exchange` 의 `modify_type` 이고, **그것 하나뿐**이다.

### AC-8 — 전량 BE pytest ✅

**`4759 passed, 32 skipped` · rc=0 · 421.50s** (fresh `quantbridge_w4_test`, `.env.local` 통째 소싱,
파이프 없이 `rc=$?`). 문턱 ≥4759 를 정확히 만족한다.

★**여기까지 세 번 돌렸고, 앞의 두 번은 red 였다.** 그 두 번이 이 회차에서 가장 값나간 부분이라 남긴다.

| 회차   | 조건                             | 결과                           | 정체                                |
| ------ | -------------------------------- | ------------------------------ | ----------------------------------- |
| ①      | 낡은 `quantbridge_w4_test`       | 대량 `E`                       | DB 잔존 상태(위 §반증 ⑷)            |
| ②      | fresh DB · 수리 전 conftest      | `2 failed, 4757 passed`        | `auth_*` 5테이블 미생성(위 §반증 ⑸) |
| ②-대조 | fresh DB · **내 migration 제외** | `2 failed, 4757 passed` (동일) | 내 것이 아님을 확정                 |
| ③      | fresh DB · conftest 수리         | **`4759 passed` rc=0**         | —                                   |

`ExchangeName` 을 쓰는 경로는 표적 테스트로 끝내지 않고 전량으로 봤다 — 그리고 실제로
표적 테스트가 못 본 것(②)이 전량에서 나왔다.

### AC-9 — 다른 drift 를 켜지 않았다 ✅

`apps/api/` diff = 파일 2개.

| 파일                                                  | 변경                                                                                                                            |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `alembic/versions/20260817_0002_…py`                  | 신규. DDL 문 **1개** — `ALTER TABLE trading.funding_rates ALTER COLUMN exchange TYPE exchangename USING exchange::exchangename` |
| `src/trading/repositories/funding_rate_repository.py` | **주석만**. 코드 무변경                                                                                                         |

`models.py` 는 **안 고쳤다** — 모델이 처음부터 옳았고 틀린 것은 migration 이었다.
diff 의 `+` 줄에 등장하는 컬럼은 `funding_rates.exchange`(2회, 본문+주석)와
`exchange_accounts.exchange`(1회, 문서 근거로 언급)뿐이다.

★**다음 회차로 넘길 drift 후보는 없다.** migration-only DB 의 `alembic check` 가 낸 항목이
이 한 컬럼뿐이었기 때문이다 — 「축을 하나씩 켜라」는 지시가 저절로 지켜졌다.

---

## 선택의 근거

**[BL-785] `mise exec --` 대신 PATH 핀을 골랐다.** 셋 다 실측으로 갈린다:

1. `mise exec --` 는 **`mise` 바이너리가 PATH 에 있어야** 한다. 그런데 이 병의 전형적 셸은
   「shim 은 설치돼 있는데 mise 가 활성화 안 된」 셸이다. shim 은 자기완결 바이너리라
   PATH 에 `mise` 가 없어도 돈다 — 실측: `PATH=shims:/usr/bin:/bin` 에서 `pnpm --version` = 9.12.0.
2. `final-gates.sh` 는 호출 지점이 17곳이고 대부분 `bash -c '…'` 문자열 안이다. 17곳을 고치면
   17곳이 다시 새는 표면이 된다. 진입부 2줄은 **자식 프로세스 전부**를 덮는다.
3. 파생 도구(`alembic`·`ruff`·`mypy`·`prettier`·`playwright` 를 부르는 `node`)까지 같이 덮인다.
4. `.husky/pre-commit`·`pre-push` 가 **이미 그 관용구**다 — 새로 발명하지 않았다.

**[BL-782] 모델을 낮추지 않고 migration 을 올렸다.** 근거:

1. `ExchangeName` 을 쓰는 컬럼은 둘인데(`exchange_accounts.exchange`·`funding_rates.exchange`)
   **앞의 것은 이미 native enum** 이다(`20260416_2206:117`). 모델을 `str` 로 낮추면 같은 개념의
   두 컬럼이 서로 다른 타입이 된다.
2. 값 안전을 먼저 셌다 — 개발 DB `trading.funding_rates` **162행 전건 `bybit`**, `exchangename`
   라벨은 `bybit`·`binance`·`okx`. 인제스션 경로(`src/trading/funding.py`)도 `ExchangeName` 로
   타입이 잡혀 있어 그 밖의 값이 들어갈 자리가 없다.
3. enum value 를 더하거나 빼지 않으므로 [LESSON-066] 의 downgrade enum swap 패턴은 대상이 아니다.

---

## 표적 변이

심을 때와 다른 방법(sha256 대조)으로 복원을 확인했다. `git checkout <file>` 은 쓰지 않았다.

| #   | 변이                                           | 기대                 | 실측                                                       | 복원          |
| --- | ---------------------------------------------- | -------------------- | ---------------------------------------------------------- | ------------- |
| M1  | `docs-audit.sh` 의 핀 2줄 제거 (한 스크립트만) | AC-3 잔존 검사가 red | **rc=1** · `docs-audit.sh:269 [node]` 로 지목              | sha256 일치 ✓ |
| M2  | `20260817_0002` 의 `upgrade()` 를 `pass` 로    | AC-6 이 rc≠0         | **rc=255** · 사유 = `modify_type … funding_rates.exchange` | sha256 일치 ✓ |
| M3  | 감사기 자신에 `pnpm --version` 삽입            | 감사기가 red         | **rc=1** · `tool-pin-audit.sh:46 [pnpm]` 로 지목           | sha256 일치 ✓ |

★M3 은 **처음엔 통과했다.** 감사기가 자기 파일을 통째로 면제하고 있었기 때문이다(자기 판정 목록
`TOOLS = ("pnpm", "uv", …)` 가 인터프리터 히어독 축에 잡혀서). 면제를 **축 단위**로 좁혀서
(`"interp"` = 히어독 축만 끔 / `"all"` = 파일 전체) 셸 명령 위치 축은 자기 자신에게도 살아 있게 했다.
하네스는 `"all"` 이다 — fixture 본문이 셸 스니펫 그 자체라 가릴 방법이 없다.

---

## 확인하지 못한 것

1. **서버(`truewords-oracle`)의 mise 존재 여부.** 접속 금지. `soak-*.sh` 6종을 안 고친 근거가
   이것이므로, 서버에 mise 가 있다면 그 6종도 같은 핀으로 묶을 수 있다 — 다음 회차 판단거리다.
2. **서버 소크 DB 의 `funding_rates.exchange` 값 집합.** 확인 불가. 라벨 밖 값이 있으면
   migration 의 `USING` 캐스트가 `invalid input value for enum exchangename` 으로 **소리 내며**
   실패한다(조용히 틀린 결과를 내지는 않는다). 서버 적용 전에 값을 먼저 세라.
3. **`uv`·`node` 축의 AC-2 음성 대조**(§AC-2 의 ★ 참조). 증명된 것은 `pnpm` 축이다.
4. **CI 러너에서의 핀 동작.** CI 에는 mise 가 없을 수 있고, 그때 `qb_pin_tool_path` 는 경고 한 줄을
   stderr 로 내고 종전대로 PATH 를 쓴다(fail-open). 이것이 옳은 선택인지는 CI 에서 실행해 봐야 안다 —
   push 후 CI 로그의 `⚠ mise shim 디렉터리가 없다` 유무로 확인해라.
5. **신호 게이트 4종**(`codex.ok`·`g9.ok`·`screen.ok`·`vercel.ok`) — 계약대로 안 만들었다.

---

## 마감

`.claude/gates/gate-pins/` — 결과는 아래 §마감 결과.
