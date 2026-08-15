# harness — 무인 순차 step 러너 (as-is 재도입, 2026-08-15)

> **상태:** 재도입 (사용자 판정 2026-08-15) · **정본 = [ADR-033](../docs/decisions/033-harness-readopt-codex.md)**
> **출처:** <https://github.com/jha0313/harness_framework> @ `da676bc6` (2026-04-14 이후 상류 커밋 0)
> **선행:** [ADR-030](../docs/decisions/030-harness-pilot-verdict.md) — 이 프레임워크를 2회 돌리고
> 2026-08-13 에 걷어낸 기록. **먼저 읽어라.** 여기 적힌 위험은 전부 거기서 실측된 것이다.

---

## 0. 한 줄 요약

**오케스트레이터를 LLM 에서 스크립트로 내린다.** `codex exec` 를 step 마다 새 프로세스로 띄우고,
부모 컨텍스트가 없으며, 유일한 보고 채널이 `.harness/phases/<task>/index.json` 이다.

## 1. 계층 — 대체재가 아니라 층이다

| 층                        | 담당               | 무엇을 준다                                            |
| ------------------------- | ------------------ | ------------------------------------------------------ |
| **CONTROL** (Claude 세션) | 판정               | 수용 기준 동결 · 변이 · 게이트 · 문서 · PR             |
| **워크트리**              | 격리               | 브랜치 1개로 블라스트 반경을 묶는다                    |
| **harness** (이 디렉터리) | 실행 · 상태 · 무인 | ★**독립 검증은 없다** — 세션이 자기 status 를 써넣는다 |

★**「러너가 completed 라고 했다」는 검증이 아니다.** AC 재실행은 CONTROL 몫이다
(`docs/reference/operations/workflows/generator-evaluator-pipeline.md` §1 — 생성자는 게이트 판정·문서·머지 금지).

## 2. 실행

```bash
# ★preflight 2개 — 건너뛰지 마라 (아래 위험 1·2·5 가 여기서 막힌다)
git status --porcelain            # 반드시 빈 출력
git rev-parse --abbrev-ref HEAD   # 지금 어느 브랜치인지 눈으로 확인

python3 tools/scripts/execute.py <task-name>
```

- ★**워크트리에서만 돌려라.** `--dangerously-bypass-approvals-and-sandbox` 는
  `.claude/settings.json` 의 **deny 10종**(`rm -rf*`·`git reset --hard*`·`git push --force*`·
  `docker volume rm*`·`sudo*` …)을 통째로 우회한다. 코드가 메인 실행을 막지 않는다 — 사람이 지켜야 한다.
- ★**`--push` 금지.** Golden Rule(사용자 승인 없는 push). 플래그는 원본 그대로 남겨 뒀다.
  A/B 파일럿이 원격 유출을 면한 것이 이것 하나 덕이었다(위험 3·7).
- ★**celery 경유 검증을 step 에 넣지 마라** — worker 컨테이너가 **메인의 `apps/api/src`** 를 mount 한다.
- ★**게이트를 step 에 넣지 마라** — 아래 §5 참조.

에러 복구: `index.json` 의 해당 step `status` 를 `"pending"` 으로 되돌리고
`error_message`/`blocked_reason` 을 지운 뒤 재실행. ★단 **위험 7**(아래)을 먼저 읽어라.

## 3. 디렉터리

```
.harness/
├── README.md
├── docs/                        # 가드레일 4축 — ★심링크다. 사본 만들지 마라(SSOT)
│   ├── 01-domain.md    -> ../../CONTEXT.md
│   ├── 02-structure.md -> ../../AGENTS.md
│   ├── 03-backend.md   -> ../../apps/api/AGENTS.md
│   └── 04-frontend.md  -> ../../apps/web/AGENTS.md
└── phases/
    ├── index.json               # 전체 현황 (task 목록)
    └── <task>/
        ├── index.json           # step 목록 + 상태 원장  ← 유일한 보고 채널
        ├── step{N}.md           # 입력 (CONTROL 이 쓴다)
        └── step{N}-output.json  # 산출물 (gitignore — codex 는 트랜스크립트를 통째로 싣는다)
```

