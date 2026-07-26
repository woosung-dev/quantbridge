# Sprint FE-04 — Backtest UI MVP

## 배경

- BE API는 Sprint 4에서 완성됨: `backend/src/backtest/router.py` — 7 endpoints.
  - `POST /api/v1/backtests` · `GET /api/v1/backtests` · `GET /:id` · `GET /:id/trades` · `GET /:id/progress` · `POST /:id/cancel` · `DELETE /:id`
- **중요**: BE 응답의 Decimal 필드 (metrics, equity, trade pnl 등)는 `@field_serializer`로 **JSON 문자열** 로 직렬화됨 (worker 프롬프트 가정은 "number"였으나 실제 코드는 str). → Zod 스키마에서 `z.string().transform()` + `Number.isFinite` 검증 필요.
- 기존 패턴은 Sprint FE-02 strategy feature (`frontend/src/features/strategy/`)가 정답. userId factory + `makeXxxFetcher` CallExpression queryFn.

## Scope (SSOT baseline 그대로)

### 화면 4개
1. `/backtests/new` — form (strategy/symbol/timeframe/date/capital) → POST
2. `/backtests/[id]` — 30s polling 상태 머신 (pending/running → completed/error)
3. `/backtests/[id]` — Completed 시 metrics 4카드 + equity chart + trade table
4. `/backtests` — 목록 (최근 20, row 클릭 → detail)

### 기술 fix
- 차트: **recharts** (already `pnpm add` 완료)
- Polling: 30s, error 시 false
- Equity 다운샘플: 1000 pt 상한
- Trade 상한: 200 row (페이지네이션 없음)
- Schema: Zod `frontend/src/features/backtest/schemas.ts`

## 단계별 구현 (8~12 commits 예상)

### Phase 1 — feature 모듈 (TDD)
**Commit 1** · query-keys + tests
- `features/backtest/query-keys.ts`: `backtestKeys.all(uid)`, `lists(uid)`, `list(uid, query)`, `details(uid)`, `detail(uid, id)`, `progress(uid, id)`, `trades(uid, id, query)`
- `__tests__/query-keys.test.ts`: userId identity, different user → different keys (strategy 패턴 복제)

**Commit 2** · schemas (Zod) + tests
- Decimal→number transform: `z.string().transform((s) => { const n = parseFloat(s); if (!Number.isFinite(n)) throw new Error("non-finite"); return n; })`
- `BacktestStatusSchema` = enum `queued|running|cancelling|completed|failed|cancelled`
- `CreateBacktestRequestSchema` — UUID strategy_id, symbol(3-32), timeframe enum, period_start/end ISO, initial_capital(gt 0) — 숫자를 body로 보낼 때는 number로 보냄 (BE Decimal 파싱). 응답만 str→number 처리.
- `BacktestSummarySchema`, `BacktestDetailSchema` (metrics, equity_curve nullable), `TradeItemSchema` (return_pct str→number)
- `ProgressResponseSchema`, `CreatedResponseSchema`, `CancelResponseSchema`
- Pagination `PageSchema<T>` — `items/total/limit/offset/has_more` (common.pagination 참조)
- `__tests__/schemas.test.ts`: str→number finite 검증 / invalid NaN reject / equity_curve 샘플 parse

**Commit 3** · api.ts (apiFetch 래퍼)
- `listBacktests({limit, offset}, token)`, `getBacktest(id, token)`, `createBacktest(body, token)`, `getProgress(id, token)`, `listTrades(id, {limit, offset}, token)`, `cancelBacktest(id, token)`, `deleteBacktest(id, token)`
- 모든 response는 Zod parse
- 테스트 없음 (hooks 테스트가 integration 커버)

**Commit 4** · hooks.ts — userId factory 패턴
- `useBacktests(query)` — useQuery, `backtestKeys.list(uid, query)`
- `useBacktest(id)` — useQuery, detail
- `useBacktestProgress(id)` — useQuery with `refetchInterval: (q) => q.state.status === 'error' ? false : 30_000`
- `useBacktestTrades(id, {limit, offset})` — useQuery, enabled = completed
- `useCreateBacktest(opts)` — useMutation, invalidate lists
- `useCancelBacktest(opts)`, `useDeleteBacktest(opts)` — useMutation
- 모든 queryFn은 module-level `makeXxxFetcher` (strategy 패턴)
- `__tests__/hooks-factory.test.ts` — fetcher factory identity (token getter가 closure에 있지만 queryFn은 CallExpression)

**Commit 5** · downsample utility + tests
- `utils.ts` — `downsampleEquity(points: EquityPoint[], max: number = 1000): EquityPoint[]`
  - n ≤ max → 원본 그대로
  - else → 등간격 sampling (index = floor(i * n / max))
