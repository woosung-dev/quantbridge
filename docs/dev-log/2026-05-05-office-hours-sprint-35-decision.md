# office-hours — Sprint 35 분기 결정 (Wedge A backtest 단독 정밀화 + Gated 2-step + codex GO_WITH_FIXES surgery)

**날짜:** 2026-05-05 (Sprint 34 종료 직후, main @ afe9a5e)
**Mode:** Startup (dogfood-first indie SaaS, pre-product)
**Supersedes:** [`2026-05-04 Sprint 28 office-hours design`](https://gstack-projects.local/quant-bridge/sprint28-design) (1주 만에 Premise P1 무너짐)
**산출물 위치:**

- Design doc (APPROVED): `~/.gstack/projects/quant-bridge/woosung-main-design-20260505-213804.md`
- Plan file: `~/.claude/plans/office-hours-radiant-eclipse.md`
- Builder Journey: `~/.gstack/builder-journey.md`

---

## 1. 본인 직관 (entry point)

> "기능 다 안 돌아가고 출시 기능 일부만 + 디자인 엉성. 왜 배포 prep?"

Sprint 34 retro 의 "Day 7 self-assess ≥7 → Beta 본격 진입 (BL-070~075)" 분기 path 와 정면 충돌. 어제 (2026-05-04) Sprint 28 office-hours design 의 Premise P1 ("BL-141+140b+004 완료 = Beta 진입") 가 1주 만에 무너짐 evidence:

- Sprint 28 self-assess = 8.0/10 → 오늘 Day 5=6~7 → Day 6=5 (regression) → Day 6.5 PASS (mid-check)
- Day 6.5 PASS = "거짓말 안 함" PASS (Surface Trust 차단 작동) ≠ "기능 작동" PASS
- BL-178 신규 발견 — production BTC/USDT 1h/4h 3건 backtest 모두 `metrics.buy_and_hold_curve = null` (PRD 24 metric 중 1개 production 항상 null)

**진짜 H1 종료 gate (BL-005 본인 1-2주 실자본 dogfood) 는 BL-003 mainnet runbook prereq 미완료로 시작 불가** → Sprint 34 retro 의 "Day 7 ≥7 → Beta" 는 BL-005 자체를 skip 하는 fictitious gate.

---

## 2. 결정 요약

### Wedge (Q4 narrowest, dogfood-first 변형)

**A) backtest 단독 정밀화** (★★★★★) — "본인이 다음 주 월요일 본인 시간 1주 거는 가장 좁은 워크플로우 1개". backtest output trust = 모든 downstream (demo trading, live trading, 외부 user) 의 root cause.

기각: B (backtest + Bybit demo trading) / C (실자본 1-2주 mainnet, BL-003 prereq + 14일 lead time) / D (Beta 본격, BL-005 trigger 위반).

### Approach (Phase 4)

**C) Gated 2-step** (★★★★★)

- **Sprint 35** (1주, 4-5 PR) = polish iter 3 (codex GO_WITH_FIXES surgery 적용: BL-178 + BL-176 + BL-150 잔여 walk-forward 만 + **NEW backtest golden oracle**, **BL-174 제거** = Sprint 36+ defer) + Day 7 종합 self-assess
- **Day 7 4중 AND gate** ((a) self-assess ≥7 + (b) BL-178 production BH 정상 + (c) **NEW: golden oracle 통과** + (d) 신규 BL P0=0):
  - **통과** → Sprint 36 = BL-003 mainnet runbook + BL-005 본격 (1-2주 소액 mainnet, ≠ Beta 본격)
  - **미통과** → Sprint 36 = polish iter 4 (새 발견 BL fix) + 다시 Day 7

### 4 Premise (모두 동의, P3 fictitious gate 정정 + P2 codex surgery 적용)

1. **P1** — backtest output trust = Surface Trust pillar root cause (ADR-019 정합)
2. **P2 (codex surgery 적용)** — BL-178 + BL-176 + BL-150 잔여 walk-forward + NEW backtest golden oracle = backtest trust 의 정확한 surface 4건. (BL-174 제거 = Sprint 36+ defer / monte-carlo = native API X 시 Sprint 36+ 분리)
3. **P3** — Sprint 34 retro 의 "Day 7 ≥7 → Beta" = fictitious gate (BL-005 자체 skip). 측정값 자체는 유효, 후속 action 만 "Beta 본격" → "BL-005 본격" 정정
4. **P4** — Sprint 35 scope = polish iter 3 + dogfood Day 7-14 + (gating). ≠ "Beta 본격 진입"

