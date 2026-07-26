# H2 Sprint 9 · Phase C — Frontend Stress Test 탭

**Branch:** `feat/h2s9-frontend-mcwfa` (from `stage/h2-sprint9` which includes Phase A + B)
**Date:** 2026-04-24
**Master plan:** `/Users/woosung/.claude/plans/h2-sprint-9-validated-ember.md` §Phase C
**Worktree isolation:** YES
**Depends on:** Phase B merged (API endpoints + schemas 필요)

## Scope (고정)

1. **Backtest detail 페이지에 "스트레스 테스트" 탭 추가** — 기존 4 탭 (overview/metrics/analysis/trades) 옆에 5번째.
2. **Monte Carlo fan chart** (recharts AreaChart) — p5~p95 fan + median line.
3. **Walk-Forward bar chart** (recharts BarChart) — fold 별 IS vs OOS return + degradation ratio 표시.
4. **Polling** — 상태 기반 dynamic `refetchInterval` (LESSON-004 준수).
5. **기존 `features/backtest/` 확장** — api, hooks, schemas, query-keys.

## Out of scope

- Parameter stability (Sprint 10)
- Mobile-specific fan chart simplification (추후 DX 개선)
- Phase D 관측성

## 참조 파일 (사전 read 필수)

### Phase B 계약 (stress_test API)

- `backend/src/stress_test/router.py` — 4 엔드포인트 정확한 경로/스키마
- `backend/src/stress_test/schemas.py` — `CreateMonteCarloRequest`, `CreateWalkForwardRequest`, `StressTestCreatedResponse`, `StressTestDetail`, `MonteCarloResultOut`, `WalkForwardResultOut`
- `backend/src/stress_test/serializers.py` — JSONB ↔ Decimal/str 변환 확인
- `backend/src/stress_test/engine/monte_carlo.py::MonteCarloResult` — `equity_percentiles: dict[str, list[Decimal]]` (str keys "5"/"25"/"50"/"75"/"95")
- `backend/src/stress_test/engine/walk_forward.py::WalkForwardResult` — `valid_positive_regime`, `total_possible_folds`, `was_truncated` 필드

### Frontend 기존 패턴

- `frontend/src/app/(dashboard)/backtests/_components/backtest-detail-view.tsx:138-144` — 탭 구조
- `frontend/src/app/(dashboard)/backtests/_components/equity-chart.tsx` — recharts ResponsiveContainer 패턴 + width guard
- `frontend/src/features/backtest/hooks.ts:139-147` — `useBacktestProgress` polling 예시 (LESSON-004 안전)
- `frontend/src/features/backtest/api.ts` — API 호출 함수 패턴 (Clerk token 주입)
- `frontend/src/features/backtest/query-keys.ts` — factory 패턴 (userId 포함)
- `frontend/src/features/backtest/schemas.ts` — zod v4 스키마 패턴
- `.ai/stacks/nextjs/frontend.md` §React Hooks 안전 규칙 H-1, H-2, H-3 (준수 필수)

## 신규 파일

### 1. `frontend/src/features/backtest/schemas.ts` 확장