- `__tests__/downsample.test.ts` — 2000pt → 1000pt, 첫/끝 포인트 보존, 500pt → 500pt

### Phase 2 — 페이지 + 컴포넌트
**Commit 6** · `/backtests/new` page + backtest-form
- `app/(dashboard)/backtests/new/page.tsx` — client component (form state)
- `_components/backtest-form.tsx` — react-hook-form + zod resolver
  - Fields: strategy_id (select — useStrategies으로 로드), symbol, timeframe, period_start, period_end, initial_capital
  - submit → useCreateBacktest → onSuccess: router.push(`/backtests/${id}`)
  - validation: period_end > period_start, capital > 0

**Commit 7** · `/backtests/[id]` page + status-badge + metrics-cards + equity-chart + trade-table
- `app/(dashboard)/backtests/[id]/page.tsx` — client (polling)
  - `useBacktest(id)` + `useBacktestProgress(id)` (polling)
  - status별 렌더: pending/running → loading card, completed → metrics + chart + trades, failed → error card + retry button (refetch)
  - cancelled → cancelled message
- `_components/status-badge.tsx` — 상태별 색상 badge (shadcn Badge variant)
- `_components/metrics-cards.tsx` — 4 cards (total_return, sharpe, mdd, win_rate)
- `_components/equity-chart.tsx` — recharts `LineChart` + ResponsiveContainer, x=timestamp (YYYY-MM-DD), y=equity, 다운샘플 후 렌더
- `_components/trade-table.tsx` — 단순 table (shadcn table 없음 → div grid) 상한 200. useBacktestTrades(id, { limit: 200, offset: 0 })

**Commit 8** · `/backtests` 목록 page
- `app/(dashboard)/backtests/page.tsx` — RSC + HydrationBoundary prefetch (20건)
- `_components/backtest-list.tsx` — Table view, row click → `/backtests/[id]`

### Phase 3 — 통합 + 테스트 보강
**Commit 9** · form validation unit test
- `__tests__/backtest-form-schema.test.ts` — period order, capital gt 0

**Commit 10** · status state machine test
- `__tests__/status-badge.test.ts` — 상태 → label/variant mapping

**Commit 11** · cleanup / lint fix / tsc

## 엄수 체크리스트

- [x] `backtestKeys.list(userId)` — userId 첫 인자
- [x] `queryFn: makeListFetcher(query, getToken)` — 모듈-level CallExpression
- [x] `refetchInterval: (q) => q.state.status === 'error' ? false : 30_000`
- [x] `any` 금지 — Zod inferred types
- [x] `Number.isFinite` 가드 (transform 시)
- [x] equity 다운샘플 1000pt 상한
- [x] trade 200 row 상한
- [x] recharts only (no other chart lib)
- [x] LESSON-004: react-hooks disable 금지
- [x] LESSON-006: ref sync effect 필요 시
- [x] LESSON-007: dev smoke 후 process 정리

## MVP out of scope (명시적 제외)

- WebSocket 실시간 진행률
- Infinite scroll (trade / list)
- 최적화 뷰 (equity drill-down, candlestick, indicator overlay)
- 비교 뷰 (multi-backtest overlay)

## 테스트 인벤토리 (최소)

1. query-keys unit (userId factory)
2. schemas str→number transform
3. schemas invalid (NaN reject)
4. downsample utility (3 cases)
5. hooks factory (fetcher CallExpression identity)
6. backtest-form schema validation
7. status-badge label mapping

총 7개 이상 추가 → 기존 53개 → 60+ 예상.

## 위험 + 완화

- **Celery 미가동 상태에서 실행 테스트**: integration test는 mock. Live smoke는 form submit만 확인, BE가 202 반환하면 OK. 실제 completed 상태 UI는 mocked fixture로 테스트.
- **BE Decimal str 응답**: Zod transform으로 명시적 파싱. worker 프롬프트 문구 ("number 직렬화")를 따르지 않고 실제 코드 (`field_serializer → str`) 따름.
- **recharts SSR**: Next.js dynamic import로 client-only 보장.
- **Clerk build 실패 시**: env.local 이미 복사됨. 실패 시 PR body에 명시.

## 완료 기준

- `pnpm lint` 0 errors 0 warnings
- `pnpm tsc --noEmit` clean
- `pnpm test -- --run` all green
- `pnpm build` 로컬 성공
- Live smoke: `/backtests/new` + `/backtests/<id>` navigate, CPU < 80%, console error 0
- Evaluator PASS
