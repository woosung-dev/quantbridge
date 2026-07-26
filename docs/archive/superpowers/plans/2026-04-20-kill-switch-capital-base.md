# Plan: Kill Switch `capital_base` 동적 바인딩 + Notional Check

> **Session:** H1 Stealth 클로징 5-Step 풀패키지 Step 3 (2026-04-20)
> **Branch:** `feat/kill-switch-capital-base`
> **Goal:** CumulativeLossEvaluator가 ExchangeAccount의 실제 잔고를 기준으로 MDD를 계산하도록 전환 + 주문 직전 `notional = qty × price × leverage` 검증으로 자본 초과 포지션 hard-reject.
> **ADR 참조:** [ADR-007 §보안 체크리스트 line 93](../../dev-log/007-sprint7a-futures-decisions.md) — Sprint 8+ 작업으로 예정돼 있던 항목.
> **H1 종료 게이트:** 본인 Bybit Futures 실자본 dogfood 착수의 전제.

---

## 1. 현황 (2026-04-20)

| 항목                                     | 위치                                                                                | 현재 상태                                                 |
| ---------------------------------------- | ----------------------------------------------------------------------------------- | --------------------------------------------------------- | --- | ----------------------- |
| `capital_base`                           | `core/config.py:82-88` — `kill_switch_capital_base_usd: Decimal = Decimal("10000")` | **정적 config**                                           |
| `CumulativeLossEvaluator`                | `trading/kill_switch.py:45-92`                                                      | `__init__(capital_base: Decimal)` 고정 주입, MDD = `      | pnl | / self.\_capital × 100` |
| `DailyLossEvaluator`                     | `trading/kill_switch.py:95-128`                                                     | capital_base 미사용 (절대값 USD)                          |
| DI 주입                                  | `trading/dependencies.py:85`                                                        | `capital_base=settings.kill_switch_capital_base_usd` 고정 |
| `ExchangeAccountService.fetch_balance()` | `exchange/service.py`                                                               | **미구현** (파일 1줄)                                     |
| `BybitFuturesProvider.fetch_balance()`   | `trading/providers.py:187-253`                                                      | **미구현**                                                |
| `OrderService.execute()` leverage cap    | `trading/service.py:187-193`                                                        | 정적 `leverage > bybit_futures_max_leverage` 체크만       |
| notional check                           | `trading/service.py`                                                                | **없음** — qty × price × leverage 미검증                  |
| ExchangeAccount DB 컬럼                  | `exchange/models.py:58-96`                                                          | `capital_base` 컬럼 없음. runtime fetch만 가능            |

**config 주석이 이미 예견**: `"Sprint 6은 config 고정값, Sprint 7+에서 ExchangeAccount.fetch_balance() 동적 바인딩"` (config.py:85-86) — 이번 PR이 그 이연 해소.

---

## 2. 설계 결정

### D-1. capital_base 동적 바인딩 구현 방식

**결정: ExchangeAccountService-owned 30s TTL cache → evaluator는 주입받은 스칼라 사용**

- Kill Switch service가 평가 직전 `fetch_balance_usdt(account_id)` 호출 → evaluator 생성 시 주입
- Evaluator signature는 그대로 유지 (async 전환 없음, 테스트 영향 최소)
- Fetch 실패 시: config `kill_switch_capital_base_usd` fallback + `logging.warning`
- TTL cache: account_id별 30s (주문 경로 외에는 재호출 없음)

**거부된 대안:**

- ❌ Evaluator 내부 async balance fetch — signature 변경 + 테스트 파급
- ❌ Background job + DB 저장 — over-engineering (주문 직전 1회 평가면 충분)

### D-2. Notional check 구현 위치

**결정: `OrderService.execute()` 내 기존 leverage cap 검증 직후 단일 블록**

- `notional_usdt = quantity × price × leverage` vs `available_usdt × leverage_cap_safety`
- 신규 예외 `NotionalExceeded` (422, 기존 `LeverageCapExceeded`와 같은 계열)
- safety margin: `notional ≤ available × bybit_futures_max_leverage × 0.95` (5% 버퍼)

**거부된 대안:**

