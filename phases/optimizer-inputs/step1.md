# Step 1: `var_name` 자유 입력 → 드롭다운. 스윕 불가는 **숨기지 말고 비활성 + 사유**

## 읽어야 할 파일

- `apps/web/src/features/optimizer/components/param-rows-fieldset.tsx` (수정 대상 — 3폼 공용)
- `apps/web/src/features/optimizer/components/{grid-search,bayesian-search,genetic-search}-form.tsx`
- `apps/web/src/features/optimizer/components/optimizer-page-view.tsx`
- `apps/web/src/features/optimizer/use-strategy-inputs.ts` (step 0 산출)
- `apps/web/src/features/strategy/schemas.ts` — `isSweepable` · `SWEEPABLE_INPUT_TYPES`
- 스펙 관례 = `apps/web/src/features/optimizer/components/__tests__/optimizer-forms-field-errors.test.tsx`

## 작업

1. **`param-rows-fieldset.tsx`** 에 선택 prop `inputs?: InputDecl[]` 를 추가한다.
   - `inputs` 가 **비어 있지 않으면** `var_name` 칸을 `<select>` 로 렌더한다. RHF 배선은
     지금과 같다(`{...register(\`parameters.${idx}.var_name\`)}`) — 요소만 바뀐다.
   - 옵션 라벨은 `var_name` 을 **가공하지 마라**(override 키다). `title` 이 있으면 뒤에 붙인다.
   - 스윕 불가(`isSweepable(input) === false`)는 **목록에서 빼지 말고** `disabled` 옵션으로 두고
     라벨에 사유(`input_type`)를 적는다. 이유: 빼면 사용자가 「그 파라미터가 없다」고 읽는다.
   - 첫 옵션은 빈 값의 안내 옵션이다(선택 전 상태).
   - `inputs` 가 **비었으면 지금의 자유 입력을 그대로 쓴다**(파싱 실패·전략 미선택·input 0건).
     이유: 목록을 못 얻었다고 폼이 잠기면 안 된다.
2. **3폼**(grid/bayesian/genetic)이 `inputs?: InputDecl[]` 를 받아 `ParamRowsFieldset` 에 넘긴다.
3. **`optimizer-page-view.tsx`** 가 선택된 백테스트에서 `strategy_id` 를 꺼내
   (`backtestsQuery.data.items` 에 **이미 있다** — `BacktestSummary.strategy_id`, 추가 요청 0회)
   `useStrategyInputs(strategyId)` 로 `inputs` 를 얻어 3폼에 내려 준다.

## 벗어나면 안 되는 계약

- `form-schemas.ts` 의 `var_name` zod 스키마(`z.string().min(1, ...)`)를 바꾸지 마라.
  이유: wire 계약은 그대로다. 이 step 이 바꾸는 것은 **입력 방식**이지 제출 형태가 아니다.
- 스윕 불가 항목을 목록에서 제거하거나 폼 제출을 막지 마라. BE `_validate_grid_search_pre` 의
  422 가 최종 판정자다 — 화면은 **미리 알려 줄 뿐**이다.
- 백테스트가 안 골라졌을 때 폼을 잠그지 마라. 지금 동작(자유 입력)이 그대로 남는 것이 옳다.

## Acceptance Criteria

`phases/optimizer-inputs/index.json` 의 step 1 `ac` 와 동일하다. 요지:
새 스펙 green · **변이**(fieldset 을 `origin/main` 판으로 되돌리면 그 스펙이 red) ·
기존 옵티마이저 폼 스펙 3종 green · page-view 가 `useStrategyInputs` 를 실제로 쓴다 ·
`tsc --noEmit` clean.

새 스펙 `apps/web/src/features/optimizer/components/__tests__/param-rows-var-name-select.test.tsx`
가 최소한 이 셋을 재야 한다: ⑴ `inputs` 를 주면 `var_name` 이 **select** 이고 옵션이 전건 보인다 ·
⑵ 스윕 불가 항목이 **disabled 이며 사유가 라벨에 있다** · ⑶ `inputs` 가 비면 **자유 입력**이 남는다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. ★최종 판정은 러너가 재실행해 내린다 —
   `status` 를 `completed` 로 바꾸지 마라.
2. `apps/web/AGENTS.md` H-1~H-3 · 접근성(라벨·`aria-invalid`·`aria-describedby` 기존 배선 유지).
3. 사람 개입이 필요하면 `status:"blocked"` + `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- `apps/api/**` · `contracts/**` 를 건드리지 마라. 이유: BE 0줄이 이 경로의 전제다.
- `apps/web/src/features/strategy/**` · `apps/web/src/features/backtest/**` 를 **수정**하지 마라
  (import 는 한다). 이유: 같은 밤 다른 lane 이 그 디렉터리를 쥐고 있다.
- `@radix-ui/*` 를 직접 import 하지 마라(`apps/web/AGENTS.md`). 네이티브 `<select>` 로 족하다.
- `docs/status.md` · `docs/backlog.md` 를 건드리지 마라. 이유: lane 공유 파일이다.
- 커밋하지 마라(커밋은 러너 소관).
