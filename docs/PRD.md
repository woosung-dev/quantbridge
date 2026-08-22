# QuantBridge — PRD (제품 정의 · 범위 · 현재 위치)

> **이 문서가 답하는 것** — 무엇을 만드나 / 누구를 위해 / 무엇을 **안** 하나 / 지금 어디까지 왔나 / 다음은 뭔가.
> 「왜 그렇게 정했나」는 [`adr/`](./adr/), 「지금 실행할 일」은 [`status.md`](./status.md),
> 「열린 결함」은 [`backlog.md`](./backlog.md), 「무엇이 반증됐나」는 [`lessons.md`](./lessons.md) 다.
>
> ★**2026-08-23 통합.** `domain/vision.md`(144줄) · `roadmap.md`(550줄) · `domain/requirements-overview.md`(46줄)
> 셋이 같은 질문(「제품이 뭔가」)을 나눠 답하고 있어 **이 한 파일로 합쳤다.** 원문 = `git show 4c65bc0e:docs/`.
> 합친 이유는 실측이다 — roadmap 의 미완 체크박스 **87개 중 79개가 원장에 없는 죽은 BL** 을 가리키고 있었고,
> 머리 20줄이 「그 앞:」 회차 이력이었다. living 체크리스트가 changelog 가 된 것이다.

---

## 0. 지금 유효한 제품 결정 (2026-08-23 사용자 결정)

이 셋이 아래 모든 범위 문장을 지배한다.

| # | 결정 | 따라 나오는 것 |
| --- | --- | --- |
| ⑴ | **실자금(mainnet) 안 간다** | 계정 모드는 **Bybit Demo 만**. money-path 「실자금 정밀도」 축은 닫혀 있다 |
| ⑵ | **Beta 외부 공개 당분간 안 연다** | **실사용자 0명**이 전제다. waitlist 파이프라인은 키만 넣으면 열리지만 열지 않는다 |
| ⑶ | **멀티 거래소 안 한다** | **Bybit 하나**. OKX·Binance 연결 코드는 0건이고 그대로 둔다 |

★**하나가 뒤집히면 `git show 21e40d5c:docs/backlog*.md` 에서 해당 축을 되살려라 — 다시 쓰지 마라.**

---

## 1. 제품

TradingView Pine Script 전략을 가져와 **같은 코드로** 백테스트 → 스트레스 테스트 → 데모 트레이딩까지 연결하는 웹 퀀트 플랫폼.

**메우는 단절 셋:**

1. **TV 백테스터의 한계** — 슬리피지·수수료·자본 제약 모델이 단순하고 Monte Carlo / Walk-Forward 가 없어 over-fit 판단이 어렵다.
2. **거래소 자동화 단절** — 자동 실행하려면 Pine 을 Python/JS 로 다시 쓰거나 3rd-party 봇에 종속된다.
3. **검증→실거래의 신뢰 공백** — 백테스트가 좋아도 실제 슬리피지를 확인할 단계가 없다.

**한 줄 포지셔닝:** TradingView UX × vectorbt 백테스트 정밀도 × 거래소 직결 = **"TradingView 의 Trust Layer"**.

**핵심은 기능 수가 아니라 결과와 가정이 얼마나 정직하게 보이는가다.**

## 2. 사용자 흐름

1. **Import** — Pine Script 등록. 지원 범위·degrade 여부를 **먼저** 확인한다.
2. **Verify** — `pine_v2` 인터프리터로 백테스트. 필요하면 스트레스 테스트·최적화.
3. **Operate** — 검증한 전략을 **Bybit Demo** 계정에서 자동 실행. 주문·포지션·Kill Switch 관찰.

## 3. 현재 범위 — 지금 약속하는 것

| 영역 | 계약 | 상세 정본 |
| --- | --- | --- |
| 전략 | Pine 등록·파싱·지원 범위 판정. **미지원 항목이 하나라도 있으면 부분 실행하지 않는다** | [`domain/domain-overview.md`](./domain/domain-overview.md) · [`domain/supported-indicators.md`](./domain/supported-indicators.md) |
| 백테스트 | `pine_v2` bar-by-bar 실행 결과와 리포트 | [`architecture/pine-execution-architecture.md`](./architecture/pine-execution-architecture.md) |
| 검증 확장 | Monte Carlo · Walk-Forward · 파라미터 안정성 · 최적화 — 같은 백테스트 계약 재사용 | [`architecture/system-architecture.md`](./architecture/system-architecture.md) |
| 시장 데이터 | OHLCV 수집 + TimescaleDB hypertable 보관 | [`architecture/data-flow.md`](./architecture/data-flow.md) |
| 트레이딩 | **Bybit Demo 만**. 주문 전 리스크 평가 + Kill Switch | [`domain/state-machines.md`](./domain/state-machines.md) · [`api/endpoints.md`](./api/endpoints.md) |
| 신뢰·안전 | 실행·지원 범위·비용·리스크를 숨기지 않는다. Pine 회귀는 Trust Layer CI 로 방어 | [`architecture/trust-layer-architecture.md`](./architecture/trust-layer-architecture.md) |