**왜 `docs/` 가 아니라 이 4축인가** — 원본 `_load_guardrails()` 는 `docs/*.md` 를 필터 없이 넣는다.
그건 게으름이 아니라 계약이다: 원본 `docs/`(PRD·ARCHITECTURE·ADR·UI_GUIDE)에는 **정적 설계 제약만** 있다.
우리 `docs/` 최상위는 정확히 반대다 — glob 이 잡는 것은 `status`·`backlog`·`roadmap`·`lessons`
(**2026-08-15 재측정 768,152자**)뿐이고, 정본인 `docs/reference/`·`docs/decisions/` 는 하위라 **0건**이다.
크기가 아니라 **선택**의 문제다. 4축 = **45,820자 (−94.0%)**. 근거 = ADR-030 §발견①.

## 4. ★as-is 로 안고 가는 위험 11건 — 첫 run 전에 읽어라

전부 **원본 그대로의 성질**이지 우리 수정이 만든 결함이 아니다. 고치지 않는 이유 = as-is 채택이
2026-08-15 사용자 판정의 조건이기 때문이다(ADR-033). 원문 = `git show c3a39d0d:harness/README.md` §3.1.

| #   | 위험                                                                                                                                                                                  | 등급   |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| 1   | `_checkout_branch` 에 **clean-tree 검사가 0건**. dirty tree 를 새 브랜치로 데려가고 `git add -A` 가 그것까지 커밋한다                                                                 | **P1** |
| 2   | 실패 경로에서도 `_commit_step()` 을 부른다 — 3회 실패한 step 의 부산물이 커밋된다                                                                                                     | **P1** |
| 3   | `_finalize` 가 **커밋 실패를 무시**하고 "Phase completed!" 를 찍는다                                                                                                                  | **P1** |
| 4   | 권한 bypass 를 쓰면서 **워크트리를 강제하지 않는다**. §2 는 권고일 뿐 코드가 메인 실행을 막지 않는다                                                                                  | **P1** |
| 5   | `_check_blockers` 가 **checkout 보다 먼저** 돈다 — 현재 브랜치 기준으로 판정한 뒤 브랜치를 바꾼다                                                                                     | P2     |
| 6   | `core.symlinks=false` / dangling 심링크면 조용히 링크 문자열이 되거나 `FileNotFoundError`                                                                                             | P2     |
| 7   | ★`subprocess.run(timeout=1800)` 이 **`TimeoutExpired` 를 안 잡는다.** 상한을 넘기면 phase 전체가 traceback 으로 죽고, 그 step 의 자기신고는 **검증되지 않은 채 커밋된 상태로 남는다** | **P1** |
| 8   | `info.elapsed` 를 `with` 블록 **안에서** 읽어 `✓ Step N [0s]` 가 **항상 0초**                                                                                                         | P3     |
| 9   | **non-zero exit code 가 완료를 막지 못한다.** `exitCode` 는 output json 에 실릴 뿐 `_execute_single_step` 이 한 번도 읽지 않는다                                                      | **P1** |
| 10  | (B회차 개조분) `ac` 필드가 없으면 fail-open — **이번 재도입판에는 `ac` 자체가 없다**(순수 as-is)                                                                                      | —      |
| 11  | AC 가 **세션이 변조했을 수도 있는 대상**을 그대로 실행한다 (clean snapshot·해시·allowlist 없음)                                                                                       | **P1** |

★★**7번의 최악 갈래는 재실행이다** — 상한 초과로 러너가 죽어도 세션이 이미 써 둔 `completed` 는
파일에 남는다. **다시 돌리면 그 step 은 `pending` 이 아니라서 건너뛴 채 phase 가 닫힌다.**
B회차 step 1 이 정확히 그렇게 통과했고 그 사이 러너는 **AC 를 0건 실행**했다.
⇒ **러너가 traceback 으로 죽으면 `index.json` 을 먼저 눈으로 봐라.** 재실행이 먼저가 아니다.

★**범위 이탈은 모델로 안 막힌다** — ADR-030 §④ 실측: `claude` **6/6** 범위 준수 vs `codex` **2/2**
게이트에 손댐. 1회는 `final-gates` 를 스스로 3번 돌려 **66분 33초**를 태웠다(우리 `AGENTS.md` 의
「게이트는 마지막 커밋 뒤에」를 **세션 단위로 오독**). ⇒ step 파일 「금지사항」에 박아야 한다.

## 5. step 파일 작성 규약

