# Step 4 — [BL-708] 원장 종결 (3면 + ⓪ 표)

코드가 닫혔다. 이 step 은 **원장만** 고친다. 코드는 한 줄도 안 건드린다.

## 읽어야 할 파일

- `docs/reference/operations/workflows/bl-audit-checklist.md` — 종결 절차 정본. **먼저 읽어라**
- `docs/backlog.md` 의 `### BL-708` 섹션(`**상태:**` 줄) + 인덱스 표 행
- `docs/roadmap.md` 의 `**BL-708**` 체크박스 줄
- `docs/status.md` 의 `### ⓪ 다음 후보` 표 — **V 행**이 [BL-708] 이다
- `AGENTS.md` 의 「문서 — 어느 질문은 어디가 답하나」 절 — 판정어 5종과 3면 규칙
- `phases/bl708/index.json` 의 step 1~3 `summary` — 무엇이 실제로 닫혔는지

## 작업

1. **3면을 맞춘다** (`scripts/bl-audit.sh` 가 대조하는 세 곳):
   - `docs/backlog.md` `### BL-708` 섹션의 `**상태:**` 줄 → RESOLVED
   - `docs/backlog.md` 인덱스 표의 BL-708 행
   - `docs/roadmap.md` 의 BL-708 체크박스
2. **⓪ 표를 맞춘다**: BL-708 이 더 이상 ACTIVE 가 아니므로 `docs/status.md` 의 **V 행**을
   살아 있는 행에서 뺀다. ★계약은 「살아 있는 행 == ACTIVE ∪ (PARTIAL ∧ 도래)」이고
   `scripts/docs-audit.sh` 가 강제한다. 살아 있는 행이 **3개 미만이 되면 안 된다**(현재 8건이라 여유 있다).
3. 상태줄·표 행에는 **step 1~3 이 실제로 한 것**을 적어라. 「고쳤다」가 아니라
   **무엇을 어떻게 결정적으로 만들었는지**와 **어떤 실측이 근거인지**를 적는다.
4. 요약 줄 길이 상한을 지켜라 — `backlog.md`·`roadmap.md` **1,000자** (`docs-audit.sh` 강제).

## AC (Acceptance Criteria) — 그대로 실행해서 전건 통과해야 한다

```bash
cd "$(git rev-parse --show-toplevel)"

# AC-1 3면 정합
scripts/bl-audit.sh                                   # rc=0
scripts/bl-audit.sh --list RESOLVED | grep -q 'BL-708'   # rc=0

# AC-2 ⓪ 표 정체성 · 링크 · 길이 상한
scripts/docs-audit.sh                                 # rc=0

# AC-3 BL-708 이 미완 쪽에 남아 있지 않다
scripts/bl-audit.sh --list ACTIVE   | grep -q 'BL-708' && exit 1
scripts/bl-audit.sh --list DEFERRED | grep -q 'BL-708' && exit 1
scripts/bl-audit.sh --list UNKNOWN  | grep -q 'BL-708' && exit 1
echo "AC-3 PASS"

# AC-4 ★「다음 행동 =」 을 건드리지 않았다 (전체 13줄 유지)
test "$(grep -c '다음 행동 =' docs/status.md)" = "13"

# AC-5 이 step 은 코드를 한 줄도 안 바꿨다
#     ★기준은 `main` 이 아니라 `HEAD` 다 — step 1~3 이 `frontend/e2e/` 를 정당하게 고쳤고
#       그건 이미 커밋돼 있다. 여기서 재는 것은 **step 4 자신의 작업 트리**다.
test -z "$(git diff HEAD --name-only -- frontend/ backend/ scripts/)"
```

> AC-3 의 `&& exit 1` 은 「발견되면 실패」다. 발견되지 않으면 `grep` 이 rc=1 을 내고 `&&` 가
> 끊기므로 마지막 `echo` 로 rc 를 0 으로 확정한다 — 세 줄을 블록의 마지막에 두지 마라.

## 검증 절차

1. `scripts/bl-audit.sh` 출력의 `active=` 수가 **8 → 7** 로 줄었는지 확인
2. `git diff main --stat` 이 `docs/` 와 `phases/` 만 담고 있는지 확인
3. step 4 를 `completed` + `summary` 에 **① 3면에서 바꾼 줄 ② active 수 변화** 를 한 줄로 적는다

## 금지사항

- `docs/status.md` 의 **`다음 행동 =`** 를 추가·삭제·수정하지 마라. 이유: 다음 회차의 진입점이고
  CONTROL 이 회차 종료 시 B회차(BL-709)로 넘긴다. 여기서 건드리면 살아 있는 지시가 둘이 된다.
- BL 상태를 손으로 세지 마라. 이유: `scripts/bl-audit.sh` 가 정본이다 (`AGENTS.md`).
- `dev-log/` 에 새 파일을 만들지 마라. 이유: 회고(반증 카드)는 회차 종료 시 CONTROL 몫이고,
  dev-log 신규 추가는 `INDEX.md` 갱신을 함께 요구한다.
- 코드·테스트·스크립트를 고치지 마라. 이유: AC-5 가 그것을 막는다. 코드에 문제가 남았다면
  status 를 `blocked` 로 하고 `blocked_reason` 에 적어라.
- BL-708 을 RESOLVED 로 올리기 전에 step 1~3 의 `summary` 를 읽어라. 셋 중 하나라도
  실제로 안 닫혔으면 `PARTIAL` 로 적고 무엇이 남았는지 명시해라. 이유: 원장이 코드보다
  낙관적이면 다음 회차가 없는 것을 있다고 믿는다.