```typescript
import { z } from "zod/v4";

// --- 기존 스키마 그대로 ---

// --- Stress Test 신규 ---

export const stressTestKindSchema = z.enum(["monte_carlo", "walk_forward"]);
export type StressTestKind = z.infer<typeof stressTestKindSchema>;

export const stressTestStatusSchema = z.enum([
  "queued",
  "running",
  "completed",
  "failed",
]);
export type StressTestStatus = z.infer<typeof stressTestStatusSchema>;

export const monteCarloResultSchema = z.object({
  samples: z.number().int(),
  ci_lower_95: z.string(), // Decimal as string
  ci_upper_95: z.string(),
  median_final_equity: z.string(),
  max_drawdown_mean: z.string(),
  max_drawdown_p95: z.string(),
  equity_percentiles: z.record(
    z.enum(["5", "25", "50", "75", "95"]),
    z.array(z.string()),
  ),
});
export type MonteCarloResult = z.infer<typeof monteCarloResultSchema>;

export const walkForwardFoldSchema = z.object({
  fold_index: z.number().int(),
  train_start: z.string(), // ISO datetime
  train_end: z.string(),
  test_start: z.string(),
  test_end: z.string(),
  in_sample_return: z.string(),
  out_of_sample_return: z.string(),
  oos_sharpe: z.string().nullable(),
  num_trades_oos: z.number().int(),
});
export type WalkForwardFold = z.infer<typeof walkForwardFoldSchema>;

export const walkForwardResultSchema = z.object({
  folds: z.array(walkForwardFoldSchema),
  aggregate_oos_return: z.string(),
  degradation_ratio: z.string(), // "Infinity" possible
  valid_positive_regime: z.boolean(),
  total_possible_folds: z.number().int(),
  was_truncated: z.boolean(),
});
export type WalkForwardResult = z.infer<typeof walkForwardResultSchema>;

export const stressTestDetailSchema = z.object({
  id: z.string().uuid(),
  backtest_id: z.string().uuid(),
  kind: stressTestKindSchema,
  status: stressTestStatusSchema,
  params: z.record(z.string(), z.unknown()),
  result: z.union([monteCarloResultSchema, walkForwardResultSchema]).nullable(),
  error: z.string().nullable(),
  created_at: z.string(),
  started_at: z.string().nullable(),
  completed_at: z.string().nullable(),
});
export type StressTestDetail = z.infer<typeof stressTestDetailSchema>;

export const stressTestCreatedResponseSchema = z.object({
  stress_test_id: z.string().uuid(),
  kind: stressTestKindSchema,
  status: stressTestStatusSchema,
  created_at: z.string(),
});
export type StressTestCreatedResponse = z.infer<
  typeof stressTestCreatedResponseSchema
>;

// Request
export const createMonteCarloRequestSchema = z.object({
  backtest_id: z.string().uuid(),
  n_samples: z.number().int().min(100).max(2000).default(1000),
  seed: z.number().int().default(42),
});
export type CreateMonteCarloRequest = z.infer<
  typeof createMonteCarloRequestSchema
>;

export const createWalkForwardRequestSchema = z.object({
  backtest_id: z.string().uuid(),
  train_bars: z.number().int().min(10).max(10_000),
  test_bars: z.number().int().min(5).max(5_000),
  step_bars: z.number().int().min(1).max(5_000).nullable().optional(),
  max_folds: z.number().int().min(1).max(100).default(20),
});
export type CreateWalkForwardRequest = z.infer<
  typeof createWalkForwardRequestSchema
>;
```

> **참고:** 백엔드가 실제로 내려주는 JSON key 이름과 문자열 형식에 맞춰 final 하게 조정. 스키마 검증은 런타임에 실패하면 바로 발견됨.

### 2. `frontend/src/features/backtest/query-keys.ts` 확장

```typescript
// 기존 backtestKeys 옆에 추가
export const stressTestKeys = {
  all: (userId: string) => ["stress_test", userId] as const,
  detail: (userId: string, id: string) =>
    ["stress_test", userId, "detail", id] as const,
  byBacktest: (userId: string, backtestId: string) =>
    ["stress_test", userId, "by_backtest", backtestId] as const,
};
```

### 3. `frontend/src/features/backtest/api.ts` 확장

```typescript
import type { ApiFetcher } from "@/lib/api"; // 기존 패턴
import {
  type CreateMonteCarloRequest,
  type CreateWalkForwardRequest,
  type StressTestCreatedResponse,
  type StressTestDetail,
  stressTestCreatedResponseSchema,
  stressTestDetailSchema,
} from "./schemas";

export async function postMonteCarlo(
  fetcher: ApiFetcher,
  body: CreateMonteCarloRequest,
): Promise<StressTestCreatedResponse> {
  const res = await fetcher("/api/v1/stress-test/monte-carlo", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return stressTestCreatedResponseSchema.parse(await res.json());
}

export async function postWalkForward(
  fetcher: ApiFetcher,
  body: CreateWalkForwardRequest,
): Promise<StressTestCreatedResponse> {
  const res = await fetcher("/api/v1/stress-test/walk-forward", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return stressTestCreatedResponseSchema.parse(await res.json());
}

export async function getStressTest(
  fetcher: ApiFetcher,
  id: string,
): Promise<StressTestDetail> {
  const res = await fetcher(`/api/v1/stress-test/${id}`);
  return stressTestDetailSchema.parse(await res.json());
}
```

### 4. `frontend/src/features/backtest/hooks.ts` 확장

**LESSON-004 준수 — `refetchInterval` 은 dynamic 함수로, 터미널 상태에서 자동 stop.**

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useApiFetcher } from "@/lib/api-hooks";
import { useUserId } from "@/lib/auth"; // Clerk userId scalar
import { getStressTest, postMonteCarlo, postWalkForward } from "./api";
import { stressTestKeys, backtestKeys } from "./query-keys";
import type {
  CreateMonteCarloRequest,
  CreateWalkForwardRequest,
  StressTestDetail,
} from "./schemas";