---

## 3. Codex GO_WITH_FIXES surgery 5건

**Codex 결과:** `VERDICT=HOLD, P1_FINDINGS_COUNT=1, PREMISE_CHALLENGED=P2, APPROACH_C_OK=YES` = GO_WITH_FIXES 승인 조건 충족.

**Codex 핵심 challenge (P2):** "BL-178 + BL-176 + BL-174 + BL-150 잔여" 가 정확한 surface 4건 아님. **UI polish + robustness 기능 섞인 목록.** 진짜 trust surface 빠진 것: **Pine semantics oracle + data quality invariant + backtest equity/trade golden fixture + production data lineage**.

| #   | Surgery                                                                                                                                                                                                                    | 적용 결과                                                             |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| 1   | **P2 갱신** — BL-174 제거 + NEW backtest golden oracle 추가                                                                                                                                                                | design doc Premises + plan file 양쪽 적용                             |
| 2   | **NEW Slice 1.5** — backtest golden oracle fixture 2-3개 (Pine semantic / entries / exits / equity / BH curve, BTC/USDT 1h+4h, bar 단위 tolerance, TradingView export 또는 수동 검증 strategy), Worker A or 메인, M (3-4h) | 9 slice 으로 확장                                                     |
| 3   | **Slice 2 축소** — BL-176 만, BL-174 제거                                                                                                                                                                                  | Worker B scope = BL-176 만 (S 2h)                                     |
| 4   | **Slice 3 조건부** — BL-150 잔여 walk-forward 만 (Slice 0 결과 따라 분기). monte-carlo = native API X 시 Sprint 36+ 분리                                                                                                   | Effort: M (3-4h walk-forward 만 native) / L (1일 walk-forward custom) |
| 5   | **Day 7 4중 AND gate** — (a)+(b)+(d) 기존 + (c) NEW golden oracle 통과 추가                                                                                                                                                | "거짓말 안 함" PASS 와 별도 "기능 작동" 직접 검증 mechanism           |

**Sprint 33-34 lesson #2 (codex P1 한도 제거) 정합** — P1 finding 1건 모두 surgery 적용. P2 challenge 자체 가 "기능 다 안 돌아간다" 본인 직관의 진짜 root cause = golden oracle 부재 mechanism 발견.

---

## 4. Sprint 35 Master Plan 골격 (9 slice)

| Slice                  | scope                                                                                                                                  | Est                              | Worker                      |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------- | --------------------------- |
| 0 (preflight)          | vectorbt walk-forward + monte-carlo native API survey spike                                                                            | S (30min)                        | 메인                        |
| 1a                     | BL-178 root cause spike (TimescaleDB BTC/USDT bar `close.isna()` + `(close<=0)` + dtype + v2_adapter ohlcv path)                       | S (30min-1h)                     | A                           |
| 1b                     | BL-178 fix — code fix path (2-3h) / **escape hatch (backfill scope 시 BL-178 분리, Sprint 36+ 의무)**                                  | S-M (2-3h or escape)             | A                           |
| **1.5 (NEW codex P1)** | **backtest golden oracle fixture 2-3개** (BTC/USDT 1h+4h, bar 단위 tolerance, Pine semantic / entries / exits / equity / BH 동시 검증) | M (3-4h)                         | A or 메인                   |
| 2 (codex 축소)         | **BL-176 만** (SelectWithDisplayName clear). BL-174 제거 → Sprint 36+ defer                                                            | S (2h)                           | B                           |
| 3 (codex 조건부)       | BL-150 잔여 **walk-forward 만** (monte-carlo native X 시 Sprint 36+ 분리)                                                              | M (3-4h native) / L (1일 custom) | 메인 (Slice 1b/1.5 머지 후) |
| 4a (mid-dogfood)       | Slice 1b 머지 직후 단독 mid-check (numeric fixture + golden oracle 통과 검증)                                                          | (사용자 30분)                    | 메인                        |
| 4b (optional)          | Slice 2 머지 후 추가 mid-check 선택                                                                                                    | (사용자 15분)                    | 메인                        |
| 5 (retro)              | Sprint 35 master retrospective + Day 7 self-assess + AGENTS/BACKLOG/INDEX 갱신                                                         | M (2h)                           | 메인                        |

