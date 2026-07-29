# 함대 오케스트레이션 — 워커에 일을 던지고, 합치고, 검증하기

> 화면을 띄우는 방법은 [`reference/worktree-parallel.md`](../reference/worktree-parallel.md) §2.3.
> **이 문서는 띄운 다음에 무엇을 어떻게 시키는가**를 규정한다.
>
> 프로토콜은 새로 만들지 않았다. [ADR-015](../decisions/015-sprint-7d-okx-sessions.md)(signal IPC) ·
> [ADR-017](../decisions/017-fe-polish-bundle-1-2-retro.md)(stage 경유) · `autonomous-parallel-sprints`
> 스킬(worker-prompt · blocker-playbook · merge-strategies)이 정본이고, **여기는 herdr 어댑터**다.

---

## 1. 역할 — 누가 무엇을 하는가

|      | 오케스트레이터 (CONTROL, 슬롯 0)                           | 워커 (워크트리, 슬롯 N)            |
| ---- | ---------------------------------------------------------- | ---------------------------------- |
| 산출 | 수용 기준 · 작업 분배 · 통합 · 게이트 · PR                 | **구현 diff + 커밋**               |
| 금지 | 구현 diff 작성                                             | 머지 · 푸시 · PR · 사용자에게 질문 |
| 검증 | 통합 브랜치에서 **전체 게이트 재실행** · celery 경유 · e2e | 자기 워크트리에서 가능한 것만 (§3) |

★**수용 기준은 착수 *전에* 오케스트레이터가 동결한다.** 워커가 자기 테스트를 쓰면 그 테스트는 자기
구현의 거울이 된다 — 이 레포가 반복해서 밟은 함정이다
([generator-evaluator-pipeline.md](generator-evaluator-pipeline.md) §G1). 함대에서는 그 G1 이
**task 파일**이고, 거기에 표적 변이와 음성 대조까지 적는다.

★**워커의 "다 됐고 게이트 통과했다" 는 보고이지 증거가 아니다.** 오케스트레이터가 통합 브랜치에서
다시 잰다. 이 재측정이 Generator/Evaluator 분리를 절차가 아니라 **구조**로 만든다.

---

## 2. 디렉터리 계약

```
.claude/fleet/<run>/          # gitignore (.claude/* 규칙)
├─ tasks/<worker>.md          # 오케스트레이터가 쓴다 — 무엇을·수용기준·금지경로
├─ signals/<worker>.status    # 워커가 쓴다 — running | done | blocked
└─ reports/<worker>.md        # 워커가 쓴다 — 커밋 SHA · 만진 파일 · 자기 게이트 결과 · 막힌 것
```

워커 이름 = 워크트리 이름 = `herdr-fleet.sh --agent <kind>:<이름>` 의 그 이름. 브랜치는 `wt/<이름>`.

**상태는 두 곳에서 온다.** herdr 의 `agent_status`(`working`/`idle`/`blocked`)는 **프로세스**가 살아
있는지, `signals/*.status` 는 **일**이 어디까지 갔는지를 말한다. 둘은 다르다 —
`agent_status=blocked` 는 대개 권한 프롬프트에 걸린 것이고, 그건 워커가 스스로 못 푼다.

---

## 3. 작업 라우팅 — 무엇을 워커에 줄 수 있나

★**워커는 celery 를 타는 검증을 못 한다**(`reference/worktree-parallel.md` §3). 이게 분배를 가른다.

| 작업 성격                                    | 워커에 줘도 되나       | 검증 주체                                           |
| -------------------------------------------- | ---------------------- | --------------------------------------------------- |
| FE 컴포넌트 · 훅 · 문서 · 순수 함수 · 스키마 | ✅ 자기 완결           | 워커 (`pnpm test` · `pytest`)                       |
| API 핸들러 · Repository · 서비스 계층        | ✅ 코드·단위테스트까지 | 워커 + 오케스트레이터 재측정                        |
| **백테스트 · 라이브신호 · 옵티마이저 로직**  | △ **코드만**           | ★**오케스트레이터 전용** (CONTROL 에서 celery 경유) |
| 마이그레이션 · 시드 · 컨테이너               | ❌                     | 오케스트레이터 (가드가 워커에서 거부한다)           |

**스코프는 disjoint 여야 한다.** 두 워커가 같은 파일을 만지면 통합에서 터지고, 그걸 되돌리는 비용이
병렬로 번 시간을 넘는다. task 파일에 **건드리면 안 되는 경로**를 명시한다.

---

## 4. 절차

```
① 분해     오케스트레이터가 BL/스프린트를 읽고 A/B/C 로 쪼갠다 → tasks/*.md
   ★정지점 1 — 분배안을 사람에게 보이고 승인받는다 (가장 싼 수정 지점)
② 부팅     scripts/herdr-fleet.sh --agent claude:a --agent claude:b --agent codex:c
③ 분배     scripts/fleet-dispatch.sh --run <run>
④ 폴링     scripts/fleet-dispatch.sh --run <run> --status     (반복 호출)
⑤ 통합     stage/<theme> 에 워커별 순차 squash merge (§5)
⑥ 검증     통합 브랜치에서 전체 게이트 + celery 경유 + e2e
   ★정지점 2 — PR 생성 전 사람 승인
⑦ 정리     herdr-fleet.sh --teardown · 워크트리·브랜치·슬롯 DB 제거
```

정지점은 **① 착수 전**과 **⑥ PR 전** 둘뿐이다(사용자 결정 2026-07-29). ⑤ 통합과 ⑥ 게이트는 자동으로
진행하고, 깨지면 그때 보고한다.