## 4. 비범위 — 의식적으로 안 하는 것

**결정 3건이 닫은 것** (§0): 실자금/mainnet · 외부 Beta 공개 · 멀티 거래소(OKX·Binance).

**설계 단계에서 제외한 것:**

- **Web3 / 온체인 자동매매** — 중앙화 거래소(Spot + Perpetual) 한정
- **AI 전략 자동 생성** — Pine 은 사용자가 작성/임포트한다. LLM 이 전략을 만들어주지 않는다
- **모바일 네이티브 앱** — 반응형 웹만
- **멀티 사용자 협업** — 실시간 공동 편집 없음
- **옵션 등 파생상품** — Spot + Perpetual Futures 한정
- **알고리즘 마켓플레이스 · 회계/세무 리포트** — 외부 도구 연동 권장

변경은 **ADR 로 기록**한다. 산문으로 슬쩍 넓히지 마라.

## 5. 성공 지표

| 지표 | 목표 |
| --- | --- |
| Pine Script 파싱 성공률 | 80%+ (주요 패턴) |
| 단일 심볼 1Y/1H 백테스트 | < 10초 |
| 데모 주문 체결 레이턴시 | < 2초 |
| 백테스트 정확도 (vectorbt 직접 실행 대비) | 99%+ |
| 임포트 → 첫 백테스트 결과 | < 5분 |
| 백테스트 → 데모 트레이딩 | 3클릭 이내 |

★**이 표는 목표지 실측이 아니다.** 실측하려면 그 회차에 재고 `lessons.md` 에 남겨라.

## 6. 지금 어디까지 왔나 (2026-08-23)

**작동하는 것** — Pine v2 AST 인터프리터 · 백테스트 · 스트레스 테스트 · 옵티마이저 · Bybit Demo 라이브 트레이딩(Auto-Loop 포함) · TimescaleDB 시장 데이터 · self-host Better Auth([ADR-034]) · 프로덕션 배포(`qb.woosung.dev` / `qb-api.woosung.dev`, Cloudflare Access 뒤).

**안 여는 것** — waitlist 초대 파이프라인은 **코드·테스트·화면 완비**이고 서버에 키 3종만 넣으면 열린다. 결정 ⑵ 로 **열지 않는다**. 절차 = [`operations/waitlist-activation.md`](./operations/waitlist-activation.md).

**열린 결함** — [`backlog.md`](./backlog.md) 의 ACTIVE 16건. 전부 **데모 라이브의 현존 결함**이다(청산 원장 2배 적재 · StrEnum 크래시 · 409 계약 불일치 등). 실자금 정밀도 항목은 결정 ⑴ 로 닫혔다.

**다음에 할 일** — [`status.md`](./status.md) 의 살아 있는 `다음 행동 =` **하나**가 유일한 진입점이다. 그 뒤 개발 항목은 ⓪ 표에서 고른다.

## 7. 핵심 비즈니스 규칙 (요약)

전문은 [`AGENTS.md`](../AGENTS.md) · [`apps/api/AGENTS.md`](../apps/api/AGENTS.md).

- 금융 숫자는 `Decimal` — `float` 금지
- Pine → 실행 시 `exec()`/`eval()` 절대 금지 ([ADR-003])
- Pine 미지원 함수 1개라도 포함 시 전체 "Unsupported" ([ADR-003])
- OHLCV 는 TimescaleDB hypertable
- 거래소 API Key 는 AES-256(Fernet) 암호화 저장 — 평문 컬럼 금지

## 8. 변경 규칙

제품 범위가 바뀌면 **이 문서를 짧게 고치고** 같은 세션에 다음 중 **정확히 한 곳**을 갱신한다.

| 무엇이 바뀌었나 | 어디 |
| --- | --- |
| 지금 실행할 일 | `status.md` |
| 열린 위험·결함 | `backlog.md` |
| 왜 그렇게 정했나 | `adr/` — **결정 / 이유 / 트레이드오프 3줄**. 회차 발견을 여기 쌓지 마라 |
| 무엇이 반증됐나 | `lessons.md` |
| 오래 유지할 구현 계약 | `architecture/`·`domain/`·`api/`·`development/`·`operations/` |

★**끝난 회차 기록은 어느 문서에도 쌓지 않는다** — 커밋 메시지와 git log 가 정본이다.
이 규칙이 없어서 `roadmap.md` 가 550줄, `status.md` 가 124KB, ADR 하나가 72KB 가 됐다(2026-08-23 실측).
