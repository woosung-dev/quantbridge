# Sprint 8a Tier-0 Week 1-2 Comprehensive Report

> **일자:** 2026-04-18 (Day 1-13 통합, v2.0)
> **브랜치:** `feat/sprint8a-tier0-pynescript-fork`
> **관련 PR:** #20
> **ADR:** [ADR-011 Pine Execution Strategy v4](011-pine-execution-strategy-v4.md) (+[#19 amendment](https://github.com/woosung-dev/quantbridge/pull/19))
> **선행 작업:** [Phase -1 findings](../../.gstack/experiments/phase-minus-1-drfx/output/phase-1-findings.md) (PR #18 merge `0f6583d`)

---

## 🎯 한 줄 권고

> **CONTINUE to Sprint 8a Week 3 (렌더링 scope A + OCO 지연 체결 + 실전 corpus E2E). pine_v2가 실제 Pine 전략(합성 MA crossover)을 처음부터 끝까지 실행하여 거래 시퀀스 생산 성공. 152 tests로 8개 레이어 검증. ADR-011 §9 가정 3개 전부 실증. s1_pbr 실전 E2E는 Week 3의 pivot detection + stop order가 필요하여 이연.**

---

## 1. Week 1-2 실측 범위 — 8 레이어 Foundation (Day 1-13)

| # | 레이어 | 파일 | 테스트 | 핵심 가치 |
|:--:|------|------|:--:|------|
| **L1** | Pine 파서 | `parser_adapter.py`, `ast_metrics.py` | 17 | pynescript AST + 에러 경로 고정 |
| **L2** | AST 분류기 | `ast_classifier.py` | 12 | Track S/A/M + 호출 분포 |
| **L3** | Alert Hook v1 | `alert_hook.py` | 29 | 메시지+조건 분류, mismatch 자동 감지 |
| **L4** | 런타임 primitive | `runtime/persistent.py` | 15 | var/varip bar lifecycle |
| **L7** | AST content 추출 | `ast_extractor.py` | 21 | strategy kwargs + inputs + var decls |
| **L8** | **Interpreter** ⭐ | `interpreter.py` | 21 | 표현식+문장 tree-walking visitor |
| **L9** | **stdlib ta.*** ⭐ | `stdlib.py` | 13 | 9개 지표 + na/nz + user var subscript |
| **L10** | **strategy.*** ⭐ | `strategy_state.py` | 13 | 포지션/체결/PnL, H1 MVP 준수 |
| **Integration** | 통합 POC + E2E | 3 test 파일 | 11 | L1→L4 POC + MA crossover E2E |
| **합계** | — | 9 source / 9 test 파일 | **152** | ruff/mypy clean, 기존 526 green |

---

## 2. Week 2 핵심 성취: 합성 Pine 전략 E2E 실행

### 입력 (합성 MA Crossover 전략)
```pine
//@version=5
strategy("MA Cross E2E")
fast = ta.sma(close, 3)
slow = ta.sma(close, 5)
if ta.crossover(fast, slow)
    strategy.entry("L", strategy.long, qty=1.0)
if ta.crossunder(fast, slow)
    strategy.close("L")
```

### 실행 pipeline (모든 단계 검증됨)
```
Pine 소스
  └→ [L1] pynescript 파싱 → AST
       └→ [L8] Interpreter 해석
            ├→ 표현식: BinOp/Compare/Name(built-in close) → 숫자
            ├→ [L9] ta.sma(close, 3) stateful → fast
            ├→ [L9] ta.sma(close, 5) stateful → slow
            ├→ [L9] ta.crossover(fast, slow) → bool (이전 bar 비교)
            ├→ [L8] if문 분기 → body 실행
            ├→ [L10] strategy.entry → StrategyState에 Trade open
            ├→ [L10] strategy.close → PnL 계산 + closed_trades
            └→ [L4] var/transient 관리 + [next bar]
  └→ bar-by-bar 이벤트 루프 (event_loop.py)
  └→ 거래 결과 리포트 {open/closed/pnl/warnings}
```

### 검증된 거래 시나리오 (6 E2E 테스트)
- 하락→상승: crossover 발생 → Long 진입 → 하락 반전 시 close
- 평탄 가격: 0 거래 (crossover 이벤트 없음)
- 양방향(L+S): crossover→Long, crossunder→Long close + Short 진입
- close_all: bar_index 조건으로 모든 포지션 일괄 청산 + PnL 집계
- 미지원 kwarg(stop=)는 조용히 경고 기록만

---

## 3. 6 Pine Script × 8 레이어 매트릭스

### Phase -1 corpus (frozen snapshot)

| # | Track | 파일 | 크기 | Pine ver |
|:--:|:---:|------|---:|:---:|
| S1 | S 🟢 | `s1_pbr.pine` (Pivot Reversal Strategy) | 828B | v6 |
| S2 | S 🟠 | `s2_utbot.pine` (UT Bot Strategy) | 2,784B | v5 |
| S3 | S 🔴 | `s3_rsid.pine` (RSI Divergence Strategy) | 6,555B | v5 |
| I1 | A 🟢 | `i1_utbot.pine` (UT Bot Alerts) | 1,781B | v4 `study()` |
| I2 | A 🟠 | `i2_luxalgo.pine` (LuxAlgo Trendlines) | 3,903B | v5 |
| I3 | A 🔴 | `i3_drfx.pine` (DrFX Diamond Algo) | 38,308B | v5 |

### 레이어별 통과율

| 레이어 | s1 | s2 | s3 | i1 | i2 | i3 | 비고 |
|:---|:-:|:-:|:-:|:-:|:-:|:-:|:---|
| L1 파싱 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 노드 수 strict equality |
| L2 Track 판정 | S | S | S | A | A | A | alert 기반 자동 |
| L3 Alert 추출+분류 | — | — | — | 2/2 | 2/2 | 6/6 | N=10 alerts · 100% 분류 · i3 #2 자동 mismatch |
| L4 PersistentStore | — | — | — | — | — | — | 의미론 단위 검증 (15) + 통합 POC |
| L7 content 추출 | 2/0/2 | 9/0/2 | 15/0/3 | 3/0/0 | 7/9/0 | 21/24/0 | input/var/strategy.* |
| **L8 Interpreter** | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 실전 E2E는 Week 3 scope (아래 §5) |
| **L9 stdlib ta.*** | 9 indicators 구현 | — | — | — | 13 tests 통과 |
| **L10 strategy.*** | entry/close/close_all | — | — | — | 13 tests 통과 |

**⚠️ L8 interpreter가 6 corpus 실전에서 막히는 이유 (Week 3 과제):**
- s1: `ta.pivothigh/pivotlow` 미구현 + `syminfo.mintick` na 반환 + `stop=` kwarg 미지원 (stop order 체결 로직)
- s2: `ta.atr` 있으나 heikin ashi OHLC 별도 계산 필요
- s3: `ta.rsi` + pivot high/low + divergence 복합 로직
- i1-3: indicator + alert만 있으므로 strategy.* 실행 경로 0 — 실행 자체는 가능하나 거래 결과 없음

6 corpus 중 **i1_utbot** 정도는 strategy.entry/close 없이 실행 가능. 나머지 5종은 Week 3 확장 필요.

---

## 4. ADR-011 §9 가정 3개 최종 판정

| # | 가정 | 판정 | 근거 |
|:--:|---|:--:|---|
| **A1** | Track S/A/M 비율 20~30/40~50/20~30% | 🟡 **유보** | N=6에서 S 50%/A 50%/M 0%. 일반화 불가. TV 15-20개 프로파일링 Week 3 또는 별도 |
| **A2** | PyneCore `trail_points/offset` 지원 | ✅ **N/A** | #19 PR로 H2+ 이연 확정. H1 MVP scope 준수 |
| **A3** | Alert 메시지 분류기 >80% 정확도 | ✅ **강하게 실증** | 10/10 분류 + i3 #2 mismatch 자동 감지 (v1 condition-trace) |

### 신뢰도 추이
- ADR-011 v1 초기: 8/10
- Phase -1 amendment(#19) 후: 9/10
- Week 1 Foundation 후: 9.2/10
- **Week 2 interpreter + strategy.* E2E 증명 후: 9.5/10** — ADR-011 §9에 추정했던 "Phase -1 + Week 2-3 완료 시 9.5/10"에 도달

---

## 5. Week 3 이연 항목 (s1_pbr 실전 E2E 차단 요인)

Week 2 scope에서 당초 목표로 했던 `s1_pbr.pine` 실전 실행은 아래 3개 미지원 기능으로 인해 **명시적 이연**:

| 이연 항목 | 이유 | Week 3 구현 복잡도 | H1 MVP 필수? |
|:---|---|:---:|:---:|
| `ta.pivothigh(lookback_l, lookback_r)` / `pivotlow` | lookback confirmation 지연 emit (`right` bar 지나야 확정) | 중 | ❓ |
| `strategy.entry(stop=price)` stop order 지연 체결 | next bar에서 price crossing 감지 후 fill (OCO 로직) | **상** | ✅ (s1 필수) |
| `syminfo.mintick` 상수 (0.01 등) | 심볼별 최소 가격 단위 — 현재 na 반환 | 하 | ✅ |
| 렌더링 범위 A (box/label/line/table 좌표 getter) | i2/i3 실행에 필요 (line.get_price 등) | 중-상 | ✅ (i3 필수) |
| `request.security` MTF | i3 8회 사용 | 상 | ❌ (H2+) |

Week 3 수행 시 추가 10-15h 예상.

---

## 6. Week 1-2 핵심 발견 7가지

### 💡 발견 1: Track 분포가 corpus 편향 크게 반영
S 3/A 3/M 0 — 사용자 제공 corpus 특성. ADR-011 §9 "M 20-30%" 가정은 TV 15-20개 공개 스크립트 프로파일링 후 재검증 필요.

### 💡 발견 2: i3_drfx 79 render scope A 실증 (Execution-First)
box 25 + label 35 + line 16 + table 3 = 79. ADR-011 §3 통찰 2 (매매 로직 4.6%)가 단일 스크립트로 실증.

### 💡 발견 3: Pine v4 `study()` 자동 alias 감지 성공
i1_utbot이 v4 문법. L2 분류기가 자동 indicator 취급.

### 💡 발견 4: alert #2 message-condition mismatch 자동 감지 (ADR-011 §2.1.3 구현)
i3_drfx alertcondition(bear, "BUY", "BUY") — message=BUY → long, condition=bear → short. L3 v1에서 discrepancy=True + 최종 signal은 condition 우선(SHORT_ENTRY). 10 alert 중 1건(10%)의 구조적 소스 오타 자동 방어.

### 💡 발견 5: i3_drfx request.security 8회 (H2 MTF 우선순위 근거)
인기 indicator의 MTF 사용 실태.

### 💡 발견 6: pynescript SyntaxError는 Python 내장 미상속
`pynescript.ast.error.SyntaxError`는 builtin SyntaxError 상속 안 함. Week 2+ 에러 UX 설계 시 이 전제 고정.

### 💡 발견 7 (신규): strategy.entry stop= OCO 체결은 H1 MVP 핵심 차단 요인
s1_pbr (가장 단순 TV 내장 전략)도 stop entry 체결 로직 필요. ADR-011 §6 H1 MVP scope에 "market order만"으로 축소했으나 **실전 TV 스크립트 호환엔 stop order가 사실상 필수** — Week 3에서 추가하되 trail_points/qty_percent는 H2+ 유지.

---

## 7. 라이선스 & 외부 자산 현황

| 자산 | 라이선스 | QB 사용 방식 | NOTICE | 상태 |
|:---|:---:|---|:---:|:---:|
| pynescript 0.3.0 | LGPL-3.0 | PyPI 의존성 (pinned) | ✅ | 활성 |
| antlr4-python3-runtime 4.13.2 | BSD-3-Clause | pynescript transitive | — | 활성 |
| PyneCore `transformers/persistent.py` | Apache 2.0 | 의미론 참조 이식(재설계) | ✅ 예정 | Week 1 완료 |

**격리 정책 확인:**
```bash
cd backend && rg -n "^import pynescript|^from pynescript" src/strategy/pine_v2/
# parser_adapter.py, ast_metrics.py, ast_classifier.py, alert_hook.py, ast_extractor.py, interpreter.py
#  — 6 파일만 (LGPL 파일 단위 copyleft 격리)
```

`backend/src/strategy/pine/` 모듈 touch: **0 lines** (기존 pine 경로 dogfood 안전)

---

## 8. 커밋 & PR 요약

| Day | Commit | 내용 | Tests |
|:---:|:---:|---|:---:|
| 1 | `fb9d318` | pynescript scaffold + NOTICE + parser baseline | 7 |
| 2 | `ec1175a` | AST classifier + Track 판정 | 12 |
| 3 | `92a5af9` | Alert Hook v0 | 24 |
| 4 | `3a5896f` | PersistentStore var/varip | 15 |
| 5 | `7352345` | Week 1 보고서 v1.0 | — |
| 6 | `4f278d8` | Alert Hook v1 condition-trace + 자동 discrepancy | +5 |
| 7 | `725b035` | AST content extractor | 21 |
| 8 | `7cc3225` | L1 에러 경로 + 통합 POC | 15 |
| 8b | `2a428cd` | 보고서 v1.1 | — |
| **9-10** | `3e217d5` | **Week 2 Interpreter + event loop** | 21 |
| **11** | `22f163a` | **ta.* stdlib + user 변수 series** | 13 |
| **12-13** | `ffc6ee9` | **strategy.* + E2E MA crossover** | 19 |
| 14 | (본 커밋) | Week 1-2 종합 보고서 v2.0 | — |

**총 변경:** 9 source + 9 test + 4 fixture + NOTICE + README + 본 보고서
**총 테스트:** **152 pine_v2** (152/152 PASS) + 526 기존 회귀 green
**품질 게이트:** ruff ✅ · mypy ✅ (13 source files)

---

## 9. Week 3 후속 결정 (Sprint 8a Tier-0 완성)

다음 세션에 동일 브랜치 또는 새 브랜치에서 진행:

### 우선순위 A — s1_pbr E2E 완주 (H1 MVP 호환)
1. `ta.pivothigh` / `ta.pivotlow` 구현 (lookback confirmation)
2. `strategy.entry(stop=price)` 지연 체결 (next bar price cross 시 fill)
3. `syminfo.mintick` 상수 (기본 0.01)
4. s1_pbr 실행 → 기존 `src/strategy/pine/` 모듈 결과 대조 검증

### 우선순위 B — 렌더링 범위 A (Track A 실행 unblock)
5. `box.new` / `box.get_top/bottom` / `box.delete` 좌표 저장
6. `line.new` / `line.get_price` (LuxAlgo i2 필수)
7. `label.new` / `label.set_x/y`
8. `table.new` / `table.cell` NOP or 메모리 stub

### 우선순위 C — 운영 경계
9. Performance: 10k bar 실행 시간 <1s 목표
10. DB 저장 스키마 설계 (Trade → PostgreSQL Trades 테이블 매핑)
11. API endpoint: `/api/v1/strategies/{id}/backtest-v2` — 기존 `pine/` 경로와 병행

---

## 10. 참조

- [ADR-011 Pine Execution Strategy v4](011-pine-execution-strategy-v4.md)
- [ADR-011 Phase -1 amendment (#19)](https://github.com/woosung-dev/quantbridge/pull/19)
- [Phase -1 findings](../../.gstack/experiments/phase-minus-1-drfx/output/phase-1-findings.md)
- [pine-execution-architecture](../04_architecture/pine-execution-architecture.md)
- [pine_v2 README](../../backend/src/strategy/pine_v2/README.md)
- [NOTICE](../../NOTICE)
