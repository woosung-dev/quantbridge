# QuantBridge — 프로젝트 비전

## 한 줄 요약

TradingView Pine Script 전략을 가져와 고급 백테스트 → 스트레스 테스트 → 데모 트레이딩 → 라이브 트레이딩으로 연결하는 웹 기반 퀀트 플랫폼.

## 문제 정의 (Why)

TradingView Pine Script로 전략을 작성한 사용자는 다음 단계에서 단절을 겪는다.

1. **TradingView 백테스터의 한계** — 슬리피지·수수료·자본 제약 모델이 단순하고, Monte Carlo / Walk-Forward 같은 스트레스 테스트가 없어 over-fit 여부 판단이 어렵다.
2. **거래소 자동화 단절** — Bybit/Binance에서 자동 실행하려면 Pine Script를 Python/JS로 다시 작성하거나, 3rd-party 봇(3Commas, Cryptohopper 등)에 종속되어야 한다.
3. **검증→실거래 사이의 신뢰 공백** — 백테스트가 잘 나와도 "실제 시장에서 어떤 슬리피지가 발생할지" 확인할 단계가 없다.

QuantBridge는 이 세 단절을 **하나의 파이프라인**으로 연결한다 — Pine Script를 그대로 임포트해서 동일 코드로 백테스트→데모→라이브를 수행한다.

## 핵심 가치

1. **쉬운 전략 임포트** — TradingView의 수천 개 공개 전략을 즉시 테스트 가능
2. **고급 검증** — TV 백테스터가 제공하지 못하는 Monte Carlo, Walk-Forward, 현실적 슬리피지/수수료 시뮬레이션
3. **실시간 검증** — 데모 트레이딩으로 백테스트 기대치와 실제 시장 사이의 괴리 측정
4. **원클릭 라이브 전환** — 동일 코드, URL만 변경하여 라이브 트레이딩
5. **(2026-05-04 Addendum) Auto-Loop 자동화** — Beat scheduler + Worker dispatch 로 dogfood/Beta 사용자가 매분 수동 개입 없이 평가→주문→close cycle 자동 실행 (Sprint 27 §0.5 dogfood Day 0-4 evidence: 26h+ 무중단, dispatch rate 1.0/min, 5 sessions 동시). **외부 노출 가능 핵심 신뢰 지표** — 처음 office-hours (Sprint 7c) 의 "curl/psql 감내" 가정이 dogfood 결과로 무효화, 자동화 필수성으로 승격. 상세: [`docs/dev-log/008-sprint7c-scope-decision.md`](../dev-log/008-sprint7c-scope-decision.md) "2026-05-04 Addendum"

## 4 신규 도메인 (Sprint 12-27 dogfood 부상, Sprint 28 office-hours 재진행 시 명시)

처음 vision (2026-04-14) 에는 미존재. dogfood 3개월 누적으로 부상한 cross-cutting 도메인:

1. **WebSocket Stability** — BL-001 / BL-011-016 6 항목. Sprint 12 metrics 정의 + Sprint 27 26h+ 무결.
2. **Auth Trust Layer** — 15 ADR + commit-spy. Sprint 13 dogfood 가 1185 backend tests 통과인데도 production bug 발견 (OrderService outer commit) = dogfood 가 진정한 검증.
3. **Auto-Loop 자동화** — Sprint 27 §0.5 first run 으로 외부 노출 가능 신뢰 지표 부상 (위 핵심 가치 §5 와 동일).
4. **Multi-account / symbol / timeframe Live Trading** — Sprint 26 PR #100. 두 ExchangeAccount + BTC/SOL + 1m/5m/15m/1h 혼합.

이 4 도메인이 Sprint 28 narrowest wedge 정의 (BL-141 / BL-140b / BL-004 = Beta 진입) 의 evidence base.

## 차별화 (Positioning)

> 자세한 비교 매트릭스는 [`requirements-overview.md`](../01_requirements/requirements-overview.md) §1 참조. 본 문서는 한 줄 결론만.

| 도구                                   | 강점                           | QuantBridge가 채우는 공백                 |
| -------------------------------------- | ------------------------------ | ----------------------------------------- |
| **TradingView**                        | 차트·Pine Script 작성 ergonomy | 백테스트 모델 단순, 거래소 자동 실행 없음 |
| **3Commas / Cryptohopper**             | 거래소 봇 운영                 | Pine Script 미지원, 백테스트 검증 약함    |
| **vectorbt / backtrader (라이브러리)** | 백테스트 정밀도                | Python 코딩 필요, UI/거래소 연결 없음     |
| **QuantConnect**                       | 풀 스택 퀀트                   | C#/Python 학습곡선, Pine 미지원           |

**QuantBridge =** TradingView UX × vectorbt 백테스트 정밀도 × 거래소 직결. **"TradingView의 Trust Layer"** `[/office-hours 2026-04-13 확정]`.

## 타겟 사용자

- TradingView에서 Pine Script를 사용하는 크립토 트레이더
- 고급 백테스팅 도구가 부족한 개인 퀀트
- Bybit/Binance에서 자동화 트레이딩을 원하는 트레이더

> 페르소나·Pain Point 상세는 [`requirements-overview.md`](../01_requirements/requirements-overview.md) §2 참조.

## 성공 지표 (KPI)

| 지표                                      | 목표                   |
| ----------------------------------------- | ---------------------- |
| Pine Script 파싱 성공률                   | 80%+ (주요 패턴)       |
| 단일 심볼 1Y/1H 백테스트                  | < 10초                 |
| 데모 주문 체결 레이턴시                   | < 2초                  |
| 백테스트 정확도 (vectorbt 직접 실행 대비) | 99%+                   |
| 임포트 → 첫 백테스트 결과                 | < 5분                  |
| 백테스트 → 데모 트레이딩                  | 3클릭 이내             |
| 데모 → 라이브 트레이딩                    | 2클릭 이내 (확인 포함) |

