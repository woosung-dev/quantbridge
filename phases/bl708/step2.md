# Step 2 — 감사 코어에서 비결정 원천을 없앤다 (판정이 회차에 안 흔들리게)

step 1 이 무엇이 갈리는지 실측으로 짚었다. 이 step 은 **감사 코어가 소유한 몫**을 고쳐
같은 커밋에서 몇 번을 돌려도 **같은 답**이 나오게 만든다.

★[BL-708] 이 요구하는 것은 「초록」이 아니라 **「같은 답」**이다. 초록으로 만드는 것은
step 3 몫이고, 이 step 의 계약은 **결정성**이다.

## 읽어야 할 파일

- `phases/bl708/index.json` 의 step 1 `summary` — 앞 step 이 무엇을 관측했는지
- `frontend/e2e/design-canon-audit.ts` — 이 step 의 유일한 수정 대상
- `docs/backlog.md` `### BL-708` 의 **권장 접근** 2갈래
- `frontend/e2e/design-canon-public.spec.ts` · `frontend/e2e/authed-canon-p1.spec.ts` —
  같은 코어를 쓰는 **앱 쪽** 대상. 여기 부수 피해가 없어야 한다

## 작업

1. step 1 이 귀속한 비결정 원천을 **`frontend/e2e/design-canon-audit.ts` 안에서** 처리한다.
   - 처방을 하나 고르고, **왜 그쪽인지**를 코드 주석에 실측 근거와 함께 남긴다.
   - `AuditOptions` 에 이미 `ignoreConsole` · `prepare` 같은 확장점이 있다. 새 축을 만들기 전에
     있는 것으로 되는지 먼저 봐라.
2. ★**앱 쪽 감사의 판별력을 깎지 마라.** `design-canon-public` · `authed-canon-p1` 은 같은 코어로
   **실제 앱**을 잰다. 거기서 진짜 결함이던 것이 이 수정으로 조용히 안 잡히게 되면 안 된다.
   코어에서 무언가를 **일괄로 무시**하는 방향을 골랐다면 그건 틀린 방향이다 —
   무시 여부는 대상을 아는 spec 이 정해야 한다 (`design-canon-audit.ts:100-103` 이 그 원칙을
   이미 적어 뒀다).
3. 렌더 상태를 옮기는 처방(폰트를 못 받게 막는 등)은 `CANON_BASELINE` 을 흔든다.
   **그 경우 기준선 표를 고치지 말고** step 을 `blocked` 로 올려라 (아래 금지사항 참조).

## AC (Acceptance Criteria) — 그대로 실행해서 전건 통과해야 한다

```bash
cd frontend

# AC-1 타입/린트
pnpm typecheck            # rc=0
pnpm lint                 # rc=0

# AC-2 ★독립 프로세스 3회가 **같은 답**을 낸다 (--repeat-each 로 대체하지 마라. 아래 금지사항)
rm -f /tmp/bl708-s2-rc.txt
for i in 1 2 3; do
  PLAYWRIGHT_BASE_URL=http://localhost:3100 pnpm exec playwright test \
    e2e/design-canon-calibration.spec.ts --project=chromium-design-canon --no-deps \
    --reporter=line >"/tmp/bl708-s2-$i.txt" 2>&1
  echo "$?" >>/tmp/bl708-s2-rc.txt
done
cat /tmp/bl708-s2-rc.txt                                   # 증거로 남긴다
test "$(sort -u /tmp/bl708-s2-rc.txt | wc -l | tr -d ' ')" = "1"   # 답이 하나여야 한다

# AC-3 3회의 pass/fail 집계가 서로 같다 (rc 만으로는 어느 파일이 갈렸는지 안 보인다)
test "$(for i in 1 2 3; do grep -aoE '[0-9]+ (passed|failed)' "/tmp/bl708-s2-$i.txt" \
  | sort | tr '\n' ' '; echo; done | sort -u | wc -l | tr -d ' ')" = "1"

# AC-4 spec 파일은 여전히 한 글자도 안 바뀌었다
cd .. && test -z "$(git diff main -- frontend/e2e/design-canon-calibration.spec.ts)"
```

## 검증 절차

1. `/tmp/bl708-s2-1.txt` ~ `-3.txt` 의 `reached:` 줄에서 step 1 이 넣은 `subresourceFail=` 이
   3회 모두 어떻게 나오는지 눈으로 대조한다
2. `git diff main --stat -- frontend/e2e/` 가 여전히 `design-canon-audit.ts` **하나**인지 확인
3. step 2 를 `completed` + `summary` 에 **① 고른 처방 ② 3회 rc ③ 앱 쪽 판별력을 어떻게
   보존했는지** 를 한 줄로 적는다

## 금지사항

- `--repeat-each=3` 으로 AC-2 를 대체하지 마라. 이유: [BL-708] 원문이 「한 회차 안에서는
  결정적이고 **회차 사이에서만** 갈린다」고 적었다. `--repeat-each` 는 같은 프로세스 안에서
  도므로 갈리는 축을 건드리지 않는다 — 판별력이 0 이다.
- `--grep` 으로 대상을 좁혀 AC-2 를 돌리지 마라. 이유: 단독 실행은 3/3 초록이다(step 1 관측 4번).
  전량 22건이 병렬로 도는 상태에서만 재현된다.
- `CANON_BASELINE` · `LIGHT_BASELINE` 의 숫자를 바꾸지 마라. 표를 고쳐야만 통과한다면 그것은
  네 처방이 **렌더 상태를 옮겼다**는 뜻이다. 그때는 status 를 `blocked` 로 하고
  `blocked_reason` 에 「어느 숫자가 몇으로 바뀌어야 하는지」를 적고 즉시 멈춰라.
  이유: 기준선은 2026-07-20 확정 정본이고, 판단 없이 표를 맞추면 검사기가 자기 자신을
  정당화한다 (`design-canon-calibration.spec.ts:22-30`).
- `design-canon-calibration.spec.ts` 를 수정하지 마라. 이유: spec 계약은 step 3 몫이다.
- 테스트를 `skip` · `fixme` 처리하거나 `test.setTimeout` 을 늘려 넘기지 마라.
  이유: [BL-708] 은 「대기를 늘린다」가 **틀린 방향**이라고 CI 실측으로 이미 적었다.
