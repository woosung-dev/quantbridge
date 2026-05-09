<!-- Trust 한 줄 카피 finalization + 근거. vision.md 차별화 4개 매트릭스 의 상세화 layer. -->

# QuantBridge — Positioning Statement

> **본 문서 위치:** `docs/00_project/` Tier-0 — 프로젝트 외부 노출 카피의 SSOT.
> **작성일:** 2026-05-09 (Sprint 47 kickoff)
> **상위 문서:** [`vision.md`](vision.md) §차별화 — 본 문서는 그 _상세화·운영 layer_
> **하위 문서:** [`competitive-landscape.md`](competitive-landscape.md) (5+1 비교), [`../01_requirements/absorption-funnels.md`](../01_requirements/absorption-funnels.md) (E1~E6 흡수 펀넬)

---

## 한 줄 카피 (Final)

### 영문 (1순위)

> **"Run TradingView Pine on your own infrastructure — 1:1 semantics, real fees, full trust."**

### 한국어 (1순위)

> **"파인스크립트, 그대로 — 진짜 수수료까지 똑같이."**

---

## 왜 이 카피인가 (3 layer 근거)

### Layer 1 — Reddit r/algotrading 탑보트 페인포인트 직격

| 페인포인트                              | 정확한 인용                                                           | 카피 매핑                                                      |
| --------------------------------------- | --------------------------------------------------------------------- | -------------------------------------------------------------- |
| 832↑ "fees 누락"                        | "This is what happens when you DO NOT include Fees in your backtests" | **"real fees"** / "진짜 수수료"                                |
| 362↑ "TV 의존"                          | "Mom, I want TradingView, no we have TradingView at home"             | **"on your own infrastructure"** / "그대로" (TV 그대로 가져옴) |
| 521↑ "overfit" + 383↑ "look-ahead bias" | "I ADMIT IT. I OVERFIT" / "epic look-ahead bias"                      | **"full trust"** (Surface Trust Layer)                         |

### Layer 2 — pine_v2 의 _수학적_ 차별점 (다른 카피로는 표현 불가)

- **"1:1 semantics"** — pine_v2 = AST 인터프리터 + bar-by-bar 이벤트 루프. vectorized 마스크 방식 (freqtrade/jesse) 이나 transpile (PyneSys) 로는 본질적 불가
- 같은 카피 영역에 진입하려면 기술 자산이 동일해야 함 — 그런 OSS·SaaS 가 0개 (자세한 비교 → `competitive-landscape.md`)
- ADR-011 §6/§8 + Sprint 8a Final Report 의 결정이 이 한 줄 카피의 _수학적_ 정당화 근거

### Layer 3 — 직접 경쟁 카피 cross-cutting

| 경쟁 카피                                         | 약점                                           | QB 카피의 우위                                          |
| ------------------------------------------------- | ---------------------------------------------- | ------------------------------------------------------- |
| LuxAlgo PineTS: "Run Pine Script Anywhere"        | JS 만, AGPL/Commercial, Trust 약함             | "1:1 semantics + real fees + full trust" 추가           |
| Jesse: "look-ahead bias zero"                     | 단일 차원, vectorized 한계                     | "1:1 semantics" 가 더 포괄적 (look-ahead 는 그 sub-set) |
| Freqtrade: "Free, open source crypto trading bot" | feature list 카피, 차별화 약함                 | "TradingView Pine + Trust" = 명확한 좌표                |
| 3Commas: "TradingView Automated Trading Bots"     | webhook signal 한정, fee/slippage 미보장       | "1:1 semantics" + "real fees"                           |
| PyneSys: "Pine Script to Python Compiler"         | transpile 정확도 ≠ 1:1, paid SaaS, vendor lock | "Run Pine on your own infra" + OSS 인프라 + Trust       |

---

## Sub-카피 후보 (상황별 활용)

### 컨텍스트별 변형

- **개발자 어필:** "The only Pine Script engine that matches TradingView bar-by-bar."
- **Trust 강조:** "백테스트가 거짓말하지 않는 유일한 곳."
- **거부형 (negative space):** "Pine to Production — without LLMs, transpilers, or guesswork."
- **한국 데모-first:** "Bybit 데모로 먼저, 진짜 수수료 그대로."

### 카피 사용 가이드

| 채널                      | 권장 카피                       |
| ------------------------- | ------------------------------- |
| 랜딩 페이지 hero          | 1순위 영문                      |
| 한국 카톡 micro-cohort    | 1순위 한국어                    |
| r/algotrading 게시글 hook | "real fees" 강조 sub-카피       |
| TradingView 커뮤니티      | "Run Pine ... on your own" 강조 |
| Build-in-Public 트윗      | dogfood 결과 + 1순위 카피       |

---

## 정합성 cross-check

- ✅ `vision.md` §"TradingView의 Trust Layer" 와 정합 — 본 카피가 그 _외부 노출 형태_
- ✅ `roadmap.md` Pillar 우선순위 (Trust ≥ Scale > Monetize) 와 정합 — "full trust" 가 Pillar 1 직접 표현
- ✅ Sprint 28+ Surface Trust 4 sub-pillar (가정박스 / 차트 / 24 metric / 거래목록) 자산 = 카피 "full trust" 의 _증명 장치_
- ✅ pine_v2 SSOT (AGENTS.md PR #236 정정 후) = 카피 "1:1 semantics" 의 _수학적 기반_

---

## 갱신 정책

- **분기별 review** — 외부 OSS·SaaS 의 카피·라이선스·기능 변동 추적 (PineTS / PyneSys 가 가장 risk 높음)
- **dogfood Phase 2 결과 반영** — 1-2명 micro-cohort 인터뷰에서 카피 공감도 측정 → finalization 또는 변경
- **Beta 본격 진입 (BL-070~075) 시점** = 카피 lock-in 1회 (도메인 + 랜딩 hero 적용)
- **변경 시 의무:** 본 파일 + `vision.md` + `competitive-landscape.md` + `absorption-funnels.md` 4 파일 cross-update (LESSON-062 SSOT sync 의무 정신)