## MVP 범위 (Phase 1: Week 1-4)

- 프로젝트 스캐폴딩 (Next.js 16 + FastAPI + Docker)
- Clerk 인증
- Pine Script 파서 (Regex 기반 MVP)
- 기본 백테스트 엔진 (vectorbt, 단일 심볼)
- 전략 CRUD + 편집기 UI
- 백테스트 결과 리포트 UI

## Sprint 로드맵 요약 (기술 관점)

> 상세 진행 상황은 [`docs/TODO.md`](../TODO.md). 본 섹션은 Phase 단위 **기술** 로드맵 한눈에 보기.
> **제품 로드맵(Horizon × Pillars, 비즈니스·수익화·Launch 포함)**은 [`docs/00_project/roadmap.md`](./roadmap.md) 참조.

| Phase     | 기간 (계획) | 핵심 산출물                                             | 진행 상태                                              | Horizon 매핑 |
| --------- | ----------- | ------------------------------------------------------- | ------------------------------------------------------ | ------------ |
| Phase 0   | 1주         | 스캐폴딩 (Next.js 16 + FastAPI + Docker + Clerk)        | ✅ 2026-04-15 완료                                     | (pre-H1)     |
| Phase 1   | 4주         | Pine 파서 + 백테스트 + 전략 CRUD + 백테스트 리포트 BE   | ✅ Sprint 1~4 완료 (2026-04-16)                        | (pre-H1)     |
| Phase 1.5 | 2주         | Infra Hardening + market_data (TimescaleDB hypertable)  | ✅ Sprint 5 완료 (2026-04-16)                          | (pre-H1)     |
| Phase 2   | 4주         | 스트레스 테스트 + 파라미터 최적화                       | ⏳ Sprint 9~10                                         | **H2**       |
| Phase 3   | 4주         | 데모 트레이딩 (Bybit/Binance), 리스크 관리, Kill Switch | ✅ Sprint 6 완료 + Sprint 7a Futures 완료 (2026-04-17) | (pre-H1)     |
| Phase 4   | 4주         | 라이브 트레이딩, 멀티 거래소, 알림                      | 🔄 Sprint 7b/7c/8a/8b                                  | **H1**       |

> 본 Phase 표는 **기술 관점**의 로드맵이다. "언제 외부 공개할지 / 어떻게 수익화할지 / 어떤 규제 프레이밍을 쓸지" 같은 **제품 관점 결정**은 [`roadmap.md`](./roadmap.md) 참조.

## 비범위 (Out of Scope — MVP 명시 제외)

다음은 의식적으로 제외하거나 후순위로 미룬 항목이다. 변경은 ADR을 통해 기록한다.

- **Web3 / 온체인 자동매매** — 중앙화 거래소(Spot + Perpetual)에 한정
- **AI 전략 자동 생성** — Pine Script는 사용자가 작성/임포트. LLM이 전략을 만들어주지 않음
- **모바일 네이티브 앱** — 반응형 웹만
- **멀티 사용자 협업** — 전략 공유는 templates 단방향만, 실시간 공동 편집 없음
- **옵션·선물 외 파생상품** — Spot + Perpetual Futures 한정
- **알고리즘 마켓플레이스** — Phase 5+ 검토
- **회계·세무 리포트** — 외부 도구 연동 권장

## 핵심 비즈니스 규칙

본 비전을 코드로 옮길 때 반드시 지킬 규칙은 [`.claude/CLAUDE.md`](../../.claude/CLAUDE.md) §"QuantBridge 고유 규칙" 및 [`requirements-overview.md`](../01_requirements/requirements-overview.md) §8에 정리.

대표 원칙:

- 금융 숫자는 `Decimal` 사용 (`float` 금지)
- Pine Script → Python 변환 시 `exec()`/`eval()` 절대 금지 (ADR-003)
- Pine Script 미지원 함수 1개라도 포함 시 전체 "Unsupported" 반환 (ADR-003)
- OHLCV 데이터는 TimescaleDB hypertable 저장 (Sprint 5 도입, ADR-005도 참조)
- 거래소 API Key는 AES-256 암호화 저장 (평문 금지)

## 참조 문서

- **제품 로드맵** (Horizon × Pillars + 수익화 + Launch): [`roadmap.md`](./roadmap.md)
- 요구사항 상세: [`01_requirements/requirements-overview.md`](../01_requirements/requirements-overview.md), [`req-catalog.md`](../01_requirements/req-catalog.md)
- 도메인 모델: [`02_domain/domain-overview.md`](../02_domain/domain-overview.md)
- 시스템 설계: [`04_architecture/system-architecture.md`](../04_architecture/system-architecture.md)
- 의사결정 트레일: [`dev-log/`](../dev-log/) (ADR-001~012)
- 작업 추적: [`TODO.md`](../TODO.md)

## 변경 이력

- **2026-04-15** — 초안 작성 (한 줄 요약 + 핵심 가치 + KPI + Phase 1 MVP)
- **2026-04-16** — 가벼운 보강 (Sprint 5 Stage A docs sync). 문제 정의·차별화·Sprint 로드맵·Out of Scope·참조 문서 섹션 추가
- **2026-04-17** — Phase 로드맵에 Horizon 매핑 열 추가 + 제품 로드맵([`roadmap.md`](./roadmap.md)) 링크 추가 ([ADR-010b](../dev-log/010b-product-roadmap.md))
