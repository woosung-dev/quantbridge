# phases/ — 하네스 러너의 회차 정의

각 디렉터리 = phase 1개 = **브랜치 1개 = PR 1개**. 안의 step 은 **순차**로 돈다
(`step0` → `step1` → …, 앞 step 의 `summary` 가 다음 step 프롬프트에 누적된다).

★**`index.json` 은 순서가 아니라 목록이다.** 항목 사이에 의존이 없으면 서로 다른 워크트리에서
**동시에** 돌 수 있다. 러너(`tools/harness/execute.py`)는 인자로 받은 phase **하나만** 처리하므로,
병렬은 러너 안이 아니라 **밖 — 프로세스를 N벌 띄우는 것 — 에서 만들어진다.**
(출처 레포 jha0313/finsight 에서는 `0-foundation` → `1-core-loop` → … 처럼 **순번**이었다.
우리는 같은 파일을 병렬 묶음에도 쓴다. 어느 쪽인지는 아래 절이 말한다.)

## 지금 열려 있는 병렬 묶음 — `ops2-*` 8벌 (2026-08-21)

[ADR-037] §① 이 「검사기 복귀 시 함께 복귀」라 적어 둔 자기시험 `*-test.sh` **14종** 중
**대상 스크립트가 아직 살아 있는 7종**의 잔여(4벌) + **짝 하네스가 애초에 없던 인접 4종**이다.
소유 티켓 = **[BL-812]**. **여덟은 동시에 돌도록 설계됐다.**

| phase                   | 대상                                    | 새 테스트 파일 (`apps/api/tests/scripts/`) | 짊어진 이슈                     |
| ----------------------- | --------------------------------------- | ------------------------------------------ | ------------------------------- |
| `ops2-prepush-guard`    | `lib/pre-push-ref-guard.sh` 판정 순서   | `test_pre_push_ref_guard.py`               | Golden Rule · [BL-554]·[BL-555] |
| `ops2-notify-telegram`  | `lib/notify-telegram.sh` seam·토큰 침묵 | `test_notify_telegram_lib.py`              | [BL-768]                        |
| `ops2-mise-shim`        | `lib/mise-shim-path.sh` PATH 계산       | `test_mise_shim_path.py`                   | [BL-785] · [BL-791] gap 고정    |
| `ops2-soak-watch`       | `soak-watch.sh` 지문·신선도             | `test_soak_watch.py`                       | [BL-737]                        |
| `ops2-soak-restart`     | `soak-restart.sh` `ps` rc 3값           | `test_soak_restart.py`                     | [BL-656]                        |
| `ops2-stack-migrate`    | `soak-stack.sh` `_migrate` 대상 증명    | `test_soak_stack_migrate.py`               | [BL-743]                        |
| `ops2-db-backup-retain` | `db-backup.sh` `--status`·`_retain`     | `test_db_backup_retain.py`                 | [BL-767]                        |
| `ops2-logs-follow`      | `soak-logs-follow.sh` 회전·커서         | `test_soak_logs_follow.py`                 | [BL-619]                        |

동시에 돌 수 있는 근거는 **파일 겹침 0** 이다 — 각 lane 은 자기 테스트 파일 하나만 만들고
대상 스크립트·`conftest.py`·`shards.json` 을 건드리지 않는다(각 step 의 금지사항에 박혀 있다).
공용 헬퍼 모듈도 금지다 — 그것이 lane 사이의 유일한 공유 파일이 되기 때문이다.

★**대상을 tmp 로 돌리는 방식이 lane 마다 다르다.** 진짜 파일을 그대로 부르는 넷
(`lib/` 3종은 **source 전용**이라 `bash -c '. lib; fn'` · `db-backup` 은 env)과, 경로가
`SCRIPT_DIR`/`ROOT` 파생이라 못 바꾸는 넷(`soak-watch`·`soak-restart`·`soak-stack`·
`soak-logs-follow`)은 **`tmp_path` 아래 가짜 레포에 복사해서** 돈다. 진짜 경로를 겨누면
이 레포의 소크 앵커·커서·백업 디렉터리를 덮어쓴다.

★**외부 명령만 PATH 스텁**(`docker`·`oci`·`uv`·`timeout`) — `awk`/`sed`/`grep` 은 대상이
쓰는 것이라 스텁하면 대상을 안 재게 된다.

### 앞선 묶음 (완주)

`ops-*` 6벌 (2026-08-20 · PR #703~#709) — 운영 스크립트 6종의 판정 로직 **0건 → 72 passed +
1 xfailed**. `runner-*` 4벌 (2026-08-20 · PR #698~#702) — 러너 자신(`tools/harness/execute.py`)의
테스트 0건을 `apps/api/tests/harness/test_execute_{ac,retry,commit,boot}.py` **41건**으로 채웠다.

## 밤샘 루프 — 배치를 이어 돌릴 때 (2026-08-20 설계)

러너는 phase 하나만 처리한다. 여러 배치를 밤새 이어 돌리는 것은 **러너 밖 셸 루프**다.
★**저작이 상한이다** — 밤에 도는 분량은 저녁에 저작해 둔 분량뿐이고, 그래서 재료는
**동형(同型)**이어야 한다(같은 대상 종류 × 같은 종류의 일). 이질적인 티켓 N건은 저작이 안 된다.

배치 루프가 하는 일 — 2026-08-20 6 lane 회차에서 **손으로 한 순서 그대로**다:

1. `phases/index.json` 의 `pending` 에서 cap N 개를 꺼낸다 (**웨이브를 저작하지 마라** —
   배치는 동시 실행 상한 + 체크포인트일 뿐이다)
2. lane 마다 워크트리 생성 + `worktree-bootstrap.sh --adopt-env --skip-deps` + `apps/api` `uv sync`
3. ★**착수 전 AC red 확인** — rc=0 인 lane 은 **판별력이 0** 이므로 큐에서 빼고 기록한다
4. 러너 N벌 `nohup` 병렬 → `wait` (대화 세션 타임아웃이 러너를 죽인다)
5. ★**변이 red 확인** — red 가 아니면 PR 을 올리지 말고 `unverified` 로 기록한다
   (2026-08-20 에 이 축이 「옳은 단언 + 잘못된 픽스처」 1건을 잡았다)
6. `--push` + `gh pr create` → **CI 가 밤새 대신 돈다.** 아침에 결과가 이미 있다
7. ★`git worktree remove` 로 **슬롯을 회수**한다 — 슬롯은 1..12 뿐이라 회수 없이는 3배치째에 막힌다
8. 시간 상한이 남았으면 1로

★**자동 머지는 하지 않는다.** 「마지막 강력 검증」(사람 diff + 머지)은 아침의 몫이다.
★`blocked` 는 즉시 알린다(자격증명 등 사람만 풀 수 있는 것) — 나머지는 아침에 몰아 본다.
★**화면은 pane 2개면 된다** — 상태 보드 + `dispatch.log`. lane 당 `tail -f` 6벌은 새벽에 못 읽는다.
`herdr pane split --current --direction right --ratio 0.3` · `herdr pane run <ID> <cmd>` ·
`herdr notification show <제목> --sound done`. ★워크트리는 `herdr worktree create` 가 아니라
`worktree-bootstrap.sh` 로 만든다 — herdr 은 슬롯·env·테스트DB 를 모르고, 워크트리마다 탭이
생겨 [ADR-030] 이 걷어낸 함대 모델로 돌아간다.

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