- ❌ 새 middleware layer (OrderValidator) — 재사용 요구 없음, YAGNI
- ❌ Kill Switch evaluator 확장 — evaluator는 사후 평가, notional은 사전 게이트

### D-3. Fetch 실패 정책

**결정: config fallback + 경고 로깅 (trading 중단 금지)**

- 네트워크 실패·API 에러 시 즉시 주문 거부는 사용자 dogfood 경험을 망침
- 대신 structured log + 가능하면 metric으로 관측 가능하게
- Fallback 값도 초과하면 `NotionalExceeded` 정상 발동

---

## 3. Task 분해

### T1. `BybitFuturesProvider.fetch_balance()` + `ExchangeAccountService.fetch_balance()`

**파일:**

- `backend/src/trading/providers.py` — `BybitFuturesProvider.fetch_balance(creds) -> dict[str, Decimal]`
- `backend/src/exchange/service.py` — `ExchangeAccountService.fetch_balance_usdt(account_id) -> Decimal | None`
- `backend/src/trading/providers.py` — Protocol에 `fetch_balance` 추가 (선택)

**구현:**

```python
# providers.py
async def fetch_balance(self, creds: Credentials) -> dict[str, Decimal]:
    exchange = ccxt_async.bybit({
        "apiKey": creds.api_key,
        "secret": creds.api_secret,
        "options": {"defaultType": "linear", "testnet": creds.testnet},
    })
    try:
        raw = await exchange.fetch_balance()
        return {
            asset: Decimal(str(data.get("free", 0)))
            for asset, data in raw.items()
            if isinstance(data, dict)
        }
    finally:
        await exchange.close()

# exchange/service.py
async def fetch_balance_usdt(self, account_id: UUID) -> Decimal | None:
    account = await self._get_decrypted(account_id)
    if account is None:
        return None
    try:
        balances = await self._bybit_provider.fetch_balance(account.creds)
        return balances.get("USDT")
    except ProviderError as exc:
        logger.warning("fetch_balance_failed", account_id=str(account_id), error=str(exc))
        return None
```

**테스트:**

- `test_bybit_provider_fetch_balance.py` — CCXT mock, USDT/BTC 반환 검증
- `test_exchange_service_fetch_balance.py` — account decrypt + provider 주입 mock

### T2. `CumulativeLossEvaluator` 동적 capital_base 주입

**파일:**

- `backend/src/trading/kill_switch.py:45-92` — `CumulativeLossEvaluator` 수정
- `backend/src/trading/dependencies.py:76-92` — DI 변경

**설계 (breaking change 최소화):**

```python
class CumulativeLossEvaluator:
    def __init__(
        self,
        threshold_percent: Decimal,
        default_capital: Decimal,
        exchange_service: ExchangeAccountService | None = None,
    ) -> None:
        self._threshold = threshold_percent
        self._default_capital = default_capital
        self._exchange_service = exchange_service

    async def evaluate(self, ctx: EvaluationContext, pnl: Decimal) -> EvaluationResult:
        capital = self._default_capital
        if self._exchange_service is not None and ctx.account_id is not None:
            dynamic = await self._exchange_service.fetch_balance_usdt(ctx.account_id)
            if dynamic is not None and dynamic > Decimal("0"):
                capital = dynamic
        # 이하 기존 MDD 계산
```

**이유:**

- exchange_service None이면 기존 동작 유지 (테스트 호환)
- account_id None이면 Strategy 전역 scope → default 사용
- dynamic 0 이하는 fallback (계좌 이관 중 같은 edge case)

### T3. `OrderService.execute()` notional check 추가

**파일:**

- `backend/src/trading/service.py:187-193` 이후에 블록 삽입
- `backend/src/trading/exceptions.py` — `NotionalExceeded` 추가

**구현:**

```python
# service.py (line 193 다음)
if req.leverage is not None:
    available = await self._exchange_service.fetch_balance_usdt(req.account_id)
    if available is not None and available > Decimal("0"):
        notional = req.quantity * req.price * Decimal(req.leverage)
        max_notional = available * Decimal(settings.bybit_futures_max_leverage) * Decimal("0.95")
        if notional > max_notional:
            raise NotionalExceeded(
                notional=notional,
                available=available,
                leverage=req.leverage,
                max_notional=max_notional,
            )
```

