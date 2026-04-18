# Sprint 8a Tier-0 Final Report (Week 1-3 완주)

> **일자:** 2026-04-18 (Day 1-16 통합, v3.0)
> **브랜치:** `feat/sprint8a-tier0-pynescript-fork`
> **관련 PR:** #20
> **ADR:** [ADR-011 Pine Execution Strategy v4](011-pine-execution-strategy-v4.md) (+[#19 amendment](https://github.com/woosung-dev/quantbridge/pull/19))
> **선행 작업:** [Phase -1 findings](../../.gstack/experiments/phase-minus-1-drfx/output/phase-1-findings.md) (PR #18 `0f6583d`)

---

## 🎯 한 줄 결론

> **Sprint 8a Tier-0 완주. pine_v2가 TradingView 공식 Pivot Reversal Strategy(s1_pbr.pine)를 끝까지 실행하여 거래 시퀀스를 생성 — Phase -1 "기존 pine/ 0/6 실패"를 완전히 역전. 169 tests로 검증. ADR-011 신뢰도 9.5 → 9.7. Week 4+ 렌더링/나머지 corpus는 별도 Sprint.**

---

## 1. Phase -1 findings 완전 역전 (핵심 성취)

| 대상 | 기존 `pine/` (Phase -1) | **pine_v2 (본 PR)** |
|:---|:---|:---|
| s1_pbr.pine 실행 | ❌ `unsupported: ta.pivothigh` | ✅ **27 bars 완주, errors=0** |
| ta.pivothigh/pivotlow | 미지원 | ✅ 구현 + 11 단위 테스트 |
| strategy.entry(stop=) | 미구현 | ✅ pending order + OCO 체결 |
| syminfo.mintick | 미지원 | ✅ 0.01 반환 |
| 파서 커버리지 (6 corpus) | 0/6 | pynescript 기반 6/6 |

**증명 로그 (test_e2e_s1_pbr.py 실행 출력):**
```
=== s1_pbr 대조 ===
  기존 pine/: status=unsupported, error=function not supported: ta.pivothigh
  pine_v2:    bars_processed=27, errors=0
```

---

## 2. Week 1-3 전체 — 8 레이어 + 실행 계층 Foundation

| # | 레이어 | 파일 | 테스트 | 가치 |
|:--:|------|------|:--:|------|
| L1 | Pine 파서 (pynescript 래퍼) | `parser_adapter.py`, `ast_metrics.py` | 17 | AST + 에러 경로 |
| L2 | AST 분류기 (Track S/A/M) | `ast_classifier.py` | 12 | 호출 분포 프로파일 |
| L3 | Alert Hook v1 (condition-trace) | `alert_hook.py` | 29 | 메시지+조건, mismatch 감지 |
| L4 | 런타임 primitive (var/varip) | `runtime/persistent.py` | 15 | bar lifecycle |
| L7 | AST content 추출 | `ast_extractor.py` | 21 | strategy kwargs + inputs |
| **L8** | **Interpreter** | `interpreter.py` | 21 | 표현식+문장 tree-walker |
| **L9** | **stdlib ta.***  | `stdlib.py` | 13+3 | 11개 지표 + user var series |
| **L10** | **strategy.*** | `strategy_state.py` | 13+7 | 포지션/체결/PnL + pending stop |
| Integration | 통합 POC + E2E | 3 파일 | 17 | MA cross + **s1_pbr E2E** |
| **합계** | **9 source / 10 test / 4 fixture** | — | **169 PASS** | ruff/mypy clean |

Week 3 추가 (+17 tests):
- ta.pivothigh / pivotlow (4): 3 단위 + 1 Pine 통합
- strategy.entry(stop=) pending order (7): long/short fill, 미도달, same-bar 방지, re-issue, mintick 조합
- **s1_pbr E2E (6)**: 파싱 + strict 완주 + pivot 감지 + stop 체결 + 기존 pine/ 대조

---

## 3. 6 corpus × 레이어 최종 매트릭스

| Corpus | Track | L1 파싱 | L8 실행 | L9 ta.* | L10 strategy.* | 상태 |
|:---|:---:|:---:|:---:|:---:|:---:|:---|
| **s1_pbr** (v6) | S | ✅ 24/231 | ✅ **완주** | pivot 지원 | **BUY STOP 체결 ✅** | **Week 3 E2E 완료** |
| s2_utbot (v5) | S | ✅ 27/734 | ⚠️ heikin-ashi 필요 | sma/ema | market order | Week 4+ |
| s3_rsid (v5) | S | ✅ 32/1245 | ⚠️ divergence 로직 | rsi/pivot | entry/close | Week 4+ |
| i1_utbot (v4) | A | ✅ 25/587 | ✅ indicator 완주 | atr | N/A | — |
| i2_luxalgo (v5) | A | ✅ 30/822 | ⚠️ line.get_price 필요 | 대부분 지원 | N/A | 렌더링 필요 |
| i3_drfx (v5) | A | ✅ 40/10289 | ⚠️ 79 render + 8 security | 대부분 | N/A | 렌더링 + MTF |

**실행 가능: 2/6 (s1_pbr, i1_utbot)** — Sprint 8a Tier-0 최소 증명 충족
**Week 4+ 범위: 4/6** (렌더링 scope A, heikin-ashi, MTF 등)

---

## 4. ADR-011 §9 가정 최종 판정

| # | 가정 | 최종 판정 | 근거 |
|:--:|---|:--:|---|
| **A1** | Track S/A/M 비율 20~30/40~50/20~30% | 🟡 **유보** | N=6에서 S 50%/A 50%/M 0%. TV 15~20개 프로파일링 필요 |
| **A2** | PyneCore `trail_points` 지원 | ✅ **N/A** | #19 PR로 H2+ 이연 |
| **A3** | Alert 분류기 >80% 정확도 | ✅ **강하게 실증** | 10/10 분류 + i3 #2 mismatch 자동 감지 |
| **A4 (신규)** | pine_v2 TV 실전 전략 실행 가능 | ✅ **실증** | s1_pbr.pine 완주 + 기존 pine/ 대조 |

### 신뢰도 추이
| 시점 | 신뢰도 | 비고 |
|:---|:---:|:---|
| ADR-011 v1 초기 | 8/10 | Phase -1 실측 전 |
| Phase -1 (#19 PR) | 9/10 | A2/A3 실증 |
| Week 1 Foundation | 9.2/10 | Alert Hook v1 |
| Week 2 (합성 E2E) | 9.5/10 | MA crossover 실행 |
| **Week 3 (s1_pbr E2E) ← 현재** | **9.7/10** | 실전 TV 전략 완주 |
| Week 4+ (렌더링 + 6/6) | 9.8/10 예상 | 남은 실전 커버리지 |

---

## 5. 커밋 구성 — Week 1-3 전체

| Week | Day | Commit | 내용 | +Tests |
|:---:|:---:|:---:|---|:---:|
| 1 | 1 | `fb9d318` | pynescript scaffold | 7 |
| 1 | 2 | `ec1175a` | AST classifier | 12 |
| 1 | 3 | `92a5af9` | Alert Hook v0 | 24 |
| 1 | 4 | `3a5896f` | PersistentStore | 15 |
| 1 | 5 | `7352345` | 보고서 v1.0 | — |
| 1 | 6 | `4f278d8` | Alert Hook v1 condition-trace | +5 |
| 1 | 7 | `725b035` | Content extractor | 21 |
| 1 | 8 | `7cc3225` | L1 에러 + 통합 POC | 15 |
| 1 | 8b | `2a428cd` | 보고서 v1.1 | — |
| **2** | 9-10 | `3e217d5` | **Interpreter + event loop** | 21 |
| **2** | 11 | `22f163a` | **ta.* stdlib + var series** | 13 |
| **2** | 12-13 | `ffc6ee9` | **strategy.* + E2E MA crossover** | 19 |
| **2** | 14 | `5b82381` | 보고서 v2.0 | — |
| **3** | 15 | `589c13e` | **pivot + stop order + s1_pbr E2E** | **17** |
| **3** | 16 | `d297181` | 보고서 파일명 변경 | — |
| **3** | 16 | (본 커밋) | 최종 보고서 v3.0 | — |

**누적 테스트: 169 pine_v2 + 526 기존 regression** · ruff/mypy clean · pynescript import 6 파일 격리 · 기존 `pine/` touch 0 lines

---

## 6. 지원 범위 vs 이연 항목 (H1 MVP 기준)

### ✅ 구현 완료 (Week 1-3)

**Pine 구문:**
- 모든 주요 표현식: 산술/비교/논리/ternary/unary/subscript
- 문장: Assign/ReAssign/If-else + top-level Expr(If) 언래핑
- User 변수 series history (`myvar[n]`)
- built-in series: open/high/low/close/volume/bar_index/na/true/false

**Pine stdlib (11개):**
- ta.sma, ta.ema, ta.atr, ta.rsi, ta.highest, ta.lowest, ta.change
- ta.crossover, ta.crossunder
- **ta.pivothigh, ta.pivotlow** (Week 3)
- na, nz

**strategy.*:**
- strategy.entry (long/short, 시장가, **stop=** Week 3)
- strategy.close, strategy.close_all
- strategy.position_size, strategy.position_avg_price
- strategy.long/short 상수
- 시장가 + BUY/SELL STOP OCO 체결 (다음 bar price cross)
- 중복 id 재진입 override
- 미지원 kwarg 경고 기록

**메타 기능:**
- Alert Hook 추출 + 분류 (메시지 + 조건 + mismatch 자동 감지)
- AST content 추출 (strategy kwargs + inputs + var decls)
- Track S/A/M 자동 판정
- Pine v4 `study()` alias 지원
- syminfo.mintick 상수 (기본 0.01)

### ⏸️ Week 4+ 이연

**실전 corpus 완주 (s2/s3/i2/i3):**
- heikin-ashi OHLC 별도 series 계산 (s2_utbot)
- RSI divergence 복합 로직 (s3_rsid)
- 렌더링 범위 A — box/label/line/table 좌표 getter (i2_luxalgo `line.get_price`, i3_drfx 79 calls)
- request.security MTF (i3_drfx 8회) — H2+ 이연

**기타:**
- strategy.entry(limit=) 지정가
- trail_points, qty_percent (분할익절), pyramiding (ADR-011 #19 H2+)
- 수수료/슬리피지 모델
- 다중 시간프레임 (MTF) 병렬 실행

---

## 7. Week 4+ 로드맵 (Sprint 8b 전제)

1. **렌더링 범위 A** (3-5일) — box/label/line/table 좌표 getter. i2_luxalgo `line.get_price()` 지원. i3_drfx 79 calls 모두 NOP 없이 완주
2. **6 corpus 완주** (1주) — 나머지 4 corpus도 pine_v2로 실행. 실패 원인별 stdlib 확장 루프
3. **기존 pine/ 교체** — 라우터·서비스를 pine_v2로 전환. 하위 호환 어댑터
4. **DB 스키마** — Trade → PostgreSQL trades 테이블 매핑
5. **API endpoint** — `/api/v1/strategies/{id}/backtest-v2`
6. **TV 15-20개 프로파일링** — ADR-011 §9 A1 가정 실증 + 신뢰도 9.8로

예상 추가 2-3주.

---

## 8. 라이선스 엄수 재확인

**pynescript (LGPL-3.0):**
- PyPI pinned 의존성 `==0.3.0`
- import 격리: `parser_adapter.py`, `ast_metrics.py`, `ast_classifier.py`, `alert_hook.py`, `ast_extractor.py`, `interpreter.py` **6 파일만**
- 소스 copy 없음 (공개 API만 호출)

**PyneCore (Apache 2.0):**
- `transformers/persistent.py` **의미론 참조 이식** (재설계) — 코드 직접 copy 없음
- `NOTICE` 예정 항목 이미 기록

**기존 pine/ 모듈:**
- `backend/src/strategy/pine/` touch **0 lines** (dogfood 복구 경로 보호)

---

## 9. 참조

- [ADR-011 Pine Execution Strategy v4](011-pine-execution-strategy-v4.md)
- [ADR-011 Phase -1 amendment (#19, merged)](https://github.com/woosung-dev/quantbridge/pull/19)
- [Phase -1 findings](../../.gstack/experiments/phase-minus-1-drfx/output/phase-1-findings.md)
- [pine-execution-architecture](../04_architecture/pine-execution-architecture.md)
- [pine_v2 README](../../backend/src/strategy/pine_v2/README.md)
- [NOTICE](../../NOTICE)