export function useCreateMonteCarlo() {
  const fetcher = useApiFetcher();
  const qc = useQueryClient();
  const userId = useUserId() ?? "anon";
  return useMutation({
    mutationFn: (body: CreateMonteCarloRequest) =>
      postMonteCarlo(fetcher, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: stressTestKeys.all(userId) });
    },
  });
}

export function useCreateWalkForward() {
  const fetcher = useApiFetcher();
  const qc = useQueryClient();
  const userId = useUserId() ?? "anon";
  return useMutation({
    mutationFn: (body: CreateWalkForwardRequest) =>
      postWalkForward(fetcher, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: stressTestKeys.all(userId) });
    },
  });
}

export function useStressTest(id: string | null) {
  const fetcher = useApiFetcher();
  const userId = useUserId() ?? "anon";
  return useQuery({
    queryKey: id ? stressTestKeys.detail(userId, id) : ["stress_test", "noop"],
    queryFn: () =>
      id ? getStressTest(fetcher, id) : Promise.reject(new Error("no id")),
    enabled: !!id,
    // LESSON-004: refetchInterval dynamic + error 시 false — 무한 루프 방지
    refetchInterval: (query) => {
      const data = query.state.data as StressTestDetail | undefined;
      if (!data) return 2000; // 최초 poll
      if (data.status === "queued" || data.status === "running") return 2000;
      return false; // completed | failed → stop
    },
    refetchIntervalInBackground: false,
  });
}
```

### 5. `frontend/src/app/(dashboard)/backtests/_components/monte-carlo-fan-chart.tsx` (신규)

```tsx
"use client";

import { useMemo } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { MonteCarloResult } from "@/features/backtest/schemas";

interface Props {
  result: MonteCarloResult;
}

