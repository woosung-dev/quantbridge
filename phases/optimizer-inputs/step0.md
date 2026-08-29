# Step 0: `useStrategyInputs` — 옵티마이저가 Pine input 선언 목록을 얻는 경로를 만든다

## 읽어야 할 파일

- `apps/web/src/features/strategy/hooks.ts` — `useStrategy(id)` · `usePreviewParse(pineSource)`
- `apps/web/src/features/strategy/schemas.ts` — `InputDeclSchema` · `isSweepable` ·
  `SWEEPABLE_INPUT_TYPES` · `ParsePreviewResponseSchema`
- `apps/web/src/features/optimizer/hooks.ts` (이 도메인의 훅 관례)
- 스펙 관례 = `apps/web/src/features/optimizer/__tests__/hooks.core.test.tsx`
- `apps/web/AGENTS.md` — React Hooks 안전 H-1~H-3

## 배경 (2026-08-30 실측)

옵티마이저 폼은 Pine 변수명을 **손으로 치게** 한다(`form-schemas.ts` 의
`var_name: z.string().min(1, "변수 이름을 입력하세요.")`). 오타면 BE `_validate_grid_search_pre`
(`optimizer/engine/grid_search.py`)가 422 로 거부하고 **그제야** 선언 목록을 알려 준다.

[ADR-040] Stage 1 이후 그 목록은 이미 있다 — 다만 **`inputs` 를 주는 GET 이 없다.**
`inputs` 는 `POST /strategies/parse`(`ParsePreviewResponse`)와 `GET /strategies/{id}/brief`
두 곳에만 있고 `StrategyResponse` 에는 **없다**(필드 전수 확인).

★**확정 경로(2026-08-30 · 다시 논하지 마라)** = `GET /strategies/{id}` 로 `pine_source` 를 받아
`POST /strategies/parse` 에 넘긴다. 2왕복이지만 **BE 0줄 · 계약 변경 0**이다.
기각한 대안 둘: `/{id}/brief` 는 응답이 무겁고 brief 계약에 옵티마이저를 묶는다 ·
`StrategyResponse` 에 `inputs` 추가는 **OpenAPI 계약 파일**을 건드려 같은 밤 다른 lane 과 충돌한다.

★비용 함정은 없다 — 「콜드 파스 53.38초」는 **L2 디스크 캐시(PR #837, 2026-08-26) 이전 수치**다.
지금 콜드는 소스당 1회이고 재방문은 4.8ms 다. 비용을 이유로 설계를 비틀지 마라.

## 작업

새 파일 `apps/web/src/features/optimizer/use-strategy-inputs.ts` 를 만든다.

```ts
export interface StrategyInputsResult {
  inputs: InputDecl[];
  isLoading: boolean;
  error: Error | null;
}

/** strategyId → (GET /strategies/{id}) pine_source → (POST /strategies/parse) inputs. */
export function useStrategyInputs(strategyId: string | undefined): StrategyInputsResult;
```

- 구현은 `useStrategy` + `usePreviewParse` **합성**이다. 새 api 함수·새 query key 를 만들지 마라.
- `strategyId` 가 없으면 두 훅 다 자연히 비활성(`enabled`)이고 `inputs` 는 `[]` 다.
  **훅을 조건부로 호출하지 마라**(H-1) — 인자로 껐다 켠다.
- `error` 는 두 단계 중 먼저 난 것을 그대로 돌려준다. 삼키지 마라 — 화면이 사유를 말해야 한다.

스펙 `apps/web/src/features/optimizer/__tests__/use-strategy-inputs.test.tsx` 를 만든다:
`@/features/strategy/hooks` 를 mock 하고 ⑴ `strategyId` 없음 → `inputs: []` ·
⑵ 전략이 `pine_source` 를 주면 **그 문자열이 `usePreviewParse` 인자로 그대로** 넘어가고
`inputs` 가 나온다 · ⑶ 두 단계 중 하나가 실패하면 `error` 가 전파된다.

## Acceptance Criteria

`phases/optimizer-inputs/index.json` 의 step 0 `ac` 와 동일하다. 요지:
새 스펙 green · 훅이 `useStrategy` 와 `usePreviewParse` 를 **둘 다** 쓴다(구조 확인).

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. ★최종 판정은 러너가 재실행해 내린다 —
   `status` 를 `completed` 로 바꾸지 마라.
2. `apps/web/AGENTS.md` H-1~H-3 · Zod v4 규약 · TS strict.
3. 사람 개입이 필요하면 `status:"blocked"` + `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- `apps/api/**` 와 `contracts/**` 를 건드리지 마라. 이유: **BE 0줄 · 계약 변경 0** 이 이 경로를
  고른 이유 자체다. 같은 밤 다른 lane 이 계약 파일을 쥐고 있어 손대면 머지 충돌이 난다.
- `apps/web/src/features/strategy/**` 와 `apps/web/src/features/backtest/**` 를 **수정**하지 마라
  (import 는 한다). 이유: 같은 밤 다른 lane 이 그 디렉터리를 쥐고 있다.
- 이 step 에서 UI 를 바꾸지 마라(폼·fieldset). 이유: step 1 소관이다.
- `docs/status.md` · `docs/backlog.md` 를 건드리지 마라. 이유: lane 공유 파일이다.
- 커밋하지 마라(커밋은 러너 소관).