`.claude/commands/harness.md` 대신 이 절이 정본이다. 상류 §C 설계 원칙 7개를 그대로 쓰되,
이 레포에서 반드시 추가할 「금지사항」 4줄:

```markdown
## 금지사항

- `tools/scripts/final-gates.sh` 를 실행하지 마라. 이유: 게이트는 **회차 단위**이고 사람이 돌린다.
  세션 단위로 오독해 66분을 태운 실측이 있다 (ADR-030 §발견②).
- `docs/**` 를 만지지 마라. 이유: `backlog.md` 단일 파일 9천 줄이라 충돌한다.
- celery 경유 검증(백테스트·라이브신호·옵티마이저)을 하지 마라. 이유: worker 가 **메인의 `apps/api/src`**
  를 mount 하므로 내 코드가 아니라 메인 코드가 돈다 — 침묵 실패다.
- `make up`/`down`/`migrate`/`seed` 를 하지 마라. 이유: 앱 DB 는 1벌 공유다.
```

**AC 규약 2개** (ADR-030 부수 절):

1. **AC 는 착수 전에 red/green 양쪽을 실측해라.** 파일럿에서 헛초록 4건이 착수 전 스모크에 걸렸다 —
   판정 없이 `wc -l` 로 찍기만 함 · 기준을 `main` 으로 잡아 후속 step 의 정당한 변경까지 위반으로 셈 ·
   `grep -q 'searchParams'` 가 **결함을 설명하는 주석** 때문에 이미 rc=0 · 무관한 동명 상수.
2. **AC 를 시점 독립으로 짜라.** 「이 회차가 아직 X 를 안 건드렸다」는 뒤 step 이 X 를 정당하게 고치면
   영원히 red 다 — 사후 재실행이 불가능해진다.

## 6. 우리 수정 5곳 (상류 대비)

`tools/scripts/execute.py` — 나머지는 `da676bc6` 그대로다.

| #   | 위치               | 무엇                                                                                                                                                      | 왜 「as-is 라 안 건드린다」가 성립 안 하나                                                                               |
| --- | ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| ①   | `_invoke_claude`   | `claude -p --dangerously-skip-permissions --output-format json` → `codex exec --dangerously-bypass-approvals-and-sandbox -C <root>` + **`stdin=DEVNULL`** | 사용자 요청. ★`-p` 는 옮기면 안 된다(codex 에서 `--profile`). ★`stdin` 미지정이면 codex 가 **무한 대기**한다             |
| ②-1 | `__init__`         | `phases/` → `.harness/phases/`                                                                                                                            | 루트 오염 회피                                                                                                           |
| ②-2 | `_load_guardrails` | `docs/` → `.harness/docs/`                                                                                                                                | §3 참조 (768,152자 → 45,820자)                                                                                           |
| ②-3 | 모듈 상수          | `ROOT = parent.parent` → `parent.parent.parent`                                                                                                           | ★상류는 `scripts/` 가 루트 직하. 우리는 [ADR-029] 로 `tools/scripts/` 라 한 단 깊다. **안 고치면 가드레일이 조용히 0자** |
| ②-4 | `_commit_step`     | reset 경로 `phases/…` → `.harness/phases/…`                                                                                                               | ★②-1 의 딸림. 안 고치면 `git reset` 이 조용히 실패해 **2단 커밋 분리가 붕괴**한다                                        |

`tools/scripts/test_execute.py` — 상류 51건 + **우리 AC 4건**:
`TestRootResolution` 3건(②-3) · `test_reset_paths_match_phases_dir`(②-4) · `TestInvokeClaude` 강화(①).

```bash
uv run --no-project --with pytest pytest tools/scripts/test_execute.py -q     # 55 passed
```

★`apps/api` 안에서 돌리지 마라 — 세션 픽스처 `drop_all` 이 **개발 DB 를 겨냥**한다.

★★**「55 passed」를 러너 검증으로 읽지 마라.** 상류 51건은 **12개 클래스 전부 헬퍼 단위**이고
`run()`·`_execute_single_step`·`_execute_all_steps`·`_finalize` 가 테스트에 **각 0회** 등장한다.
`run()` 을 no-op 으로 바꿔도 51건은 대부분 초록이다(ADR-030 §발견⑤). 우리 4건이 덮는 것은
②-3/②-4/① **그 세 곳뿐**이고, 그것도 변이 M1~M4 로 도달을 확인했기 때문에 하는 말이다.
