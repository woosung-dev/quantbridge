# Sprint 7a: Bybit Futures + Cross Margin — 사전 결정 기록

> **작성일:** 2026-04-17
> **작성 세션:** Sprint 6 SDD 세션 (PR #9 머지 후)
> **상태:** ✅ 구현 완료 (2026-04-17)
> **구현 브랜치:** feat/sprint7a-futures
> **관련 커밋:** e1126a0 (T1), 07d4ed7 (T2), 67414e9 (T2 review fix), fe82ca2 (T3),
> T4 커밋은 이 파일과 함께 기록 (`git log feat/sprint7a-futures` 참고)

---

## 배경

Sprint 6 완료 후 다음 확장으로 **Futures + Cross Margin** 지원을 결정.
현재 `BybitDemoProvider`는 Spot 전용 (`defaultType: "spot"`, `testnet: True`).

## 거래소 조사 결과 요약

### 테스트넷 평가 (Spot + Futures Cross Margin)

| 순위 | 거래소 | 점수 (/100) | 핵심 |
|------|--------|------------|------|
| 1 | **Bybit** | 92 | UTA Cross Margin 기본값. Spot+Futures 동일 API. 3,072 마켓. CCXT 10개 메서드 전체 지원 |
| 2 | OKX | 73 | 헤더 기반 안정적. 단 일부 기능 제한 이력 |
| 3 | Binance | 51 | Spot/Futures 테스트넷 별도 API 키. CCXT sandbox 깨진 상태 |
| 4 | Bitget | 51 | CCXT sandbox URL 미내장. load_markets 실패 보고 |
| 5 | KuCoin | 37 | Cross margin 실질 동작 안 함. 탈락 |

### 프로덕션 평가 (실서버)

| 순위 | 거래소 | 점수 (/320) | 핵심 |
|------|--------|------------|------|
| 1 | Binance | 271 (84.7%) | CCXT Certified. 유동성/인프라 1위. 한국 미등록 |
| 2 | OKX | 256 (80.0%) | 파생상품 1위. 보안 최우수 (해킹 0). zk-STARK PoR |
| 3 | Bybit | 245 (76.6%) | 현 프로젝트 기본값. 레이트 리밋 최고. 2025.2 $1.5B 해킹 |
| 4 | Bitget | 239 (74.7%) | CCXT Certified. 출금 수수료 최저 |
| 5 | Gate.io | 214 (66.9%) | 코인 수 4,500+ 최다. 인프라/보안 열세 |

### 전략 결정

- **Sprint 7a**: Bybit testnet에서 Futures + Cross Margin 추가 (데모 검증)
- **Sprint 7b**: OKX 멀티 거래소 추가 (2순위)
- **Sprint 8+**: Binance mainnet (실거래, 프로덕션 메인) + OKX (보조)

## 기술 결정 3가지

| # | 질문 | 결정 | 이유 |
|---|------|------|------|
| Q1 | 별도 Provider vs 파라미터화 | **별도 클래스** (`BybitFuturesProvider`) | Spot과 Futures는 심볼 형식, 설정, 에러 핸들링이 다름 |
| Q2 | Leverage 설정 위치 | **OrderSubmit DTO에 leverage 필드** | 전략마다 다른 레버리지 사용 가능 |
| Q3 | Position mode | **One-way only** | CCXT Bybit Hedge mode 이슈 보고됨 (#24848), 안정성 우선 |

## 워크플로우: 경량 3-Step

Full 6-Step (Sprint 6)은 과도. 범위가 작으므로:

1. **기술 결정 메모** → 이 문서 (완료)
2. **경량 plan** (3-5 tasks) → 새 세션에서 /writing-plans
3. **보안 체크리스트** → plan 헤더에 포함
4. **SDD 실행** → subagent-driven-development

## 예상 Task 구조

```
T1: OrderSubmit DTO 확장 + config 추가
    - OrderSubmit에 leverage: int | None, margin_mode: Literal["cross","isolated"] | None
    - Config: exchange_provider Literal에 "bybit_futures" 추가

T2: BybitFuturesProvider 구현 (TDD)
    - defaultType: "linear", testnet: True
    - setMarginMode('cross') + setLeverage(N)
    - 심볼: BTC/USDT:USDT
    - CCXT mock 테스트 (Sprint 6 T6 패턴)

T3: Celery task + DI 분기 확장
    - _build_exchange_provider()에 "bybit_futures" 분기
    - execute_order_task에서 futures 심볼 처리

T4: Kill Switch 레버리지 고려 + E2E
    - CumulativeLossEvaluator 레버리지 반영 검토
    - E2E: futures order → fill → kill switch

T5: (Optional) 실서버 준비
    - BybitLiveProvider (testnet=False)
    - Config: "bybit_live", "bybit_futures_live"
```

## 보안 체크리스트

- [ ] 레버리지 상한 검증 (config MAX_LEVERAGE, 기본 20x 권장)
- [ ] Cross margin 청산 시뮬레이션 (testnet 의도적 청산 테스트)
- [ ] InsufficientMargin 등 Futures 전용 에러 타입 ProviderError 매핑
- [ ] Kill Switch capital_base가 레버리지 포지션 반영하는지 확인
- [ ] Funding rate 비용이 PnL 계산에 반영되는지 (Sprint 7a는 skip 가능)

## 구현 노트: DB string ↔ DTO Literal 경계

**불변식:** `Order.margin_mode: str | None` (SQLModel 컬럼) vs
`OrderSubmit.margin_mode: Literal["cross","isolated"] | None` (frozen dataclass).

**Runtime 검증 없음 — defense-in-depth 3계층에 의존:**
1. Pydantic V2 `OrderRequest.margin_mode: Literal[...]` (HTTP 경계)
2. Celery `_async_execute`가 `# type: ignore[arg-type]`로 narrowing
3. CCXT `set_margin_mode(value, symbol)`가 서버측 검증 (ProviderError 최종 wrap)

**향후 주의:** DB seed / raw SQL / 외부 writer가 `margin_mode`에 임의 문자열을 넣으면
runtime에서는 잡히지 않고 CCXT 호출 시점까지 전파된다. Sprint 8+에서 mainnet
연동 전 DB-level `CHECK constraint` 추가를 고려할 것 (T1 code review M1 참조).

## 참조 파일

- `backend/src/trading/providers.py` — BybitDemoProvider (Spot 기존 구현)
- `backend/src/trading/providers.py:63` — ExchangeProvider Protocol
- `backend/src/core/config.py:57` — exchange_provider Literal
- `backend/src/tasks/trading.py:65` — _build_exchange_provider() 분기
- `docs/dev-log/006-sprint6-design-review-summary.md` — ADR-006