**예외:**

```python
# exceptions.py
class NotionalExceeded(AppException):
    status_code = 422
    code = "notional_exceeded"
    def __init__(self, notional: Decimal, available: Decimal, leverage: int, max_notional: Decimal):
        self.notional = notional
        self.available = available
        self.leverage = leverage
        self.max_notional = max_notional
        super().__init__(
            f"notional {notional} exceeds max {max_notional} "
            f"(available={available}, leverage={leverage}x)"
        )
```

### T4. 테스트 확장

**파일:**

- `backend/tests/trading/test_kill_switch_evaluators.py` — dynamic capital 시나리오 3건
  - balance fetch 성공 → 동적 값 사용
  - balance fetch 실패 (None 반환) → default fallback
  - exchange_service None → default fallback (backward compat)
- `backend/tests/trading/test_service_orders_kill_switch.py` — notional check 통합 테스트 2건
  - notional ≤ max → 정상 주문
  - notional > max → `NotionalExceeded` 422
- `backend/tests/trading/test_bybit_provider_fetch_balance.py` (신규) — 3건
- `backend/tests/trading/test_exchange_service_fetch_balance.py` (신규) — 3건

---

## 4. 수락 기준

- [ ] `BybitFuturesProvider.fetch_balance()` + `ExchangeAccountService.fetch_balance_usdt()` 구현 + 단위 테스트 green
- [ ] `CumulativeLossEvaluator`가 exchange_service 주입 시 동적 capital 사용, 미주입 시 default fallback
- [ ] `OrderService.execute()`에서 notional 초과 시 `NotionalExceeded` 422 반환
- [ ] 기존 Kill Switch 테스트 회귀 없음 (backward compat 확인)
- [ ] ruff + mypy clean
- [ ] 신규 테스트 최소 8건 추가 (T1: 3, T2: 3, T3: 2)
- [ ] `config.py:85-86` 주석 업데이트 ("Sprint 7+ 동적 바인딩" → "✅ 2026-04-20 완료")

---

## 5. 리스크 & 완화

| 리스크                                             | 완화                                                                                      |
| -------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| CCXT testnet fetch_balance이 실제 거래와 다른 응답 | Mock unit test + mainnet 전환 전 수동 smoke (Step 4 runbook에 포함)                       |
| 매 주문마다 fetch_balance 호출 → rate limit        | 30s TTL cache (D-1) + ADR-007 line 102 "idempotent no-op" 정책 참고                       |
| async evaluator가 기존 sync 호출 경로 깸           | evaluator는 이미 async 메서드. 호출부(`KillSwitchService.evaluate_strategy`)는 이미 async |
| capital=0인 계좌 (신규 계정 + 입금 전)             | `dynamic > 0` 가드 (T2) + logging.warning                                                 |
| Bybit testnet API key 만료                         | Step 4 runbook에 key 로테이션 절차 포함                                                   |

---

## 6. 범위 밖 (H2+ 이연)

- OKX balance fetch (Sprint 7d에서 OKX 어댑터는 추가됐지만 balance는 별도 PR)
- Isolated margin 전환 (ADR-007 Sprint 7b 스코프)
- Funding rate 비용 PnL 반영 (ADR-007 §보안 체크리스트)
- 실시간 WebSocket balance 스트리밍
- Prometheus metric (`fetch_balance_duration_seconds`, `notional_rejected_total`)

---

## 7. 구현 순서

1. T1-a: `BybitFuturesProvider.fetch_balance` + 단위 테스트
2. T1-b: `ExchangeAccountService.fetch_balance_usdt` + 단위 테스트
3. T2: `CumulativeLossEvaluator` 수정 + DI 변경 + 테스트 확장
4. T3: `NotionalExceeded` 예외 + `OrderService.execute` 검증 + 통합 테스트
5. pytest 전체 green + ruff + mypy
6. `config.py` 주석 업데이트
7. 커밋 (논리별 3개: T1 / T2 / T3+config)
8. 푸쉬 + PR
