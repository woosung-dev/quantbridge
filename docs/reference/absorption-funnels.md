<!-- E1~E6 흡수 펀넬 PRD. 기존 사용자 base 가 큰 6개 경쟁군에서 QB 로 옮길 1줄 미끼 + 검증 metric. -->

# QuantBridge — Absorption Funnels (E1~E6)

> **위치:** `docs/01_requirements/` Tier-0 — Sprint 48+ 흡수 펀넬 구현 PRD.
> **작성일:** 2026-05-09 (Sprint 47, 포화 시장 reframe 인사이트 기반)
> **철학:** 신규 사용자 _획득_ 보다 기존 사용자 _이탈 경로 설계_ 가 ROI 압도적. 포화 시장 = 검증된 수요 4중 (TAM/가격/페르소나/채널). 자세한 근거: 본 세션 인사이트 트리 v2 ④.
> **상위:** [`../00_project/positioning.md`](../00_project/positioning.md) (한 줄 카피), [`../00_project/competitive-landscape.md`](../00_project/competitive-landscape.md) (5+1 비교)

---

## 6 펀넬 한 페이지 요약

|   ID   | 출발지                                          |  TAM  |  ROI  |            Sprint 48+ 후보             |
| :----: | ----------------------------------------------- | :---: | :---: | :------------------------------------: |
| **E1** | freqtrade (50k★ Python 사용자)                  | ★★★★★ | ★★★★★ |         docs only (Sprint 47)          |
| **E2** | jesse (8k★ MIT, 유료벽 불만)                    |  ★★★  | ★★★★☆ |               docs only                |
| **E3** | TradingView Pine (수백만, "TV at home")         | ★★★★★ | ★★★★★ | **paste editor 구현 (Sprint 48 후보)** |
| **E4** | 3Commas/Cryptohopper/Coinrule (paid no-code)    | ★★★★  | ★★★☆☆ |             광고/SEO (H2+)             |
| **E5** | 인텔리퀀트/퀀터스 (KR 주식 SaaS)                |  ★★   | ★★★☆☆ |       한국어 가이드 (Sprint 48~)       |
| **E6** | LuxAlgo PineTS / PyneSys (Pine bridge OSS·SaaS) |  ★★   | ★★★☆☆ |      비교 페이지 (Sprint 47 docs)      |

---

## E1 — freqtrade 흡수 ★★★★★

### 페르소나

Python 가능, freqtrade YAML/Docker 환경 1년+ 운영, FreqAI 진입장벽에 막힘, web UI 약점 인지

### 페인포인트 (Reddit + GitHub issues 패턴)

- YAML config 50+ 옵션 학습곡선
- FreqAI ML 학습 데이터 준비 burden
- web UI = freqtrade-ui 별도 설치 + 기능 제한
- 거래소 stratum 변경 시 docker-compose 재기동 burden

### 미끼 카피 1줄

> **"freqtrade YAML 50+ 줄 → Pine Script 1줄 → pine_v2 직접 실행 (1:1 의미론)"**

### 검증 metric

- freqtrade 사용자 인터뷰 N=3 (Sprint 48 dogfood Phase 3)
- 마이그레이션 가이드 docs 페이지 view → click-through rate
- "freqtrade vs QB" 키워드 organic 검색 유입

### Sprint 48+ 구현 후보

- `docs/guides/migrate-from-freqtrade.md` — 1:1 매핑 표 + Pine Script 변환 예제 3개
- 본인 freqtrade 1주 운영 후 Pine Script 변환 회고 dev-log

---

## E2 — jesse 흡수 ★★★★☆

### 페르소나

Python developer, jesse "look-ahead bias zero" 카피에 끌려 가입, 유료 구독 강제 + 거래소 한정에 불만

### 페인포인트

- 유료 구독 (free trial 부재)
- 거래소 한정 (CCXT 미내장)
- 커뮤니티 작음 (8k★)
- Pine Script 미지원 (재작성 burden)

### 미끼 카피 1줄

> **"jesse 의 backtest 정합성 + Demo free + Pine Script 직접 + 한국 거래소 (Bybit/업빗)"**

### 검증 metric

- jesse 사용자 인터뷰 N=2
- "jesse alternative" SEO 페이지

### Sprint 48+ 구현 후보

- `docs/guides/migrate-from-jesse.md` — 전략 어휘 매핑 (jesse Strategy class → Pine indicator/strategy)

---

## E3 — TradingView Pine 흡수 ★★★★★ (TAM 가장 큼)

### 페르소나

TV Premium 사용자, Pine Script v5/v6 작성 가능, 백테스트 fee 누락 인지, 외부 자동매매 욕구 있으나 3Commas 등 black-box 신뢰 못 함

### 페인포인트 (Reddit r/algotrading 직접 인용)

- 832↑ "fees 누락" — TV 백테스트 vs 실거래 -15% 정확도
- 362↑ "TV at home" — 모두가 TV 대안 만들지만 못 떠남
- 383↑ "look-ahead bias" — Pine `request.security` lookahead 함정
- TV ToS 회색지대 webhook 불안

