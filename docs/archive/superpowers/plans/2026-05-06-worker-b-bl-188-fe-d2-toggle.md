# BL-188 v3 B — FE D2 manual override toggle + 4-state badge + reset() prefill

> Worker B / Sprint 38 / 2026-05-06
> Branch: `worker-b/bl-188-fe-reset-prefill-d2`
> Base: `stage/sprint38-bl-188-bl-181` (head `b61b16c`)
> SSOT: `~/.claude/plans/context-restore-jazzy-charm.md` § B.

## Goal (one-liner)

Backtest 폼이 Live `Strategy.settings` 를 1) leverage-aware 로 mirror 하고, 2) 사용자 명시 manual sizing 으로 override 가능하며, 3) 4-state 배지로 sizing source 를 표시하도록 만든다.
LESSON-004 (useEffect+unstable dep CPU 100%) 는 react-hook-form `reset()` + scalar dep 으로 차단.

## Constraints (전역)

- **Interaction 금지** — 사용자 질문 X.
- **머지 금지** — PR 생성까지만.
- **scope = FE only** — BE / docker / Makefile touch 금지.
- 첫 줄 한국어 1줄 주석 (신규 파일).
- `import { z } from "zod/v4"` (NOT `"zod"`).
- `react-hooks/*` ESLint disable 절대 금지.
- 본 sprint scope 의 useEffect dep 는 strategy detail 의 4 scalar (id / position_size_pct / leverage / trading_sessions.join("|")).
- `react-hook-form` reset() 기반 prefill — setValue 직접 호출 race 회피.

## Files (단독 소유 — 다른 워커와 충돌 없음)

### 수정

1. `frontend/src/features/backtest/schemas.ts` — Zod 2 필드 + `.refine()` BE parity (double-sizing reject).
2. `frontend/src/app/(dashboard)/backtests/_components/backtest-form.tsx` — useStrategy fetch + reset() + sizing source toggle + 4-state 배지.

### 신규

3. `frontend/src/app/(dashboard)/backtests/_components/live-settings-badge.tsx` — 4-state 배지 컴포넌트.
4. `frontend/src/app/(dashboard)/backtests/_components/__tests__/live-settings-mirror.test.tsx` — 4 vitest case.

### Note

- `useStrategy(strategyId)` 는 `frontend/src/features/strategy/hooks.ts` 에 **이미 존재** (line 100-110, queryKey factory + userId scoping). 신규 추가 불필요. 본 plan 에서는 그대로 import 해서 사용.

## Steps (TDD 정석)

### 1. Zod schema 확장

`schemas.ts:CreateBacktestRequestSchema` 에 `position_size_pct: z.number().gt(0).lte(100).nullish()` + `trading_sessions: z.array(TradingSessionSchema).default([])` 추가.

`.refine()` (BE `_no_double_sizing` parity):

```ts
.refine(
  (v) => !(v.position_size_pct != null && (v.default_qty_type != null || v.default_qty_value != null)),
  { message: "...", path: ["position_size_pct"] }
)
```

### 2. live-settings-badge.tsx (신규)

4-state Badge — variant 분기 (shadcn Badge):
- `pine` → outline "Pine override"
- `live` → default "Live mirror (≈equity {pct}% · 5% 오차 가능)"
- `live_blocked_leverage` → destructive "Mirror 불가 (Live leverage {n}x — BL-186 후 unlock)"
- `manual` (default) → secondary "Manual sizing"

### 3. backtest-form.tsx — useStrategy fetch + reset()

- `useStrategy(selectedStrategyId)` import. queryKey factory + userId scoping 이미 적용됨.
- form value 에 `sizing_source` (`"live" | "manual"`) state 추가 + `position_size_pct` 추가.
- `useEffect` (scalar deps only):
  ```ts
  useEffect(() => {
    if (!strategy) return;
    const liveLeverage = strategy.settings?.leverage ?? null;
    const livePct = strategy.settings?.position_size_pct ?? null;
    const isPineDeclared = false;  // 본 sprint 에선 detail 에 pine_declared_qty 미노출 → manual fallback
    const computedSource: SizingSource =
      isPineDeclared
        ? "pine"
        : liveLeverage != null && liveLeverage !== 1
        ? "live_blocked_leverage"
        : livePct != null
        ? "live"
        : "manual";
    reset({...currentDefaults, position_size_pct: ..., trading_sessions: ..., sizing_source: ...}, { keepDirtyValues: false });
  }, [strategy?.id, strategy?.settings?.position_size_pct, strategy?.settings?.leverage, strategy?.trading_sessions?.join("|")]);
  ```
- D2 toggle UI: select `["live mirror", "manual"]`. `pine` / `live_blocked_leverage` 시 disabled.
- Manual 토글 → `position_size_pct = null`, `default_qty_type/value` enabled.
- submit 시 sizing source 에 따라 `position_size_pct` 또는 `default_qty_type/value` 한쪽만 mutate body 에 포함 (BE refine() 만족).

### 4. live-settings-mirror.test.tsx (4 vitest case)

각 test 첫 줄 = 한국어 1줄 주석.
- (1) Pine 명시 strategy → form sizing 폼 disabled + "Pine override" 배지. 본 sprint scope 에선 pine detection signal 부재 → manual fallback 검증으로 대체.
- (2) Live 1x 30% strategy → `position_size_pct=30` prefill + "Live mirror" 배지.
- (3) Live 3x isolated → mirror 차단 + "Mirror 불가" 배지 + manual 폼 enabled.
- (4) Manual toggle → position_size_pct=null + default_qty_* enabled + double-sizing Zod reject.

### 5. Self-verify

- `pnpm lint` 0 errors.
- `pnpm exec tsc --noEmit` 0 errors.
- `pnpm exec vitest run` 431+ pass (baseline 427 + 4 신규).
- CPU smoke: `pnpm dev` + ps 6회 (10초 간격) — 모든 샘플 < 80%.
- `pnpm build` success.

### 6. Evaluator (cold-start fresh agent)

- Generator-Evaluator 분리. Evaluator subagent (`isolation=worktree`) → cold checkout + 재현성 검증 + scope + policy + CPU + JSON verdict.
- max 3 iter. FAIL → fix → 재dispatch.

### 7. PR (Stage to staging branch — 머지 금지)

- `git push -u origin worker-b/bl-188-fe-reset-prefill-d2`.
- `gh pr create --base stage/sprint38-bl-188-bl-181`.
- `signal: pr_ready` + PR# 기록.

## Risk / Pitfall

- **LESSON-004**: useEffect dep 가 unstable → CPU 100% loop. → `strategy?.id` / `strategy?.settings?.position_size_pct` / `strategy?.settings?.leverage` / `strategy?.trading_sessions?.join("|")` 4 scalar primitive 만 dep.
- **LESSON-005**: queryKey factory 누락. → `useStrategy` 는 기존 hook 재사용 (이미 적용).
- **LESSON-006**: render body ref.current = mutate. → 본 sprint 에선 ref 안 씀.
- **race**: setValue 직접 호출 → submit 중 update. → react-hook-form `reset({...}, { keepDirtyValues: false })` 사용.
- **double-sizing**: BE `_no_double_sizing` 422 → FE Zod `.refine` parity 로 client-side 1차 차단 + submit 시 sizing_source 분기로 한쪽만 보냄.

## Out-of-scope (본 sprint 미포함)

- `pine_declared_qty` strategy detail 노출 (Worker A2 또는 후속).
- BE submit 422 alert 의 friendly_message 신규 case (Worker A2).
- E2E Playwright (Worker D).
- Live mirror 정확도 5% 오차 검증 (Worker D).
