# Step 3 — 캘리브레이션 spec 이 자기 판정 계약을 명시적으로 갖게 한다

step 2 가 코어를 결정적으로 만들었다. 남은 것은 **spec 층**이다. 지금 이 spec 의 판정 계약은
암묵적이다 — 「하드 실패 0」이라고만 적혀 있고, **정적 `file://` 프로토타입**이라는 자기 대상의
성질이 판정에 어떻게 반영되는지는 어디에도 안 적혀 있다. 그래서 외부 요인이 판정에 섞여도
다음 사람이 그것을 읽어낼 수 없다.

## 읽어야 할 파일

- `phases/bl708/index.json` 의 step 1·2 `summary`
- `frontend/e2e/design-canon-calibration.spec.ts` — 이 step 의 유일한 수정 대상
- `frontend/e2e/design-canon-audit.ts` 의 `AuditOptions`(`:368-390`) — spec 이 쓸 수 있는 확장점
- `docs/backlog.md` `### BL-708` 의 **권장 접근 ⑵**(문턱 근처 WARN 강등)

## 작업

1. 이 spec 이 **무엇을 하드 실패로 세고 무엇을 안 세는지**를 명시적으로 만든다.
   - 대상은 커밋된 정적 HTML 이고 앱이 아니다. 앱 spec 과 같은 계약이어야 할 이유가 없다.
   - 계약을 바꿨다면 **왜 그것이 판별력을 안 깎는지**를 주석에 실측과 함께 남겨라.
2. 반복 안정성의 **근거를 spec 상단 주석에 남긴다** — 「독립 프로세스 N회에서 같은 답이
   나왔다(날짜·실측)」. 다음 회차가 이 실측을 다시 유도하지 않게 하는 것이 목적이다.
3. 필요하다고 판단하면 **권장 접근 ⑵**(문턱 ±0.5 이내 WARN 강등)를 여기서 한다. 안 했다면
   `summary` 에 **왜 불필요했는지**를 적어라.

## AC (Acceptance Criteria) — 그대로 실행해서 전건 통과해야 한다

```bash
cd frontend

# AC-1 타입/린트
pnpm typecheck            # rc=0
pnpm lint                 # rc=0

# AC-2 ★독립 프로세스 3회가 **전건 초록** (22 tests × 3)
for i in 1 2 3; do
  PLAYWRIGHT_BASE_URL=http://localhost:3100 pnpm exec playwright test \
    e2e/design-canon-calibration.spec.ts --project=chromium-design-canon --no-deps \
    --reporter=line >"/tmp/bl708-s3-$i.txt" 2>&1 || { echo "run $i FAILED"; exit 1; }
done
echo "AC-2 PASS"

# AC-3 3회 모두 22건을 **실제로 돌렸다** (0건 초록 차단)
for i in 1 2 3; do grep -aq '22 passed' "/tmp/bl708-s3-$i.txt" || { echo "run $i 22건 아님"; exit 1; }; done
echo "AC-3 PASS"

# AC-4 이 step 은 spec 을 실제로 고쳤다
cd .. && test -n "$(git diff main -- frontend/e2e/design-canon-calibration.spec.ts)"
```

## 검증 절차

1. `git diff main -- frontend/e2e/design-canon-calibration.spec.ts` 를 통독하고,
   바뀐 판정 계약이 주석으로 설명돼 있는지 확인
2. `grep -n 'CANON_BASELINE' -A 20 frontend/e2e/design-canon-calibration.spec.ts` 로
   기준선 숫자 17개가 원본 그대로인지 눈으로 대조
3. step 3 을 `completed` + `summary` 에 **① 바꾼 판정 계약 ② 3회 결과 ③ WARN 강등 채택 여부와
   근거** 를 한 줄로 적는다

## 금지사항

- `CANON_BASELINE` · `LIGHT_BASELINE` 의 숫자를 바꾸지 마라. 이유: step 2 와 같다 —
  판단 없이 표를 맞추면 검사기가 자기 자신을 정당화한다.
- 위생 메타테스트 3건(`위생 — 캘리브레이션 대상이 실제로 존재한다`)을 약화시키지 마라.
  이유: 그 3건은 「인벤토리가 조용히 비면 캘리브레이션이 0건을 돌고 그린이 된다」를 막는
  장치다 (spec `:64-66`).
- `design-canon-audit.ts` 를 수정하지 마라. 이유: 코어는 step 2 가 이미 닫았다. 여기서 또
  건드리면 「코어가 고친 것인지 spec 이 고친 것인지」 귀속이 사라진다.
- `test.skip` · `test.fixme` · `--repeat-each` · `--grep` 로 AC 를 우회하지 마라.
  이유: step 2 금지사항과 같다.
