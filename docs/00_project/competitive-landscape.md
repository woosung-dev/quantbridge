<!-- 5+1 OSS·SaaS 비교 + pine_v2 단독 카테고리 시각화. positioning.md 의 근거 layer. -->

# QuantBridge — Competitive Landscape (5+1)

> **작성일:** 2026-05-09 (Sprint 47, 이번 세션 검색 데이터 기반)
> **상위:** [`positioning.md`](positioning.md) — 본 문서가 한 줄 카피의 비교 근거 layer
> **하위:** [`../01_requirements/absorption-funnels.md`](../01_requirements/absorption-funnels.md) — 각 경쟁군에서 사용자를 흡수하는 펀넬 PRD
> **출처:** GitHub API (2026-05-09), Reddit r/algotrading top posts (1년), 각 OSS README, ADR-011 §6/§8

---

## 한 페이지 결론

> **pine_v2 (QB 자체) 는 PineTS (JS transpile) / PyneSys (Python transpile) / jesse (vectorized) / freqtrade (vectorized + ML) / 3Commas (no-code SaaS) 와 _카테고리 자체가 다름_. 직접 경쟁 0 — 기술 좌표가 단독.**

---

## 카테고리 다이어그램

```
[Pine 전략을 외부에서 실행하는 방식]
│
├── 방식 1: LLM 원샷 변환 (GPT/Opus/Gemini)
│   └── IBM ICSE 2024: 정확률 2.1~47.3%, Phase -1 실측 4 모델 모두 다른 버그 ❌
│
├── 방식 2: Python transpile  →  PyneSys (SaaS, Pine v6 only, paid)
│   └── transpile 정확도 ≠ 1:1 의미론, vendor lock-in
│
├── 방식 3: JS transpile      →  LuxAlgo PineTS (TS, AGPL+Commercial, 346★)
│   └── JS 생태계만, Python backtest 격리, AGPL → SaaS 자동 발동
│
├── 방식 4: vectorized signals →  freqtrade (50k★) / jesse (7.9k★) / vectorbt (7k★)
│   └── entries/exits 마스크 → Pine bar-by-bar 와 mismatch (carry-forward 위험)
│
├── 방식 5: SaaS no-code      →  3Commas / Cryptohopper / Coinrule (paid)
│   └── webhook signal 한정, fee/slippage 미보장, black-box
│
└── 방식 6: AST 인터프리터    →  ⭐ pine_v2 (QB 자체, ADR-011, Sprint 8a)
    ├── pynescript 0.3.0 포크 (LGPL, 6 파일 격리)
    ├── PyneCore transformers/ 참조 이식 (Apache 2.0)
    ├── alert hook 으로 매매 의도 결정론적 추출 (LLM 환각 0)
    ├── strict=True bar-level 오류 즉시 raise
    └── 169 pine_v2 tests + 6/6 corpus 파싱 + s1_pbr E2E 완주
```

---

## 6개 axis 비교표

| Axis                       | LuxAlgo PineTS        | PyneSys             | jesse                       | freqtrade        | 3Commas           | **pine_v2 (QB)**                                                              |
| -------------------------- | --------------------- | ------------------- | --------------------------- | ---------------- | ----------------- | ----------------------------------------------------------------------------- |
| **GitHub Stars**           | 346★                  | SaaS (비공개)       | 7.9k★                       | 50k★             | SaaS              | OSS 미공개 (자체)                                                             |
| **언어/런타임**            | TypeScript            | Python              | Python                      | Python           | Cloud             | Python                                                                        |
| **실행 모델**              | JS transpile          | Python transpile    | vectorized                  | vectorized + ML  | webhook signal    | **AST 인터프리터 + bar-by-bar**                                               |
| **Pine 의미론 정합**       | partial (transpile)   | partial (transpile) | N/A (재구현)                | N/A (재구현)     | N/A (signal only) | **1:1 (AST tree-walker)**                                                     |
| **fee/slippage 정확도**    | 사용자 책임           | 사용자 책임         | 양호                        | 양호 (FreqAI ML) | 미보장            | **vectorbt 동등 + 1:1 의미론**                                                |
| **Trust 측정**             | ❌ 없음               | ❌ 없음             | "look-ahead bias zero" 카피 | 약함             | ❌ 없음           | **Surface Trust 4 sub-pillar + 24 metric + Coverage Analyzer + Mutation 8/8** |
| **거래소 연결**            | ❌ 미내장             | ❌ 미내장           | 한정                        | CCXT 30+         | 거래소 직결       | CCXT (Bybit Demo H1, mainnet H2+)                                             |
| **라이선스**               | AGPL-3.0 / Commercial | Closed (paid SaaS)  | MIT (subscription req)      | GPL-3.0          | 상용              | OSS H2 공개 예정                                                              |
| **가격**                   | OSS / 상용            | $8~45/mo            | 구독 강제                   | Free             | $29~99/mo         | Demo free / Live ~$29 (가설)                                                  |
| **Pine Script 직접 paste** | ✅ (transpile)        | ✅ (transpile)      | ❌                          | ❌               | ❌ (webhook only) | ✅ (AST 직접 실행)                                                            |