### 미끼 카피 1줄

> **"TradingView 전략을 _바꾸지 않고_ 외부에서 1:1 의미론으로 실행 + 진짜 fee/slippage + 24 metric Trust"**

### 검증 metric (Sprint 48 paste editor 구현 시)

- paste editor 첫 5초 funnel: paste → 결과 출력 시간 ≤ 5초
- 가입 없이 데모 → share link 발급 → 가입 전환 rate
- Reddit r/algotrading 게시글 미끼 → click-through rate

### Sprint 48+ 구현 후보 (3-5일, 코드 작업)

- `/play` 또는 `/quick-test` 랜딩 페이지 — Pine paste editor (가입 없이)
- 기본 OHLCV (BTC/USDT 1년) 자동 적용
- 24 metric + Surface Trust 가정박스 즉시 표시
- Share link 발급 → 이메일만 + share token (회원가입 별도)
- "TV 에서 가져와서 진짜 fee 로 5초 만에" UX

---

## E4 — 3Commas / Cryptohopper / Coinrule 흡수 ★★★☆☆

### 페르소나

no-code 선호, $29~99/mo paid 전환 의향 있음, 코드 작성 어려움, 전략 customization 한계 인지

### 페인포인트

- black-box (전략 내부 동작 불투명)
- fee/slippage 미보장 (백테스트 정확도 약함)
- TradingView signal 한정 (직접 backtest UI 부재)
- 환불 사고 history (사용자 trust 약함)

### 미끼 카피 1줄

> **"no-code 의 편의 + 코드의 정확성 + Trust 인프라 (24 metric 투명성)"**

### 검증 metric

- 인터뷰 N=2 (paid 사용자, 전환 의향)
- 가격 페이지 vs 3Commas/Cryptohopper bounce rate

### Sprint 48+ 구현 후보

- 가격 페이지 ($29 hypothesis vs 3Commas $29~99)
- "3Commas vs QB" 비교 페이지 (광고 SEO 수단)

---

## E5 — 인텔리퀀트 / 퀀터스 (한국 주식 SaaS) ★★★☆☆

### 페르소나

한국 retail 퀀트 (주식 위주), 크립토 확장 욕구, no-code 익숙, Pine Script 학습 의향 있음

### 페인포인트

- 주식만, 크립토 미지원
- Pine Script 생태계 분리

### 미끼 카피 1줄

> **"한국어 UX 그대로 + 크립토 + Pine 생태계 (전략 수만 개) + Bybit Demo"**

### 검증 metric

- 한국어 SEO 키워드 ("퀀트 자동매매 크립토" 등)
- 카톡 micro-cohort N=1~2 (한국 trader)

### Sprint 48+ 구현 후보

- 한국어 가이드 페이지 + Bybit Demo 한국어 안내
- 인텔리퀀트/퀀터스 사용자 대상 비교 콘텐츠

---

## E6 — LuxAlgo PineTS / PyneSys 흡수 ★★★☆☆

### 페르소나

Pine Script transpiler 영역에 이미 진입한 기술 친화 user, JS only / paid SaaS 한계 인지

### 페인포인트

- LuxAlgo PineTS: AGPL → SaaS 자동 발동 (상용 라이선스 부담), JS 생태계 격리
- PyneSys: paid (vendor lock), Pine v6 only, transpile 정확도 한계

### 미끼 카피 1줄

> **"AST 인터프리터 1:1 의미론 (transpile 아님) + Python 생태계 + OSS + Trust"**

### 검증 metric

- LuxAlgo / PyneSys GitHub issues / Discord 모니터
- "PineTS alternative" / "PyneSys alternative" SEO

### Sprint 48+ 구현 후보

- `docs/guides/why-not-transpile.md` — transpile vs interpret 본질 차이 (DrFX 650줄 + Phase -1 4 모델 변환 버그 evidence)

---

## Cross-cutting 영구 metric

- **펀넬 conversion funnel** — landing → demo → 가입 → backtest 1회 → 7일 retain. Beta 본격 진입 (BL-070~075) 시점에 측정 시작
- **카피 성공률** — 한 줄 카피 (positioning.md) view → click-through rate
- **Reddit / Twitter mention** — "QuantBridge" 자연어 mention 분기별 모니터

---

## 갱신 정책

- **분기별 review** — 각 펀넬 ROI 별점 재평가 (외부 OSS·SaaS 변동 반영)
- **dogfood Phase 2 결과 반영** — 1-2명 인터뷰에서 어떤 펀넬 페르소나가 검증되었나
- **Beta 본격 진입 시점** = E3 paste editor 구현 가능 시점 결정 (Sprint 48 candidate)
- **변경 시 의무:** `positioning.md` + `competitive-landscape.md` cross-update (LESSON-062 SSOT sync 의무)
