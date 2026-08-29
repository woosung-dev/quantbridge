# Step 1: 정상 흐름 진입점을 만든다 — 새 전략 위저드가 indicator 를 알아보고 변환을 권한다

## 읽어야 할 파일

- `apps/web/src/features/strategy/components/new/new-strategy-wizard.tsx`
  (특히 `applyPineSource` · `usePreviewParse` 로 만든 `parseResult`)
- `apps/web/src/features/strategy/components/new/parse-result-panel.tsx` (수정 대상)
- `apps/web/src/features/strategy/schemas.ts` 의 `DeclarationSchema` / `ParsePreviewResponseSchema`
- `apps/web/src/features/backtest/components/ConvertWithAIButton.tsx` (step 0 이 고친 버튼)
- 기존 스펙 = `apps/web/src/features/strategy/components/new/__tests__/parse-result-panel.test.tsx`
- 선례(같은 버튼을 쓰는 유일한 기존 호출처) = `apps/web/src/components/form-error-inline.tsx`

## 배경 (2026-08-30 코드 대조)

`ConvertWithAIButton` 의 **유일한 호출처가 422 에러 카드**(`form-error-inline.tsx`)다.
즉 사용자는 백테스트를 제출해 실패해야만 변환 버튼을 만난다 — **정상 흐름 진입점이 0개**다.

한편 새 전략 위저드는 붙여넣은 소스를 자동 파싱해 `ParsePreviewResponse` 를 이미 쥐고 있고,
그 응답의 `declaration.kind` 는 `"strategy" | "indicator" | "library" | "unknown"` 이다.
**`indicator` 를 붙여넣은 사용자가 바로 그 사용자다** — 지금은 그대로 저장할 수 있고,
저장한 뒤 백테스트에서야 막힌다.

## 작업

1. `parse-result-panel.tsx` 에 **선택 prop 2개**를 추가한다(선례 = `form-error-inline.tsx`):
   - `indicatorCode?: string`
   - `onConverted?: (result: ConvertIndicatorResponse) => void`
     (타입은 `@/features/backtest/schemas` 에서 가져온다)
   `result.declaration?.kind === "indicator"` 이고 두 prop 이 모두 있으면, 카드 본문에
   **안내 문구 + `<ConvertWithAIButton indicatorCode={...} onConverted={...} />`** 를 렌더한다.
   문구는 사실만 적는다 — 이 스크립트는 `indicator` 라 진입/청산 주문이 없고, 백테스트를 하려면
   `strategy` 로 바꿔야 한다는 것. 기존 `supported`/`unsupported` 분기 마크업은 건드리지 마라.
2. `new-strategy-wizard.tsx` 가 그 두 prop 을 넘긴다:
   - `indicatorCode={pineSource}`
   - `onConverted` 는 **변환된 코드를 에디터에 넣는다** — 기존 `applyPineSource(result.converted_code)`
     를 그대로 쓴다(그러면 debounce 자동 파싱이 다시 돌아 판정이 갱신된다). 응답의
     `warnings` 가 있으면 `toast` 로 보여 준다. ★그 warning 이 「LLM 미사용」을 말하는 자리다.
3. 새 스펙을 만든다:
   `apps/web/src/features/strategy/components/new/__tests__/parse-result-panel-convert.test.tsx`
   - `declaration.kind === "indicator"` 인 결과 + 두 prop 을 주면 변환 버튼이 **보인다**
   - `declaration.kind === "strategy"` 면 **안 보인다**
   - 두 prop 이 없으면 **안 보인다**

## 벗어나면 안 되는 계약

- 조건식은 **`result.declaration?.kind === "indicator"`** 로 쓴다(문자열 리터럴 `"indicator"`).
  이유: 러너의 변이 AC 가 그 리터럴을 바꿔 스펙의 판별력을 잰다.
- `ConvertWithAIButton` 을 복사하거나 옮기지 마라 — `@/features/backtest/components/ConvertWithAIButton`
  를 그대로 import 한다. 이유: 사본이 생기면 step 0 의 `mode` 수정이 한쪽에만 적용된다.
- 저장 게이트(`canSave`)를 바꾸지 마라. 이유: 이 step 은 **진입점**을 여는 것이지 저장 정책을
  바꾸는 것이 아니다.

## Acceptance Criteria

`phases/convert-reach/index.json` 의 step 1 `ac` 와 동일하다. 요지:
새 스펙 + 기존 `parse-result-panel.test.tsx` green · **변이**(`"indicator"` → `"library"`)에 red ·
위저드가 두 prop 을 실제로 넘긴다(구조 확인) · `tsc --noEmit` clean.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. ★최종 판정은 러너가 재실행해 내린다 —
   `status` 를 `completed` 로 바꾸지 마라.
2. `apps/web/AGENTS.md` — H-1~H-3(Hooks 안전) · 화면 컴포넌트의 자리([ADR-035]) · Zod v4 규약.
3. 사람 개입이 필요하면 `status:"blocked"` + `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- `apps/api/**` 를 건드리지 마라. 이유: BE 계약은 그대로다.
- `apps/web/src/features/backtest/**` 를 이 step 에서 수정하지 마라(import 는 한다).
  이유: step 0 의 diff 와 섞이면 무엇이 무엇을 고쳤는지 리뷰가 못 가른다.
- `apps/web/src/features/optimizer/**` 를 건드리지 마라. 이유: 같은 밤 다른 lane 이 그 디렉터리를
  통째로 쥐고 있다 — 겹치면 머지 충돌이 난다.
- `docs/status.md` · `docs/backlog.md` 를 건드리지 마라. 이유: lane 공유 파일이다.
- 커밋하지 마라(커밋은 러너 소관).
