# Step 0: `mode: "sliced"` 로 바꾼다 — LLM 을 아예 안 부르는 경로를 처음으로 켠다

## 읽어야 할 파일

- `apps/web/src/features/backtest/components/ConvertWithAIButton.tsx` (수정 대상)
- `apps/web/src/features/backtest/api.ts` 의 `convertIndicator`
- `apps/web/src/features/backtest/schemas.ts` 의 `ConvertIndicatorRequestSchema` / `...ResponseSchema`
- `apps/api/src/strategy/convert/service.py` 의 `convert()` (BE 가 `sliced` 에서 무엇을 하나)
- 기존 스펙의 관례 = `apps/web/src/features/backtest/__tests__/api.test.ts`

## 배경 (2026-08-30 코드 대조)

BE `convert/service.py:52-68` 은 `mode="sliced"` 면 `SignalExtractor` 로 슬라이싱한 뒤
**`result.is_runnable` 이면 그 자리에서 반환한다** — `input_tokens=0, output_tokens=0`,
warning 은 「AST 슬라이싱으로 직접 실행 가능한 코드 추출 (LLM 미사용)」.
즉 이것은 「토큰 77~97% 절감」이 아니라 **경우에 따라 LLM 왕복 0회**(지연 0 · 비용 0)다.
실행 불가일 때만 슬라이스된 코드를 LLM 에 넘긴다.

그런데 FE 가 `mode: "full"` 을 하드코딩(`ConvertWithAIButton.tsx:29`)한 탓에
**이 경로는 한 번도 실행된 적이 없다.**

## 작업

1. `ConvertWithAIButton.tsx` 의 요청 본문에서 `mode: "full"` 을 **`mode: "sliced"`** 로 바꾼다.
   왜 그런지(= 먼저 AST 슬라이싱을 시도하고, 실행 가능하면 LLM 을 아예 안 부른다) 주석 1~2줄을
   남긴다. 그 밖의 동작·마크업은 건드리지 마라.
2. 새 스펙을 만든다:
   `apps/web/src/features/backtest/components/__tests__/convert-with-ai-button.test.tsx`
   - `../api`(`convertIndicator`)와 `@/hooks/use-auth-ctx` 를 mock 한다.
   - 버튼을 클릭하면 `convertIndicator` 가 **`mode: "sliced"` 를 담은 본문**으로 호출되는지 단언한다.
     ★이 단언이 이 step 의 전부다 — 러너가 `"sliced"` 를 `"full"` 로 되돌려 red 가 나는지 잰다.
   - 성공 시 `onConverted` 가 응답으로 호출되는지도 단언한다.

## 벗어나면 안 되는 계약

- 요청 본문의 `mode` 값은 **리터럴 `"sliced"`** 여야 한다(변수·상수 우회 금지). 이유: 러너의
  변이 AC 가 그 리터럴을 되돌려 스펙의 판별력을 잰다. 우회하면 판정 자체가 성립하지 않는다.
- `mode` 를 사용자에게 고르게 하는 토글을 만들지 마라. 이유: BE 가 이미 실행 불가일 때
  LLM 으로 넘어간다 — 사용자가 고를 것이 없다.

## Acceptance Criteria

`phases/convert-reach/index.json` 의 step 0 `ac` 와 동일하다. 요지:
새 스펙 green · **변이**(`"sliced"` → `"full"`)에 그 스펙이 red.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. ★최종 판정은 러너가 재실행해 내린다 —
   `status` 를 `completed` 로 바꾸지 마라.
2. `apps/web/AGENTS.md` 의 React Hooks 안전 규칙(H-1~H-3)과 TS 컨벤션을 지켰는지 확인한다.
3. 사람 개입이 필요하면 `status:"blocked"` + `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- `apps/api/**` 를 건드리지 마라. 이유: BE 는 이미 완비다. 이 lane 은 FE 도달 경로만 연다.
  (BE `convert` 를 provider 층으로 옮기는 [BL-834] ⑴ 은 **다음 회차**다.)
- `apps/web/src/features/strategy/**` 를 이 step 에서 건드리지 마라. 이유: step 1 소관이다.
- `docs/status.md` · `docs/backlog.md` 를 건드리지 마라. 이유: 3 lane 이 공유하는 파일이라
  머지 충돌이 난다.
- 커밋하지 마라(커밋은 러너 소관).
