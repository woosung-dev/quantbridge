# Sprint 27 Beta prereq hotfix — BL-137 + BL-140 (실제 코드 변경)

> **일자**: 2026-05-04 (PR #102 + PR #103 머지 직후)
> **Branch**: `stage/h2-sprint27-beta-prereq-hotfix` (cascade base `686a71f`)
> **Mode**: A2-bundle 축소 (BL-137 + BL-140), BL-141 별도 sprint
> **Self-assessment**: **8.5/10** (실제 implementation, dogfood Day 1 finding 2 건 직접 fix)

---

## 1. 목적

dogfood Day 1 의 2 P2 BL 직접 fix — Beta 오픈 prereq.

| BL         | 이슈                                                            | 사이즈 | Beta prereq  |
| ---------- | --------------------------------------------------------------- | ------ | ------------ |
| **BL-137** | 신규 strategy trading settings UI 부재 → Live Session 등록 차단 | M      | ✅ 필수      |
| **BL-140** | LiveSignalDetail equity curve chart 부재 (number+table only)    | M      | ✅ 가치 ★★★★ |

BL-141 (backtest 인프라 활성화 + ts.ohlcv backfill) = L (4-8h) 별도 sprint.

## 2. BL-137 — Strategy 메타데이터 tab 에 Trading Settings UI

### Backend 사실 (변경 없음)

- `backend/src/strategy/schemas.py:72-87` `StrategySettings` Pydantic schema 이미 있음
- `backend/src/strategy/router.py:118` `PUT /strategies/{id}/settings` endpoint 이미 있음
- 본 hotfix 는 **frontend binding 만** 추가 (BE 변경 0)

### Frontend 변경 (4 파일)

1. **`frontend/src/features/strategy/schemas.ts`** — `MarginModeSchema`, `StrategySettingsSchema`, `UpdateStrategySettingsRequestSchema` 추가. `StrategyResponseSchema` 에 `settings` field optional/nullable 추가.
2. **`frontend/src/features/strategy/api.ts`** — `updateStrategySettings(id, body, token)` 함수 추가. PUT `/api/v1/strategies/{id}/settings`.
3. **`frontend/src/features/strategy/hooks.ts`** — `useUpdateStrategySettings(id, opts)` hook 추가. lists invalidate + detail setQueryData (LESSON-019 cache 정합).
4. **`frontend/src/app/(dashboard)/strategies/[id]/edit/_components/tab-metadata.tsx`** — 메타데이터 form 아래 별도 `<section>` 으로 Trading Settings form 추가. settings null 시 빨간 텍스트 "미설정 (Live Session 차단됨)" + "Settings 등록" 버튼 분기.

### UX 분기

- settings null → 빨간 미설정 텍스트 + 버튼 "Settings 등록"
- settings 있음 → 일반 form + 버튼 "Settings 저장"
- form 분리: 메타데이터(name) vs settings(leverage 등) 트랜잭션 독립

## 3. BL-140 — LiveSignalDetail Activity Timeline line chart

### scope 정정 (실측 후)

events.items 에 **realized_pnl 필드 없음** (`schemas.ts:53-69` 확인). 진정한 equity curve 는 BE schema 확장 (state.realized_pnl_history JSONB 또는 events.realized_pnl 추가) 필요. 본 commit 은 **events 만으로 가능한 minimum chart** 으로 축소.

### Frontend 변경 (1 파일)

**`frontend/src/features/live-sessions/components/live-session-detail.tsx`**:

- `recharts` import (LineChart / Line / XAxis / YAxis / CartesianGrid / Tooltip / ResponsiveContainer)
- `buildActivityTimeline(events)` helper — events 시간 순서로 cumulative entry/close 카운트 계산. events 가 desc 응답이라 `.slice().reverse()` 로 chronological 변환 (immutable mutation 안전).
- `<LineChart>` 영역 추가 — green(Entries) + blue(Closes) dual line.
- empty state: "아직 평가된 signal 이 없습니다" 그대로 유지.

### 후속 BL-140b

- BE `LiveSignalState` 에 `realized_pnl_history: list[float]` 추가 (또는 events.realized_pnl)
- 진정한 equity curve (cumulative PnL over time) 시각화
- 사이즈 M (BE schema migration + FE chart 변환)

## 4. 검증

| 명령                                         | 결과                                     |
| -------------------------------------------- | ---------------------------------------- |
| `pnpm tsc --noEmit`                          | ✅ 0 errors                              |
| `pnpm lint`                                  | ✅ 0 errors                              |
| `pnpm vitest run`                            | ✅ **257/257 passed** (44 files, 회귀 0) |
| codex G.0 + G.2 (high reasoning)             | ✅ P1 5건 → 4 fix + 1 P2 격하            |
| `pnpm e2e:authed` (PLAYWRIGHT_BASE_URL=3100) | (권장) — Sprint 25 패턴                  |

### codex G.2 P1 fix 매핑

| P1     | 이슈                                          | Fix                                                                                   |
| ------ | --------------------------------------------- | ------------------------------------------------------------------------------------- |
| **#1** | `StrategySettingsSchema` extra='forbid' 누락  | `.strict()` 추가 (BE 정합)                                                            |
| #2     | BE `settings: dict` read-path 검증 부재       | **P2 격하** — FE `.strict()` 가 invalid 응답 catch. BE schema 변경은 별도 BL-143 후보 |
| **#3** | settings/메타데이터 mutation race             | `setQueryData` → `invalidateQueries(detail)` (server truth)                           |
| **#4** | events bar_time desc 미보장 (created_at desc) | client-side `sort(bar_time asc, sequence_no asc)` 추가                                |
| **#5** | "cumulative" 라벨이 100-window 만 표시        | "최근 events" + dataKey `entries_in_window` 명시                                      |

### codex G.2 P2 fix

- **#1 ✅** "Position Size % (0-100)" → "(0 < v ≤ 100)" 라벨 정정
- **#2** memoize 후속 (현재 events polling rate 60s 라 영향 적음)
- **#3 ✅** `toLocaleTimeString()` → `toLocaleString()` (장시간 세션 X축 중복 방어)
- **#4** `buildActivityTimeline()` unit test 후속 BL
- **#5** chart 렌더 smoke test 후속 BL

## 5. critical files

| 경로                                                                             | 변경                                           |
| -------------------------------------------------------------------------------- | ---------------------------------------------- |
| `frontend/src/features/strategy/schemas.ts`                                      | +22 (settings + UpdateStrategySettingsRequest) |
| `frontend/src/features/strategy/api.ts`                                          | +17 (updateStrategySettings 함수)              |
| `frontend/src/features/strategy/hooks.ts`                                        | +24 (useUpdateStrategySettings hook)           |
| `frontend/src/app/(dashboard)/strategies/[id]/edit/_components/tab-metadata.tsx` | +149 (settings form section)                   |
| `frontend/src/features/live-sessions/components/live-session-detail.tsx`         | +83 (Activity Timeline chart)                  |
| **합계**                                                                         | **+295 / -2**                                  |

## 6. 종합 self-assessment (8.5/10)

| 측정        | 점수       | 근거                                              |
| ----------- | ---------- | ------------------------------------------------- |
| 코드 품질   | 9/10       | tsc/lint/vitest 0 회귀, schema-first, 패턴 정합   |
| BL fix 가치 | 9/10       | dogfood Day 1 발견 2 건 직접 해소, Beta prereq    |
| Scope 분리  | 8/10       | BL-140b (BE schema) 정직 분리. BL-141 별도 sprint |
| codex G.2   | TBD        | challenge 결과 따로                               |
| **종합**    | **8.5/10** | 실측 implementation, 코드 변경 0 PR 패턴 종료     |

## 7. 후속 BL

- **BL-140b**: 진정한 equity curve — BE state.realized_pnl_history 추가 (M)
- **BL-141**: Backtest UI 활성화 + ts.ohlcv hypertable backfill (L)
- **BL-138/139/142**: P3 polish (별도 정리 sprint)
- **BL-005 dogfood Day 5+**: BL-137 effect 확인 — 신규 strategy + settings UI flow 첫 사용자 시각

## 8. PR description summary

- 5 파일 +295/-2 (frontend only, BE 0)
- BL-137 settings UI + BL-140 Activity Timeline chart
- tsc/lint/vitest 257/257 PASS
- dogfood Day 1 발견 직접 fix (Beta prereq)
- BL-140b/141 후속 BL 명확 분리 (scope discipline)