---

## 5. 통합 — Option C (`stage/<theme>`)

ADR-017 이 정한 이 레포 기본값. **main 을 자동으로 건드리지 않고**, `gh pr merge` 도 쓰지 않는다.

```bash
git switch -c stage/<theme> origin/main        # 통합 지점
for w in a b c; do
  git merge --squash "wt/$w"                   # ★순차. 동시 머지 금지 (race)
  git commit -m "feat(<scope>): <워커 산출 요약> (worker $w)"
done
```

충돌이 나면 **오케스트레이터가 손으로 풀지 않는다** — 어느 워커·어느 파일인지 확인하고 그 워커에
재지시한다. 오케스트레이터가 풀면 그 해결을 아무도 검증하지 않는다.

머지 후 **통합 브랜치에서 게이트를 처음부터 다시** 돌린다. 워커별 green 의 합은 통합 green 이 아니다 —
A 와 B 가 각각 맞는데 합치면 깨지는 상호작용 결함이 정확히 이 자리에서 나온다.

---

## 6. 워커 프롬프트 (분배 시 주입되는 것)

`fleet-dispatch.sh` 가 아래를 `herdr agent prompt` 로 넣는다. 짧게 유지하고 **계약은 이 문서를 읽게** 한다 —
프롬프트에 계약을 복사하면 두 벌이 되어 갈린다.

```
너는 fleet 워커 '<worker>' 다. 워크트리 <path> (슬롯 <N>) 에서만 작업한다.

다음을 순서대로 읽고 그대로 수행해라:
  1) <main>/docs/guides/fleet-orchestration.md  — §1 역할 · §3 라우팅 · §7 워커 규칙
  2) <main>/.claude/fleet/<run>/tasks/<worker>.md  — 네 임무와 수용 기준

시작하면 즉시:  echo running > <main>/.claude/fleet/<run>/signals/<worker>.status
```

## 7. 워커 규칙 (워커가 읽는 부분)

1. **커밋까지만.** 푸시 · PR · 머지 금지. 통합은 오케스트레이터 고유다.
2. **사용자에게 질문하지 마라.** 결정은 task 파일의 수용 기준 그대로. 판단이 필요하면 멈추고
   `blocked` 를 쓰고 이유를 report 에 남겨라.
3. **task 파일의 금지 경로를 건드리지 마라.** 다른 워커가 그 파일을 쥐고 있다.
4. **수용 기준을 고쳐 쓰지 마라.** 못 맞추겠으면 `blocked` 다. 기준을 낮추는 건 워커 권한이 아니다.
5. **BE pytest 는 env 소싱 의무.** ★`cd` 는 **절대 경로**로 써라 —
   ```bash
   cd <워크트리>/backend; set -a; . ./.env.local; set +a; uv run pytest
   ```
   `cd backend && set -a; ...` 를 같은 셸에서 두 번 돌리면 **거짓 red 가 난다**(실측).
   Bash 툴은 cwd 가 호출 간에 유지되므로 2회차의 `cd backend` 가 실패하고, `&&` 때문에
   `set -a` 만 건너뛴다. 뒤의 `.  ./.env.local` 은 `;` 라 그대로 돌지만 **export 가 아니라 셸
   지역 변수 대입**이 되어 pytest 가 5432 로 떨어진다. 코드는 멀쩡한데 빨간불이 뜬다.
6. ★**celery 를 타는 것(백테스트·라이브신호·옵티마이저)은 네 코드로 안 돈다.** worker 컨테이너가
   메인의 `src` 를 mount 한다. "돌려봤더니 되더라" 는 **메인 코드가 된 것**이다. 그 검증은 하지 말고
   report 에 "오케스트레이터 검증 필요" 로 넘겨라.
7. `make up`/`down`/`migrate`/`seed` 는 가드가 거부한다. 우회하지 마라 — 남이 깨진다.
8. 끝나면 `reports/<worker>.md` 에 **커밋 SHA · 만진 파일 전체 · 자기가 돌린 게이트와 그 숫자 ·
   못 한 것**을 적고 `echo done > signals/<worker>.status`.

---

## 8. 함정 (실측)

- **`agent prompt` 는 working 중인 워커에도 들어간다** — 입력이 섞인다. `fleet-dispatch.sh` 는 `idle`
  이 아니면 거부한다.
- **`--wait --until done` 으로 오래 못 기다린다** — Bash 최대 600초. 폴링으로 간다.
- **`blocked` 은 워커가 스스로 못 푼다** (권한 프롬프트). 사람이 그 pane 에 가서 눌러야 한다.
- ★**워커의 일부 명령은 하네스 classifier 가 막는다** — 첫 실전에서 `make seed` 가
  `Blocked by classifier` 로 셸에 도달조차 못 했다. 워커는 그걸 "가드가 막았다" 로 **오인하지 않고**
  `blocked` 로 올렸다(옳다). **가드 발화를 재는 task 는 오케스트레이터가 직접 실행해라.**
- ★**계약 문서 경로는 워커 워크트리 기준이다.** 메인 체크아웃은 전혀 다른 브랜치일 수 있다.
  `fleet-dispatch.sh` 가 존재를 확인하고, 없으면 분배 자체를 거부한다.
- **수용 기준에 `exit 1` 이라고 쓰지 마라** — `make` 는 2 로 감싼다. `종료 코드 != 0` 으로 써라.
- 나머지 9블로커는 `autonomous-parallel-sprints/references/blocker-playbook.md`. cmux 전제인 1~3번은
  herdr 에서는 해당 없다(trust 다이얼로그가 없다).