---

## 각 경쟁군 강·약점 + QB 우위

### LuxAlgo PineTS (가장 가까운 카테고리)

- **강점:** Pine v5/v6 native syntax, JS 생태계, LuxAlgo 커뮤니티 백킹, npm 배포
- **약점:** JS only (Python ML/백테스트 격리), AGPL → SaaS 자동 발동 (상용 라이선스 필요), Trust 측정 부재
- **QB 우위:** Python 생태계 + Trust Layer + Bybit/CCXT 직결 + 의미론 1:1 (transpile vs interpret 본질 차이)

### PyneSys

- **강점:** Pine v6 → Python 컨버터, Python 생태계 호환
- **약점:** transpile 정확도 한계, paid SaaS (vendor lock), Pine v4/v5 미지원
- **QB 우위:** OSS 인프라 + 1:1 의미론 + 라이선스 자유

### jesse

- **강점:** "look-ahead bias zero" 강력한 카피, MIT, Python developer experience 우수
- **약점:** Pine Script 미지원 (재작성 필요), 유료 구독 강제, 거래소 한정, 커뮤니티 작음
- **QB 우위:** Pine 직접 실행 + Demo free + 더 포괄적 Trust ("look-ahead bias zero" 는 1:1 의미론의 sub-set)

### freqtrade (TAM 가장 큰 풀)

- **강점:** 50k★ 압도적 커뮤니티, FreqAI ML, 30+ 거래소, 활발한 개발
- **약점:** YAML/Docker 진입장벽, Pine Script 미지원, web UI 약함, "fees 누락" 페인포인트 (Reddit 832↑)
- **QB 우위:** Pine 직접 실행 + UX 폴리시 (Sprint 41~46 prototype-grade) + Trust 측정 + 1:1 fee 정확도

### 3Commas / Cryptohopper / Coinrule (no-code SaaS)

- **강점:** no-code, GUI, 설치 불필요, 기존 사용자 base 큼 ($19~99/mo paid 전환)
- **약점:** Pine Script 부분 지원 (webhook signal only), black-box, fee/slippage 불투명, 전략 customization 한계
- **QB 우위:** Pine 직접 실행 + 코드 정확성 + Trust transparency + 가격 동등 ($29 가설)

---

## Reddit r/algotrading 페인포인트 매핑 (top voted, 1년)

| 페인포인트            | 표 votes | 표면화 OSS·SaaS               | QB 대응 자산                                       |
| --------------------- | -------- | ----------------------------- | -------------------------------------------------- |
| Fees not included     | 832↑     | freqtrade/jesse 일부 backtest | 1:1 의미론 + vectorbt 0.3% 정합                    |
| TradingView at home   | 362↑     | LuxAlgo PineTS 부분           | "Run Pine on your own infrastructure"              |
| Look-ahead bias       | 383↑     | jesse 카피                    | strict=True bar-level raise + Coverage Analyzer    |
| Overfit               | 521↑     | 모든 OSS                      | Walk-Forward + Monte Carlo (H2 Stress Test 도메인) |
| "PM me for code" 사기 | 896↑     | TV signal seller              | 코드 + 백테스트 + 24 metric 투명성                 |

---

## 갱신 정책

- **분기별:** GitHub stars / 라이선스 / 가격 변동 cross-check (PineTS, PyneSys 가 risk 높음)
- **변경 시:** [`positioning.md`](positioning.md) §정합성 cross-check 동시 갱신 (LESSON-062 SSOT sync 의무)
- **데이터 출처 변동 시:** Reddit posts 갱신 (1년 단위)
