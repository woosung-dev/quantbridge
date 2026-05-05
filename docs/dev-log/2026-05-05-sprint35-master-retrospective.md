# Sprint 35 — polish iter 3 (Wedge A backtest 단독 정밀화) Master Retrospective

**기간:** 2026-05-05 (단일 세션 + office-hours codex G.0 iter cap 2 surgery 18건 선적용)
**브랜치:** main `8df5e58` (4 PR all merged — #152 office-hours dev-log / #153 AGENTS·BACKLOG transition / #154 Slice 1a / #155 Slice 1.5a)
**입력:** dogfood Day 6.5 PASS (BL-178 분리 + 회귀 0건) / Day 7 self-assess = **6/10 (게이트 미달)**
**Sprint 36 분기 결정:** **polish iter 4** (Day 7 gate (a) FAIL — 6 < 7)

---

## 0. Sprint 35 4 PR 통합

```
8df5e58 PR #155 test(bl-180): backtest engine golden oracle minimal fixture (8 tests, 2 scenarios)
f0f9daa PR #154 docs(sprint35): BL-178 root cause = Docker worker stale 확정 (Slice 1a)
a0cc18f PR #153 chore(sprint35): AGENTS/BACKLOG transition (Sprint 34 → 35) + BL-180 신규 등록
78fb39b PR #152 docs(sprint35): office-hours 분기 결정 (Slice 1.5a + Day 7 4중 AND gate)
```

**총 4 PR** (docs 3 + test 1). Stretch (BL-176 / BL-150 / Slice 1.5b) = 전체 미착수 — Mandatory 완료 후 시간 소진.

---

## 1. 출발점 — office-hours session 분기 결정

### office-hours session 결정 (2026-05-05)

- **Sprint 35 = Wedge A backtest 단독 정밀화** (Approach C Gated 2-step) ★★★★★
- **BL-178 fix 전제:** Slice 1a root cause 확정 → Slice 1b Path A/B 분기 → Day 7 (b) gate
- **신규 Slice 1.5a:** BL-180 hand-computed engine oracle (circular oracle 함정 회피)
- **Day 7 4중 AND gate:** (a) self-assess ≥7 + (b) BL-178 production BH 정상 + (c) BL-180 8 test GREEN + (d) new P0=0 AND Sprint-35-caused P1=0

### codex G.0 surgery (Sprint 35 진입 직전)

session `019df85d-bcbf-7d63-a6cc-ce106de4ace1` / iter cap 2 / **1.34M tokens** (iter 1=862k / iter 2=472k) / Verdict = **GO_WITH_FIXES** / surgery 18건 (P1=7/P2=7 + iter2 추가).

핵심 반영:

- Slice 1.5a 신규 (BL-180 circular oracle 회피 — hand-computed minimal 2 strategy + tiny OHLCV + checked-in expected)
- Path B escape → Day 7 (b) FAIL/UNKNOWN (free pass 폐지)
- Day 7 (d) 강화 (new P0=0 AND Sprint-35-caused P1=0)
- BL-176 schema required 유지 (sentinel/nullable X)
- vectorbt native walk-forward premise 폐기 → Sprint 36+ defer confirmed

---

## 2. Slice 1a — BL-178 root cause 확정 (PR #154)

### 진단 결과: Docker worker container STALE

**가설 3개 검증 (전부 기각):**

| 가설                                           | 검증                                                                                          | 결과        |
| ---------------------------------------------- | --------------------------------------------------------------------------------------------- | ----------- |
| OHLCV NaN/<=0 (TimescaleDB 누락 bar)           | isolated DB에서 동일 BTC/USDT 1h 조회 → close 전부 valid                                      | ❌ 기각     |
| v2_adapter dtype 변환 NaN 도입                 | `_v2_buy_and_hold_curve` 단위 테스트 + BL-175 회귀 8/8 GREEN                                  | ❌ 기각     |
| Docker worker container stale (새 코드 미반영) | `docker cp` 후 BL-175 회귀 GREEN → `make up-isolated-build` 후 production backtest BH 비-null | ✅ **확정** |

**Root cause:** Docker worker container 에 volume mount 없음 → 이미지 빌드 이후 코드 변경이 실행 컨테이너에 미반영. PR #150 (BL-175) 은 host에 merge 됐으나 worker는 이전 빌드 그대로 실행. `make up-isolated-build` 실행 후 BH curve 정상 반환 ✅

**BL-181 신규 등록:** Docker worker auto-rebuild trigger 부재 → 코드 변경 후 worker 수동 rebuild 의무. 사용자 망각 시 silent stale 재발 가능성. Sprint 36 stretch 대상.

**Slice 1b (Path A quarantine + observable reason) = 미착수:** root cause가 stale container 이므로 Path A 가정 (invalid OHLCV) 자체 무효. Slice 1b는 BL-181 auto-rebuild fix 방향으로 Sprint 36 흡수.

---

## 3. Slice 1.5a — BL-180 engine golden oracle (PR #155)

### 비순환 오라클 설계

**핵심 원칙:** `StrategyState + Trade` 직접 주입 → Pine 인터프리터 우회 → entry/exit 가격 완전 제어 → expected 값 손 계산 가능 (circular oracle 함정 회피).

```
backend/tests/fixtures/backtest_golden_minimal.py   (S1/S2 fixture + expected)
backend/tests/backtest/test_golden_oracle_minimal.py (8 named test + helpers)
```

### 2 시나리오 손 계산 검증

**S1 (단일 롱, 5 bars, fees=0):**

```
close=[100,110,105,115,120], entry@100 exit@120 qty=1
equity=[1000,1010,1005,1015,1020], BH=[1000,1100,1050,1150,1200]
```

**S2 (롱+숏 2 트레이드, 6 bars, fees=0):**

```
close=[100,120,90,110,80,100]
T1: long entry@100 exit@120 → pnl=20
T2: short entry@90 exit@80 → pnl=(90-80)*1=10
equity=[1000,1020,1020,1000,1030,1030], BH=[1000,1200,900,1100,800,1000]
```

### 실제 RawTrade 필드 발견 (소스 직독)

계획 단계에서 `entry_bar`/`exit_bar`/`qty`/`net_pnl` 로 가정했으나 실제 `types.py` 확인 결과 `entry_bar_index`/`exit_bar_index`/`size`/`pnl` 임을 확인 → test fixture 정확히 반영.

### 결과

- **8/8 PASSED** (pytest local + worker container 검증 `docker cp` 방식)
- **pytest 1580 → 1588 (+8)**
- mypy 0 / ruff 0

---

## 4. Slice 4a — mid-dogfood 6항목 검증

### 검증 환경

- isolated mode (3100/8100/5433/6380)
- 전략 "Dogfood EMA Cross" 신규 생성 (BTC/USDT 1h, 2024-01-01 ~ 2024-06-30, init_capital=10,000)
- `make up-isolated-build` 로 worker 재빌드 후 진행

### 검증 결과

| #   | 검증 항목                                 | 결과                                                          |
| --- | ----------------------------------------- | ------------------------------------------------------------- |
| 1   | `bh_curve[0][1] == initial_capital`       | ✅ `"10000.00000000" == "10000.00000000"`                     |
| 2   | BL-180 oracle 8 tests GREEN (PR #155)     | ✅ merged                                                     |
| 3   | N/A (Slice 1b Path A quarantine 미착수)   | —                                                             |
| 4   | Null backward-compat (legacy schema)      | ✅ `list[...] \| None = None` (types.py:100 + schemas.py:170) |
| 5   | `buy_and_hold_curve` 필드 존재 + nullable | ✅ 확인                                                       |
| 6   | API raw JSON == UI 렌더링 일치            | ✅ BH 곡선 (파란 점선) 정상 표시, 10,000→14,366 USDT          |

**6/6 PASS.** BH curve 실제 production (isolated) 환경에서 정상 계산·표시 확인. BL-178 root cause (worker stale) 해소 후 첫 정상 BH 렌더링.

---

## 5. Day 7 4중 AND gate 결과

| Gate    | 항목                               | 결과                      | 비고                       |
| ------- | ---------------------------------- | ------------------------- | -------------------------- |
| **(a)** | self-assess ≥ 7/10                 | **FAIL (6/10)**           | ≥7 미달                    |
| (b)     | BL-178 production BH 정상          | ✅ PASS                   | worker rebuild 후 non-null |
| (c)     | BL-180 hand oracle 8 test GREEN    | ✅ PASS                   | PR #155                    |
| (d)     | new P0=0 AND Sprint-35-caused P1=0 | ⚠️ (a) fail로 평가 불필요 | BL-181 Sprint-35 신규 P2   |

**→ 전체 게이트 미통과 (4 AND gate 중 (a) FAIL)**

**Sprint 36 = polish iter 4** (Day 7 재측정 목표, 새 발견 BL fix)

---

## 6. 신규 lessons / BL 갱신

### 새로운 lesson 후보 (Sprint 36+ 검증)

1. **Docker worker stale silent BUG 패턴** — PR merge 후 worker 미재빌드 시 production 검증이 구 코드 기준. `make up-isolated-build` 의무화 + BL-181 auto-rebuild trigger 장치 필요. sprint 마다 재발 가능성 (LESSON-038 후보).
2. **골든 오라클 circular 함정** — 엔진 출력을 expected 로 쓰면 회귀 검증 불가. `StrategyState+Trade` 직접 주입으로 Pine 인터프리터 우회 + hand-computed expected = non-circular 보장 패턴. `BacktestConfig(fees=0, slippage=0)` pin 의무 (LESSON-039 후보).
3. **`docker cp` 임시 test 주입** — volume mount 없는 worker container 에 `docker cp` 로 파일 주입 → test 실행 가능. 단 container 재시작 시 유실. BL-181 resolve 전 임시 패턴 (Sprint 35 사용 사례).

### BL 변동

- **Resolved**: BL-178 (root cause = Docker worker stale 확정 + `make up-isolated-build` 워크어라운드 적용 — 근본 fix는 BL-181로 분리) / BL-180 (engine golden oracle 8 tests GREEN, PR #155)
- **신규 등록**:
  - **BL-181** (P2, Sprint 36 stretch): Docker worker auto-rebuild trigger 부재. 코드 변경 후 `make up` 만 실행하면 stale container 유지. auto-rebuild on host change 또는 rebuild hook 필요. est S (1-2h).
- **합계 변동**: 87 → 87 BL (Resolved 2 + 신규 1 = -1 net) → **86 BL**

---

## 7. dual metric

- **4 PR** (#152~#155, docs 3 + test 1)
- **backend pytest 1580 → 1588 (+8)** (BL-180 golden oracle 8 test)
- **frontend vitest**: 변경 없음 (FE 작업 0)
- **mypy 0 / ruff 0 / tsc 0 / eslint 0**
- **codex G.0 1.34M tokens** (iter cap 2, Sprint 34 327k 대비 ~4배 ↑ — surgery 18건 depth)
- **Day 7 self-assess 6/10** (gate (a) FAIL — Sprint 36 = polish iter 4)
- **Slice 4a 6/6 PASS** (BH curve 첫 정상 렌더링 확인)
- **Stretch 미착수**: Slice 1.5b / BL-176 SelectWithDisplayName / BL-150 walk-forward — Sprint 36 재검토

---

## Cross-link

- Plan: `~/.claude/plans/sprint-35-validated-firefly.md` (Slice 1.5a engine oracle)
- Sprint 35 master plan: `~/.claude/plans/quantbridge-sprint-35-anchored-oracle.md`
- codex session: `019df85d-bcbf-7d63-a6cc-ce106de4ace1`
- office-hours 분기 결정: `docs/dev-log/2026-05-05-office-hours-sprint-35-decision.md`
- BL-178 root cause spike: `docs/dev-log/2026-05-05-bl178-rootcause-spike.md`
- 직전 Sprint 34 retro: `docs/dev-log/2026-05-05-sprint34-master-retrospective.md`
- BACKLOG: `docs/REFACTORING-BACKLOG.md` (BL-178 Resolved / BL-180 Resolved / BL-181 신규)
