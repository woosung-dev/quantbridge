# dogfood Day 1 — Sprint 27 launch (Auto-Loop §0.5 first run)

> **일자**: 2026-05-04 (Sprint 26 PR #100 머지 직후)
> **Branch**: `stage/h2-sprint27-dogfood-day1` (cascade base `01481ea`)
> **Mode**: Auto-Loop `DOGFOOD_OPTION=A` — 무중단 자동 dogfood Day 1+ continuation
> **Self-assessment**: **8/10**
> **참조**: `~/.claude/plans/h2-sprint-27-or-dogfood-day1-resume.md` §0.5 / §3 / `~/.claude/plans/h2-sprint-27-wiggly-snail.md`

---

## 1. 목적과 결과 요약

Sprint 26 PR #100 머지 후 첫 dogfood 세션. ralph-loop 패턴(Auto-Loop §0.5) 첫 실측. 사용자 explicit pre-authorization 으로 PR 작성까지 무중단 자동 진행.

| 단계                  | 산출                                                                      |
| --------------------- | ------------------------------------------------------------------------- |
| A.0 stage 분기        | `stage/h2-sprint27-dogfood-day1` ✅                                       |
| A.1 strategy 2건 등록 | PbR `947bc980...` + UtBot `0347907e...` ✅                                |
| A.2 settings 주입     | DB UPDATE 우회 (UI 부재 — Day 1 Finding #1)                               |
| A.3 LiveSession 2건   | PbR(5m) `b03e486f...` + UtBot(15m) `f477730f...` ✅                       |
| A.4 dispatch 검증     | Beat `due_count` 1→3 즉시 인식, evaluate 정상, no_new_bar skip 정상 ✅    |
| A.5 UI + CPU smoke    | LiveSessionDetail 표시 OK, Long Task 0건 / FPS 120 / blocked main 0.0% ✅ |
| A.6 dev-log + PR      | 본 문서 + commit + push + PR ✅                                           |

---

## 2. dogfood Day 1 Findings (3 + 1 LESSON)

### Finding #1 (BL-137 후보) — 신규 strategy trading settings UI 부재

- **재현**: `/strategies/<new-id>/edit` 메타데이터 tab 에 leverage / margin_mode / position_size_pct 입력 폼 없음.
- **결과**: LiveSession 등록 시 strategy combobox 가 "전략 선택 (settings 필요)" 으로 reset → session 시작 불가.
- **API 는 존재**: `PUT /api/v1/strategies/{id}/settings` (`backend/src/strategy/router.py:118`). UI binding 만 누락.
- **우회**: DB 직접 UPDATE 로 `{leverage:2, margin_mode:cross, position_size_pct:10.0, schema_version:1}` 주입. Sprint 26 dogfood Day 0 strategy 의 settings 와 동일 값.
- **권장 사이즈**: M (메타데이터 tab 에 settings section 추가, RHF + Zod schema 활용)

### Finding #2 (BL-138 후보) — Live Sessions list "BTC/USDT5m" 공백 누락

- **재현**: `/trading?tab=live-sessions` list 에 "BTC/USDT5m · created..." 표기. symbol 과 interval 사이 `·` 분리자 누락.
- **위치**: `frontend/src/features/live-sessions/` 의 list rendering. detail 영역은 "5m · last evaluated:" 처럼 정상.
- **권장 사이즈**: XS (1 line text fix)

### Finding #3 (BL-139 후보) — LiveSessionDetail "Closed Trades / Realized PnL" 집계 범위

- **재현**: 새로 만든 PbR 세션 (`b03e486f...`, 0 events) 클릭 시 Closed Trades 32 / Realized PnL -546.42 USDT 표시. 같은 user + symbol 의 다른 세션 누적값으로 보임.
- **확인 필요**: BE 의 detail aggregation 쿼리 가 session_id 로 scope 됐는지, 또는 user/symbol 로 broadened. session-level 집계 의도이면 raw_filter 더 좁힐지 product decision.
- **권장 사이즈**: S (BE query 검사 + spec 결정)

### LESSON L-S27-1 — schema 조회 시 multi-schema 인지 의무 (L-S25-1 후속)

- **상황**: 첫 sanity 단계에서 `\dt` 로 trading 테이블 누락 보고 사용자에게 "schema corruption" 으로 destructive recovery escalate.
- **실제**: trading 테이블은 `trading.*` schema, ohlcv 는 `ts.*`. `\dt` 의 default = public schema 만. `pg_tables` 전체 조회 또는 `\dt *.*` 로 검증 의무.
- **승격 후보**: `.ai/common/global.md` "DB 점검 의무" 항목 — multi-schema 프로젝트는 항상 `pg_tables WHERE schemaname IN (...)` 또는 `\dt *.*` 사용.
- **L-S25-1 (plan fixture 가설 → 코드 실측 의무)** 의 구체 사례: schema 결정 전 `select schemaname from pg_tables` 실측 후 가정 수립. 자가 정정 후 사용자에게 "false alarm" 으로 정정 보고.

---

## 3. dispatch 검증 evidence (Beat scheduler)

```
2026-05-03 23:51:47.239 evaluate-live-signals received
2026-05-03 23:52:06.627 evaluate_all succeeded due_count=3 (results 3건):
  - dogfood-smoke (5b43ba6a): events_inserted=1 last_bar=23:50:00
  - PbR (b03e486f):           events_inserted=0 last_bar=23:45:00
  - UtBot (f477730f):         events_inserted=0 last_bar=23:30:00

2026-05-03 23:52:47.249 evaluate-live-signals received
2026-05-03 23:52:48.501 evaluate_all succeeded due_count=3 (results 3건):
  - dogfood-smoke: events_inserted=1 last_bar=23:51:00
  - PbR:   skipped no_new_bar
  - UtBot: skipped no_new_bar

2026-05-03 23:51:47.776 dispatch_event 3fca3466... succeeded (replayed=False)
2026-05-03 23:52:47.818 dispatch_event 1977bcc1... succeeded (replayed=False)
```

DB row 변화 (90s window):

```
total_orders 468 → 470 (+2 dispatch + Bybit Demo fill)
total_events 468 → 470
active_sessions 1 → 3 (Beat scan 즉시 인식)
```

- ✅ 새 세션 2건 모두 next evaluate cycle 에 자동 picked up
- ✅ no_new_bar skip 정상 (5m/15m boundary 미도래)
- ✅ 기존 1m 세션 90s 동안 +2 filled orders (Bybit Demo)
- ✅ Pine 신호 미발생 정상 (PbR pivot reversal 은 swing high/low 시 발생, UtBot 도 trend transition 시)

---

## 4. CPU smoke (LESSON-004 검증)

`/trading?tab=live-sessions` 라이브 + LiveSessionDetail polling active 상태에서 60s rAF + Long Task API 측정:

| 지표                | 값    | LESSON-004 한도 | 비고                           |
| ------------------- | ----- | --------------- | ------------------------------ |
| FPS                 | 120.0 | n/a             | ProMotion 120Hz 디스플레이     |
| Long Task 개수      | 0     | n/a             | 50ms 이상 main thread 차단 0건 |
| blocked main thread | 0.0%  | < 30% (p50)     | 압도적 양호                    |
| longest task        | 0ms   | n/a             |                                |

Sprint 26 PR #100 머지 후 회귀 0건. LESSON-004 가 다룬 useEffect/Tanstack Query/RHF/Zod 무한 루프 패턴 재발 0.

---

## 5. BL-122 fix UI 효과 검증 (Sprint 26 회고 후속)

- ✅ 4개 strategy 모두 dropdown 에 **name** 으로 표시 (UUID 노출 0)
- ✅ 새로 등록한 Sprint 27 strategy 2건도 즉시 list 갱신 (cache invalidate)
- ✅ "전략 선택 (settings 필요)" placeholder 도 표시 (Finding #1 와 별개로 BL-122 자체는 정상)
- ⚠️ settings null 인 새 strategy 가 dropdown 에서 disabled 안 됨 → 선택 시 form value reset (UX gap, BL 후보)

---

## 6. evidence files

- `sprint27-day1-live-session-detail.png` (project root) — LiveSessionDetail UI + 3 sessions
- `sprint27-day1-live-sessions-list.png` (project root) — Live Sessions list

---

## 7. 다음 분기

| 옵션                                | 작업                                         | 별점  | trigger                                |
| ----------------------------------- | -------------------------------------------- | ----- | -------------------------------------- |
| **A1. dogfood Day 2-7 자연 사용**   | 매일 1-2회 진입, BL-005 (1-2주 dogfood) 완수 | ★★★★★ | self-assessment 8/10, 자연 시간 필요   |
| A2. BL-137/138/139 hotfix 별도 PR   | 본 PR 머지 후 Day 1 finding 3건 처리         | ★★★★☆ | scope 작음, ~2-4h                      |
| B. Sprint 27 Path A — Beta 오픈     | BL-070~075 (도메인/DNS/Resend/캠페인)        | ★★★☆☆ | dogfood Day 3+ 결과 보고 결정          |
| C. Sprint 27 Path B — G.2 hardening | BL-134/135/136 (real-DB integration)         | ★★☆☆☆ | production blocker 0건이라 우선도 낮음 |

**추천**: A1 (자연 시간 1-2일) → A2 (Day 1 finding hotfix 별도 PR) → 결과에 따라 B/C 결정.

---

## 8. self-assessment (8/10)

| 측정                 | 점수     | 근거                                                              |
| -------------------- | -------- | ----------------------------------------------------------------- |
| 인프라 안정성        | 9/10     | Beat schedule + worker dispatch 90s 무결, BL-122 fix 효과         |
| Bug discovery        | 8/10     | Finding 3건 + LESSON 1건 (자기 정정) — production-quality dogfood |
| LESSON 가치          | 8/10     | L-S27-1 schema multi-schema 인지 — 향후 영구 적용                 |
| Auto-Loop ergonomics | 7/10     | 사용자 1회 escalate (false alarm), 그 외 무중단                   |
| 종합                 | **8/10** | H1→H2 gate(★★★) 통과 후 추가 momentum                             |

`AGENTS.md` 활성 sprint 갱신 + REFACTORING-BACKLOG entry (BL-137/138/139 + L-S27-1) 별도 atomic update.

---

## 9. PR 머지 후 처리 BL (atomic)

- BL-137 신규 strategy trading settings UI 추가 (Finding #1)
- BL-138 Live Sessions list "BTC/USDT 5m" 공백 추가 (Finding #2)
- BL-139 LiveSessionDetail aggregation scope 검토 (Finding #3)
- L-S27-1 multi-schema 조회 의무 — `.ai/common/global.md` 승격 후보