병렬: Slice 1a → 1b → 1.5 (Worker A 직렬, golden oracle 까지) + Slice 2 (Worker B). 1주 fit risk = Slice 1b escape hatch + Slice 3 양분기 effort + Slice 2 축소 (codex surgery).

---

## 5. dual metric (review)

- **Spec review (Claude subagent reviewer):** 9.0/10 (iter 2, 7/7 issue APPLIED — issue-5.2 BL-178 escape hatch / issue-1.1 BL-150 effort 양분기 / issue-3.1 Slice 3 worker 분담 / issue-1.2 dual metric 사전 확정 / issue-5.1 codex hang fallback / issue-1.3 mid-check trigger 분리 / issue-2.1 P3 명확화)
- **Cross-model review (codex CLI 0.128.0, model_reasoning_effort=high):** VERDICT=HOLD, P1=1, PREMISE_CHALLENGED=P2, APPROACH_C_OK=YES = GO_WITH_FIXES → 5건 surgery 적용
- **승인 조건 framework 사전 정의** (GO / GO_WITH_FIXES / HOLD / NO_GO) — 본 결정은 GO_WITH_FIXES 라인 (Approach OK + premise 일부 수정)

---

## 6. 신규 lesson 후보 + Sprint 35 검증 의무

1. **design doc supersede chain Premise rot 패턴** — Sprint 28 design (어제) Premise P1 1주 만에 무너짐. /office-hours 진입 시 prior design (Supersedes 필드) 의 Premise 들 trigger 충족 여부 자동 challenge 의무. **본 session 자체 가 학습 결과 evidence** (Sprint 28 design 의 Premise P1 자동 sense → P3 fictitious gate detection)
2. **dogfood mid-check PASS vs 기능 작동 distinction** — fail-closed gate 작동 = false trust 차단 ✅, 기능 작동 ❌ 분리 의무. mid-dogfood numeric verification 시 (a) Surface Trust 차단 작동 vs (b) 기능 작동 명확히 분리 의무. **Sprint 35 Slice 1.5 backtest golden oracle = (b) 직접 검증 mechanism**
3. **승인 조건 framework 사전 정의** — codex review / spec review 결과 따라 사전 정의된 GO/GO_WITH_FIXES/HOLD/NO_GO 조건 매핑 → 자동 분기 결정 mechanism. /office-hours 종료 phase 안 영구 적용 후보

---

## 7. 다음 step

- ✅ **본 dev-log 작성 + INDEX 갱신 + commit** (현재 phase)
- ⏳ Sprint 35 master plan 작성 (`~/.claude/plans/quantbridge-sprint-35-*.md`) — 본 design 의 Slice 0~5 구체화. codex G.0 master plan validation (medium tier, iter cap 2). hang 시 Sonnet self-review fallback (다음 세션, fresh context)
- ⏳ AGENTS.md "현재 작업" + REFACTORING-BACKLOG.md 갱신 — Sprint 34 → 35 transition + BL-174 = Sprint 36+ defer + NEW backtest golden oracle BL ID assign + BL-070~075 trigger 정정 ("4중 AND gate 통과 → BL-003+BL-005 본격, ≠ Beta")

---

## Cross-link

- Plan file: `~/.claude/plans/office-hours-radiant-eclipse.md`
- Design doc (APPROVED): `~/.gstack/projects/quant-bridge/woosung-main-design-20260505-213804.md`
- 직전 Sprint 34 retro: [`2026-05-05-sprint34-master-retrospective.md`](2026-05-05-sprint34-master-retrospective.md)
- Sprint 34 mid-dogfood Day 6.5: [`2026-05-05-dogfood-day-6.5.md`](2026-05-05-dogfood-day-6.5.md)
- Sprint 28 design (superseded): `~/.gstack/projects/quant-bridge/woosung-stage-h2-sprint28-comprehensive-design-20260504-173422.md`
- Builder Journey (15 sessions, 8 designs): `~/.gstack/builder-journey.md`
- ADR-019 Surface Trust Pillar: [`2026-05-05-sprint30-surface-trust-pillar-adr.md`](2026-05-05-sprint30-surface-trust-pillar-adr.md)
