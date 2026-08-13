# Step 4 — [BL-709] 원장 종결 (3면 + ⓪ 표)

코드가 닫혔다. 이 step 은 **원장만** 고친다. 코드는 한 줄도 안 건드린다.

## 읽어야 할 파일

- `docs/reference/operations/workflows/bl-audit-checklist.md` — 종결 절차 정본. **먼저 읽어라**
- `docs/backlog.md` 의 `### BL-709` 섹션(`**상태:**` 줄) + 인덱스 표 행
- `docs/roadmap.md` 의 `**BL-709**` 체크박스 줄
- `docs/status.md` 의 `### ⓪ 다음 후보` 표 — **W 행**이 [BL-709] 다
- `AGENTS.md` 의 「문서 — 어느 질문은 어디가 답하나」 절 — 판정어 5종과 3면 규칙
- `phases/bl709/index.json` 의 step 1~3 `summary` — 무엇이 실제로 닫혔는지

## 작업

1. **3면을 맞춘다** (`scripts/bl-audit.sh` 가 대조하는 세 곳):
   - `docs/backlog.md` `### BL-709` 섹션의 `**상태:**` 줄 → RESOLVED
   - `docs/backlog.md` 인덱스 표의 BL-709 행
   - `docs/roadmap.md` 의 BL-709 체크박스
2. **⓪ 표를 맞춘다**: BL-709 가 더 이상 ACTIVE 가 아니므로 `docs/status.md` 의 **W 행**을
   살아 있는 행에서 뺀다(취소선 + 종결 표기). ★계약은 「살아 있는 행 == ACTIVE ∪ (PARTIAL ∧ 도래)」이고
   `scripts/docs-audit.sh` 가 강제한다. 살아 있는 행이 **3개 미만이 되면 안 된다**
   (착수 전 실측 7건이라 여유 있다 — 이 종결로 6건이 된다).
3. 상태줄·표 행에는 **step 1~3 이 실제로 한 것**을 적어라. 「고쳤다」가 아니라
   **무엇을 1벌로 합쳤고 무엇이 근거인지**(어떤 AC 가 무엇을 쟀는지)를 적는다.
4. 요약 줄 길이 상한을 지켜라 — `backlog.md`·`roadmap.md` **1,000자** (`docs-audit.sh` 강제).

## AC (Acceptance Criteria)

★**정본은 `phases/bl709/index.json` 의 step 4 `ac` 배열이다.** 아래는 그것과 **같은 문자열**이다.
러너가 이 커맨드를 **독립적으로 재실행**하고 하나라도 rc≠0 이면 `completed` 를 취소한다.

```bash
cd "$(git rev-parse --show-toplevel)" && scripts/bl-audit.sh
cd "$(git rev-parse --show-toplevel)" && scripts/bl-audit.sh --list RESOLVED | grep -q 'BL-709'
cd "$(git rev-parse --show-toplevel)" && scripts/docs-audit.sh
cd "$(git rev-parse --show-toplevel)" && ! scripts/bl-audit.sh --list ACTIVE | grep -q 'BL-709' && ! scripts/bl-audit.sh --list DEFERRED | grep -q 'BL-709' && ! scripts/bl-audit.sh --list UNKNOWN | grep -q 'BL-709'
cd "$(git rev-parse --show-toplevel)" && test "$(grep -c '다음 행동 =' docs/status.md)" = "13"
cd "$(git rev-parse --show-toplevel)" && test "$(git diff main --name-only -- frontend/ | LC_ALL=C sort | tr '\n' '|')" = "frontend/src/app/(dashboard)/strategies/_components/strategy-list.tsx|frontend/src/app/(dashboard)/strategies/page.tsx|frontend/src/features/strategy/__tests__/sort.test.ts|frontend/src/features/strategy/sort.ts|"
```

> 6번째가 「이 step 은 코드를 안 고쳤다」를 재는 방식이다. ★기준을 `git diff HEAD` 로 잡지 않았다 —
> 세션이 자기 변경을 커밋하면 `HEAD` 대비 diff 가 비어 **아무것도 안 재는 항진명제**가 되기 때문이다.
> 대신 **브랜치 전체의 FE 변경 파일 집합이 step 1~3 의 4개 그대로인지**를 잰다(커밋 시점과 무관).
> 파일을 하나라도 더 만들거나 고치면 red 다.

## 검증 절차

1. 위 AC 6건을 순서대로 실행해 전건 rc=0 을 확인한다.
2. `scripts/bl-audit.sh` 출력의 `active=` 수가 **7 → 6** 으로 줄었는지 확인한다.
3. `git diff main --stat` 이 `docs/` 와 `phases/` 만 새로 담고 있는지 확인한다
   (`frontend/`·`scripts/` 는 앞 step 과 하네스 개조분 그대로여야 한다).
4. step 4 를 `completed` + `summary` 에 **① 3면에서 바꾼 줄 ② active 수 변화**를 한 줄로 적는다.

## 금지사항

- `docs/status.md` 의 **`다음 행동 =`** 를 추가·삭제·수정하지 마라. 이유: 다음 회차의 진입점이고
  회차 종료 시 CONTROL 이 넘긴다. 여기서 건드리면 살아 있는 지시가 둘이 된다. 5번째 AC 가 13줄을 잰다.
- BL 상태를 손으로 세지 마라. 이유: `scripts/bl-audit.sh` 가 정본이다 (`AGENTS.md`).
- `dev-log/` 에 새 파일을 만들지 마라. 이유: 회고(반증 카드)는 회차 종료 시 CONTROL 몫이고,
  dev-log 신규 추가는 `INDEX.md` 갱신을 함께 요구한다.
- 코드·테스트·스크립트를 고치지 마라. 이유: 6번째 AC 가 그것을 막는다. 코드에 문제가 남았다면
  status 를 `blocked` 로 하고 `blocked_reason` 에 적어라.
- BL-709 를 RESOLVED 로 올리기 전에 step 1~3 의 `summary` 를 읽어라. 셋 중 하나라도 실제로
  안 닫혔으면 `PARTIAL` 로 적고 무엇이 남았는지 명시해라. 이유: 원장이 코드보다 낙관적이면
  다음 회차가 없는 것을 있다고 믿는다.
- 다른 BL 을 함께 종결하지 마라. 이유: 이 회차의 표본은 BL-709 하나다.