export function MonteCarloFanChart({ result }: Props) {
  const data = useMemo(() => {
    const p5 = result.equity_percentiles["5"] ?? [];
    const p25 = result.equity_percentiles["25"] ?? [];
    const p50 = result.equity_percentiles["50"] ?? [];
    const p75 = result.equity_percentiles["75"] ?? [];
    const p95 = result.equity_percentiles["95"] ?? [];
    return p50.map((_, i) => ({
      bar: i,
      // recharts stacked Area — ranges computed for fan effect.
      p5_to_p95_low: Number(p5[i]),
      p5_to_p95_range: Number(p95[i]) - Number(p5[i]),
      p25_to_p75_low: Number(p25[i]),
      p25_to_p75_range: Number(p75[i]) - Number(p25[i]),
      median: Number(p50[i]),
    }));
  }, [result]);

  return (
    <div className="w-full h-[320px]">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={data}
          margin={{ top: 10, right: 20, bottom: 10, left: 40 }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="bar"
            label={{ value: "Bar", position: "insideBottom", offset: -5 }}
          />
          <YAxis
            label={{ value: "Equity", angle: -90, position: "insideLeft" }}
          />
          <Tooltip />
          <Legend verticalAlign="top" />
          {/* Outer band p5~p95 */}
          <Area
            type="monotone"
            dataKey="p5_to_p95_low"
            stackId="outer"
            stroke="none"
            fill="transparent"
            name="_p5_base"
            legendType="none"
          />
          <Area
            type="monotone"
            dataKey="p5_to_p95_range"
            stackId="outer"
            stroke="none"
            fill="currentColor"
            fillOpacity={0.15}
            name="5%~95% 구간"
          />
          {/* Inner band p25~p75 */}
          <Area
            type="monotone"
            dataKey="p25_to_p75_low"
            stackId="inner"
            stroke="none"
            fill="transparent"
            name="_p25_base"
            legendType="none"
          />
          <Area
            type="monotone"
            dataKey="p25_to_p75_range"
            stackId="inner"
            stroke="none"
            fill="currentColor"
            fillOpacity={0.35}
            name="25%~75% 구간"
          />
          {/* Median line */}
          <Line
            type="monotone"
            dataKey="median"
            stroke="currentColor"
            strokeWidth={2}
            dot={false}
            name="중앙값"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
```

> **구현 주의:** recharts 의 `AreaChart` 는 stacked Area 로 fan 을 구현. 정확한 legend 처리는 본 구현을 맞춰 조정 필요. 최소 MVP: median line + 95% CI band 2개로 시작.

### 6. `frontend/src/app/(dashboard)/backtests/_components/walk-forward-bar-chart.tsx` (신규)

```tsx
"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { WalkForwardResult } from "@/features/backtest/schemas";

interface Props {
  result: WalkForwardResult;
}

export function WalkForwardBarChart({ result }: Props) {
  const data = result.folds.map((f) => ({
    fold: `fold ${f.fold_index + 1}`,
    IS: Number(f.in_sample_return) * 100,
    OOS: Number(f.out_of_sample_return) * 100,
  }));

  const degradationText = result.valid_positive_regime
    ? `Degradation ratio (IS/OOS): ${result.degradation_ratio}`
    : "Degradation ratio: N/A (손실 구간)";

  return (
    <div>
      <div className="mb-2 text-sm text-muted-foreground">
        {degradationText}
        {result.was_truncated &&
          ` · ${result.folds.length}/${result.total_possible_folds} folds shown`}
      </div>
      <div className="w-full h-[320px] overflow-x-auto">
        <div className="min-w-[600px] h-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="fold" />
              <YAxis
                label={{
                  value: "수익률 (%)",
                  angle: -90,
                  position: "insideLeft",
                }}
              />
              <Tooltip />
              <Legend />
              <Bar dataKey="IS" fill="#8884d8" name="In-sample" />
              <Bar dataKey="OOS" fill="#82ca9d" name="Out-of-sample" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
```

### 7. `frontend/src/app/(dashboard)/backtests/_components/stress-test-panel.tsx` (신규)

```tsx
"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  useCreateMonteCarlo,
  useCreateWalkForward,
  useStressTest,
} from "@/features/backtest/hooks";
import { MonteCarloFanChart } from "./monte-carlo-fan-chart";
import { WalkForwardBarChart } from "./walk-forward-bar-chart";

interface Props {
  backtestId: string;
}

export function StressTestPanel({ backtestId }: Props) {
  const [activeStressTestId, setActiveStressTestId] = useState<string | null>(
    null,
  );

  const mcMutation = useCreateMonteCarlo();
  const wfMutation = useCreateWalkForward();
  const { data: stressTest, isLoading } = useStressTest(activeStressTestId);

  async function handleRunMonteCarlo() {
    const result = await mcMutation.mutateAsync({
      backtest_id: backtestId,
      n_samples: 1000,
      seed: 42,
    });
    setActiveStressTestId(result.stress_test_id);
  }

  async function handleRunWalkForward() {
    const result = await wfMutation.mutateAsync({
      backtest_id: backtestId,
      train_bars: 500,
      test_bars: 100,
      step_bars: 100,
      max_folds: 20,
    });
    setActiveStressTestId(result.stress_test_id);
  }

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <Button onClick={handleRunMonteCarlo} disabled={mcMutation.isPending}>
          Monte Carlo 실행
        </Button>
        <Button
          variant="outline"
          onClick={handleRunWalkForward}
          disabled={wfMutation.isPending}
        >
          Walk-Forward 실행
        </Button>
      </div>

      {!activeStressTestId && (
        <p className="text-sm text-muted-foreground">
          위 버튼을 눌러 이 백테스트에 대한 스트레스 테스트를 실행하세요.
        </p>
      )}

      {activeStressTestId && (
        <div>
          {isLoading && <p className="text-sm">로딩 중...</p>}
          {stressTest?.status === "queued" && (
            <p className="text-sm">대기 중...</p>
          )}
          {stressTest?.status === "running" && (
            <p className="text-sm">실행 중...</p>
          )}
          {stressTest?.status === "failed" && (
            <p className="text-sm text-red-600">실패: {stressTest.error}</p>
          )}
          {stressTest?.status === "completed" &&
            stressTest.kind === "monte_carlo" &&
            stressTest.result && (
              <MonteCarloFanChart result={stressTest.result as any} />
            )}
          {stressTest?.status === "completed" &&
            stressTest.kind === "walk_forward" &&
            stressTest.result && (
              <WalkForwardBarChart result={stressTest.result as any} />
            )}
        </div>
      )}
    </div>
  );
}
```

### 8. `backtest-detail-view.tsx` 수정 (기존 파일)

기존 탭 목록에 `<TabsTrigger value="stress-test">스트레스 테스트</TabsTrigger>` 추가 + `<TabsContent value="stress-test">` 에 `<StressTestPanel backtestId={id} />` 렌더.

## Tests (vitest + jsdom)

- `frontend/src/app/(dashboard)/backtests/_components/__tests__/stress-test-panel.test.tsx` — 버튼 클릭 → mutation 호출 + activeStressTestId 설정
- `frontend/src/app/(dashboard)/backtests/_components/__tests__/monte-carlo-fan-chart.test.tsx` — 데이터 주입 → SVG 렌더 확인
- `frontend/src/app/(dashboard)/backtests/_components/__tests__/walk-forward-bar-chart.test.tsx` — `valid_positive_regime=false` 시 "N/A" 문구 확인 + truncation 메시지
- `frontend/src/features/backtest/__tests__/hooks.stress-test.test.ts` — `refetchInterval` 이 terminal status 에서 false 반환

## 검증 명령

```bash
cd frontend
pnpm tsc --noEmit  # TypeScript strict green
pnpm lint  # 0 errors
pnpm vitest run  # 신규 4 테스트 + 기존 전부 green
pnpm dev &  # dev server
# Chrome: localhost:3000/backtests/<id>
#   → "스트레스 테스트" 탭 클릭
#   → "Monte Carlo 실행" 버튼
#   → DevTools Performance: CPU idle (LESSON-004 smoke)
#   → fan chart 렌더
#   → polling 이 status=completed 후 멈추는지 네트워크 탭에서 확인
```

**LESSON-004 smoke 필수 (dev server 5분 이상).** `useEffect` 루프 의심 시 바로 수정.

## Golden Rules 체크리스트

- [ ] Zod v4 (`import { z } from "zod/v4"`)
- [ ] shadcn/ui `components/ui/` 직접 수정 금지
- [ ] TypeScript strict, `any` 사용 최소 (현재 SDD 에서 `result as any` 는 schema discriminated union 으로 교체 권장)
- [ ] Tailwind 페이지 고정 너비 금지 (`max-w-*` OK)
- [ ] **H-1: `useEffect` dep 에 React Query `data` 객체 직접 금지** — 본 SDD 는 `refetchInterval` 함수만 사용
- [ ] **H-2: queryKey 에 `getToken` 직접 금지** — userId 스칼라만
- [ ] **H-3: render body 에서 `ref.current = x` 금지** — 해당 없음
- [ ] `react-hooks/exhaustive-deps` disable 절대 금지

## 커밋

```
c1 feat(frontend-bt): stress-test tab — MC fan chart + WFA bar chart (Phase C)

- features/backtest: api/hooks/schemas/query-keys 확장 (stress_test)
- app/(dashboard)/backtests/_components:
  - stress-test-panel.tsx (탭 컨테이너 + 실행 버튼 + polling 상태)
  - monte-carlo-fan-chart.tsx (recharts Area p5~p95 fan + median)
  - walk-forward-bar-chart.tsx (IS vs OOS bar + degradation + truncation 표시)
  - backtest-detail-view.tsx (5번째 탭 추가)
- LESSON-004 준수: refetchInterval dynamic + terminal status stop
- vitest 4 신규 (panel, MC chart, WFA chart, hooks refetchInterval)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

## Agent 출력 JSON

```json
{
  "branch": "feat/h2s9-frontend-mcwfa",
  "commits": ["<sha>"],
  "files_added": ["..."],
  "files_modified": ["..."],
  "tests_added": 4,
  "tests_total_after_frontend": <int>,
  "lint_clean": true,
  "tsc_noEmit_clean": true,
  "dev_server_smoke_verified": true,
  "issues": ["..."],
  "ready_for_evaluator": true
}
```

## 리스크

| 리스크                                       | 대응                                                                                                                     |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| recharts stacked Area 로 fan chart 구현 복잡 | MVP 로 median line + p5~p95 single band 먼저. 욕심 금지.                                                                 |
| `result as any` 타입 캐스팅                  | schemas.ts 의 discriminated union 으로 교체. MC/WFA 구분을 `kind` 로.                                                    |
| Polling 무한 루프                            | `refetchInterval: (query) => ...` 함수 형태 사용. `useEffect` dep 에 `data` 절대 금지. dev smoke 필수.                   |
| JSON Infinity 파싱                           | `degradation_ratio` 는 항상 string. `"Infinity"` 리터럴은 `valid_positive_regime=false` 와 짝지어 UI 에서 "N/A" 로 표시. |
