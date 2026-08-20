# phases/ — 하네스 러너의 회차 정의

각 디렉터리 = phase 1개 = **브랜치 1개 = PR 1개**. 안의 step 은 **순차**로 돈다
(`step0` → `step1` → …, 앞 step 의 `summary` 가 다음 step 프롬프트에 누적된다).

★**`index.json` 은 순서가 아니라 목록이다.** 항목 사이에 의존이 없으면 서로 다른 워크트리에서
**동시에** 돌 수 있다. 러너(`tools/harness/execute.py`)는 인자로 받은 phase **하나만** 처리하므로,
병렬은 러너 안이 아니라 **밖 — 프로세스를 N벌 띄우는 것 — 에서 만들어진다.**
(출처 레포 jha0313/finsight 에서는 `0-foundation` → `1-core-loop` → … 처럼 **순번**이었다.
우리는 같은 파일을 병렬 묶음에도 쓴다. 어느 쪽인지는 아래 절이 말한다.)

## 지금 열려 있는 병렬 묶음 — `ops-*` 6벌 (2026-08-20)

`tools/scripts/` 의 **운영 스크립트 판정 로직**을 6축으로 가른 것이다. **여섯은 동시에 돌도록 설계됐다.**

| phase               | 대상 (`tools/scripts/`)            | 새 테스트 파일 (`apps/api/tests/scripts/`) |
| ------------------- | ---------------------------------- | ------------------------------------------ |
| `ops-ledger-vitals` | `ledger-vitals.sh` 3축 판정        | `test_ledger_vitals.py`                    |
| `ops-disk-guard`    | `disk-guard.sh` 임계·전이 발화     | `test_disk_guard.py`                       |
| `ops-db-backup`     | `db-backup.sh` 인자·대상 증명      | `test_db_backup_target.py`                 |
| `ops-openapi-poc`   | `openapi-poc-filter.py` 폐포·drift | `test_openapi_poc_filter.py`               |
| `ops-soak-observe`  | `soak-observe.sh` fail-closed·차분 | `test_soak_observe.py`                     |
| `ops-main-checkout` | `assert-main-checkout.sh` 워크트리 | `test_assert_main_checkout.py`             |

동시에 돌 수 있는 근거는 **파일 겹침 0** 이다 — 각 lane 은 자기 테스트 파일 하나만 만들고
대상 스크립트·`conftest.py`·`shards.json` 을 건드리지 않는다(각 step 의 금지사항에 박혀 있다).
공용 헬퍼 모듈도 금지다 — 그것이 lane 사이의 유일한 공유 파일이 되기 때문이다.

★**대상을 tmp 로 돌리는 방식이 lane 마다 다르다.** 환경변수로 대상을 바꿀 수 있는 넷
(`ledger-vitals` 는 argv 플래그 · `disk-guard`·`db-backup` 은 env · `assert-main-checkout` 은
cwd)은 **진짜 파일을 그대로 호출**하고, 못 바꾸는 둘(`soak-observe.sh` 의
`STATE_DIR=${REPO_ROOT}/.soak` · `openapi-poc-filter.py` 의 `SOURCE`/`OUTPUT`)은
**`tmp_path` 아래 가짜 레포에 복사해서** 돈다. 진짜 경로를 겨누면 이 레포의 소크 앵커나
커밋된 OpenAPI 산출물을 덮어쓴다.

### 앞선 묶음 (완주)

`runner-*` 4벌 (2026-08-20 · PR #698~#702) — 러너 자신(`tools/harness/execute.py`)의 테스트
0건을 `apps/api/tests/harness/test_execute_{ac,retry,commit,boot}.py` **41건**으로 채웠다.

## 이 저장소의 바인딩

`/harness` 커맨드는 프로젝트에 무관하게 쓰이도록 되어 있다. 이 저장소에서 그 자리에 들어가는 값은 아래다.

| 축             | 값                                                                                                                |
| -------------- | ----------------------------------------------------------------------------------------------------------------- |
| 러너           | `tools/harness/execute.py`                                                                                        |
| BE 테스트 AC   | `cd apps/api && uv run --env-file .env.local pytest <대상> -q`                                                    |
| BE 린터 AC     | `cd apps/api && uv run ruff check <대상>`                                                                         |
| FE AC          | `cd apps/web && pnpm test -- --run <대상>` · `pnpm tsc --noEmit` · `pnpm build`                                   |
| 브랜치 규약    | `feat/harness-<phase>` — `feat/` 접두는 push 가드 화이트리스트라 협상 불가                                        |
| 규칙 주입 파일 | `CONTEXT.md` · `AGENTS.md` · `apps/api/AGENTS.md` · `apps/web/AGENTS.md` (하나라도 없으면 러너가 시작을 거부한다) |
| 워크트리 준비  | `git worktree add <경로> -b feat/harness-<phase>` → 그 안에서 `tools/scripts/worktree-bootstrap.sh --adopt-env`   |
| 타임아웃       | `QB_HARNESS_CODEX_TIMEOUT` · `QB_HARNESS_AC_TIMEOUT`                                                              |

**AC 에 넣으면 안 되는 것** — 이 저장소의 구조적 제약이다:

- **서버 기동을 요구하는 검증** — 포트가 lane 사이에서 충돌한다
- **celery 경유 검증** — worker 컨테이너가 메인 체크아웃의 소스를 mount 하므로 워크트리에서는
  **내 코드가 아니라 메인 코드가 돈다**(침묵 실패)
- **`mise run up|down|migrate|seed`** — 컨테이너와 앱 DB 는 1벌 공유라 함께 깨진다
- **환경 변수 통째 소싱 없는 pytest** — DB 가드가 거부한다(rc=3)
- **BE 전량 pytest** — lane 수만큼 곱해진다. 광역 회귀는 CI 와 사람의 통합 검수가 본다

**러너가 도는 동안** 같은 체크아웃에서 다른 세션이 작업하면 안 된다(공유 작업 트리).

## 실행

```bash
python3 tools/harness/execute.py <phase-dir> [--push]     # 순차 — phase 하나
```

병렬은 워크트리마다 위 명령을 `nohup … &` 로 띄우고 각 `phases/<dir>/index.json` 을 폴링한다.
★띄우는 셸의 PATH 에 `uv` 가 있어야 한다 — 러너는 AC 를 **비로그인 `bash -c`** 로 돌린다.
★워크트리에는 `.venv` 가 따로 필요하다 — `tools/scripts/worktree-bootstrap.sh --adopt-env`.

저작 규약(step 파일 형식 · AC 규약 §C-5a~5e)의 정본 = `.claude/commands/harness.md`.
산출물(`runs/`)은 `.gitignore` 가 막는다.
