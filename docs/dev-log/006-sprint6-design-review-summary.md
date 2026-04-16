# ADR-006: Sprint 6 Trading 데모 설계 리뷰 결과 + 3 핵심 의사결정

> **상태:** 확정
> **일자:** 2026-04-16
> **작성자:** QuantBridge 팀
> **관련 PR:** [#8](https://github.com/woosung-dev/quantbridge/pull/8) (Sprint 6 설계/리뷰, commits `ebaa9b3` → `0842fa9`)
> **관련 문서:**
> - Parent design doc: `docs/01_requirements/trading-demo.md`
> - Brainstorming spec: `docs/superpowers/specs/2026-04-16-trading-demo-design.md`
> - Implementation plan: `docs/superpowers/plans/2026-04-16-trading-demo.md`
> - Security audit: `docs/audit/2026-04-16-trading-demo-security.md`

---

## 컨텍스트

Sprint 6 Trading 데모는 "TradingView Alert → 이메일 → 수동 매매"의 manual link를 제거하는 "24/7 자동 집행 + Kill Switch" MVP. 설계 완료 후 `/autoplan` 4-phase single-voice 리뷰(CEO/Design/Eng/DX, Codex 401로 subagent-only)에서 **41 findings + 5 critical**을 식별했다. 이 ADR은 그중 plan 구조를 바꾼 **3 핵심 아키텍처 결정**을 영구 기록한다.

Codex 401 상태(quota ~4/18 복귀)로 dual-voice 불가했지만, Claude subagent 4개 각각 독립 컨텍스트로 실행해 cross-phase 테마 5개(HMAC 보안/Kill Switch 운영/MultiFernet/관측성/Idempotency contract)를 독립 확인했다.

---

## 결정 1: EncryptionService를 MultiFernet 기반으로 (단일 키 시점부터)

### 원래 설계

Brainstorming spec §2.3은 "single master key (env var `TRADING_ENCRYPTION_KEY`)로 Sprint 6 시작, Sprint 7+에 `rotate_all(old_key, new_key)` 배치 메서드 추가"로 분기했다.

### 리뷰 발견 (CEO F3 + Eng E4)

독립 리뷰 2개가 같은 결론을 냈다.

- **Eng E4 (HIGH):** "Sprint 6 단일 Fernet 구현 → env 키 교체 시 **모든 기존 credential 복호화 불가 = P0 incident**." 제시된 시나리오: 운영자가 보안 사고로 키를 교체하면 DB의 모든 `ExchangeAccount.api_key_encrypted` 필드가 무효화된다.
- **CEO F3 (HIGH):** "Fernet은 multi-key를 네이티브 지원한다. `MultiFernet([active, ...old])` 5-line 확장이면 Sprint 6 ~ Sprint 7 부채 회피 완료. 반면 storage format 변경은 배포 중 re-encrypt + grace period 필요한 운영 이슈."

### 결정

**T4 `EncryptionService`를 처음부터 `MultiFernet` 기반으로 구현.** 단일 키라도 list 추상화로 시작. Sprint 7+ 키 로테이션은 "새 키 prepend + old key grace 후 제거"로 무중단 전환.

### 구현 변경점

```python
# config.py — 단일 필드, comma-separated
trading_encryption_keys: SecretStr  # newest first

@field_validator("trading_encryption_keys")
def _validate_keys(cls, v: SecretStr) -> SecretStr:
    from cryptography.fernet import Fernet
    keys = [k.strip() for k in v.get_secret_value().split(",") if k.strip()]
    if not keys:
        raise ValueError("must contain at least 1 Fernet key")
    for k in keys:
        Fernet(k.encode())  # validate
    return v

# encryption.py
class EncryptionService:
    def __init__(self, master_keys: SecretStr) -> None:
        key_strs = [k.strip() for k in master_keys.get_secret_value().split(",") if k.strip()]
        self._multi = MultiFernet([Fernet(k.encode()) for k in key_strs])

    def encrypt(self, plaintext: str) -> bytes:
        return self._multi.encrypt(plaintext.encode())  # 항상 첫 키(newest)로

    def decrypt(self, ciphertext: bytes) -> str:
        return self._multi.decrypt(ciphertext).decode()  # list 순차 시도
```

env 변수도 `TRADING_ENCRYPTION_KEY` → `TRADING_ENCRYPTION_KEYS`(복수)로 rename.

### Trade-off

- 추가 공수: +0.5d (plan 버퍼 1.5d 잠식)
- 얻는 것: Sprint 7+ 키 로테이션 P0 incident 리스크 제거, 5-line 추가로 영구 해결

---

## 결정 2: `MddEvaluator` → `CumulativeLossEvaluator` rename (시맨틱 정합)

### 원래 설계

Spec §2.2의 Kill Switch 첫 번째 evaluator는 `MddEvaluator`. 구현 계획:

```python
class MddEvaluator:
    async def evaluate(self, ctx) -> EvaluationResult:
        total_pnl = sum(Order.realized_pnl WHERE strategy=..., state=filled)
        loss_percent = abs(total_pnl) / capital_base * 100
        if loss_percent > threshold: gated=True
```

### 리뷰 발견 (CEO F4)

**CRITICAL:** "이건 **MDD가 아니다**. MDD는 **peak equity 대비 drawdown**. 현재 구현은 '누적 realized PnL 손실 / 고정 capital'." 구체적 반례:

> Strategy가 +$500 → +$1000 → +$200으로 움직여 peak $1000 대비 80% drawdown이어도, 누적 PnL은 +$200이라 gated가 `False`. 반대로 -$500 → -$800 → -$600으로 움직여 실제 peak drawdown은 $500(첫 peak $0 기준)인데 누적 PnL -$600으로 gated 판정. 네이밍과 실제 계산이 **반대 방향**으로 어긋남.

또한 `capital_base`가 `Decimal("10000")` 하드코드. 실제 자본 $5k-20k 범위에서 변동하므로 고정값 부정확.

### 결정

- 클래스/enum/변수명을 **`CumulativeLossEvaluator`** / `cumulative_loss` / `KILL_SWITCH_CUMULATIVE_LOSS_PERCENT`로 rename
- 진짜 peak-based MDD는 **Sprint 7+에 `MaxDrawdownEvaluator` 별도 구현** (equity snapshot 테이블 필요)
- Sprint 6의 `capital_base`는 config (`KILL_SWITCH_CAPITAL_BASE_USD`), Sprint 7에서 `ExchangeAccount.fetch_balance()` 동적 바인딩

### 영향 범위

- `KillSwitchTriggerType` enum: `mdd = "mdd"` → `cumulative_loss = "cumulative_loss"`
- DB CHECK constraint: `trigger_type = 'cumulative_loss'` 매칭
- plan T13 구현체 + T14 테스트 rename
- Sprint 6 fresh schema라 마이그레이션 부담 없음

### Trade-off

- 추가 공수: +0.25d
- 얻는 것: 시맨틱 버그 제거. 사용자가 "MDD 10% 넘으면 멈춤"이라는 설정이 실제로는 "누적 손실 10% 넘으면 멈춤"이라는 것을 UI/로그에서 명확히 구분 가능.

---

## 결정 3: `Order.idempotency_payload_hash BYTEA` 컬럼 추가

### 원래 설계

Brainstorming spec §2.5: `orders.idempotency_key TEXT UNIQUE` 단독. 동일 key 재요청 시 cached response 반환.

### 리뷰 발견 (Eng E2 + DX4)

독립 리뷰 2개가 교차 발견.

- **Eng E2 (CRITICAL):** "동일 Idempotency-Key + **다른 body** → 첫 주문의 cached response가 반환됨. 시그널이 silently 손실. `IdempotencyConflict` 예외는 정의만 있고 raise 경로 없음."
- **DX4 (HIGH):** "IETF draft-ietf-httpapi-idempotency-key-header는 replay 200, first-create 201, payload-mismatch 409를 명시. 현 설계는 201 하나로 fold. TV/proxy 재시도 체인에서 의미 구분 불가."

구체적 시나리오: 개발자가 Pine 전략을 수정(quantity 변경)했는데 TradingView가 기존 alert의 Idempotency-Key를 재사용 → 구 주문 응답 반환 → 새 주문 signal 손실.

### 결정

1. **Schema에 `idempotency_payload_hash BYTEA` 컬럼 추가** (T1)
2. **OrderService.execute 시그너처에 `body_hash: bytes | None` 파라미터** (T12/T15)
3. **`(OrderResponse, is_replayed: bool)` 튜플 반환** — router가 HTTP 상태 매핑
4. **HTTP status triad:**
   - 201 Created — first create
   - 200 OK + `Idempotency-Replayed: true` header — replay (same key + same hash)
   - 409 `IdempotencyConflict` + `original_order_id` — same key + different hash

### 구현 포인트

```python
# OrderService.execute 내부
if existing := await repo.get_by_idempotency_key(key):
    if body_hash is not None and existing.idempotency_payload_hash != body_hash:
        raise IdempotencyConflict(
            f"Idempotency-Key 재사용됐지만 payload가 다름. "
            f"original_order_id={existing.id}"
        )
    return OrderResponse.model_validate(existing), True  # replay

# Router: 201 vs 200 분기
response, is_replayed = await order_svc.execute(req, idempotency_key=k, body_hash=h)
if is_replayed:
    return JSONResponse(200, content=..., headers={"Idempotency-Replayed": "true"})
return JSONResponse(201, content=...)
```

### Trade-off

- 추가 공수: +0.5d (schema 컬럼 + flow 분기 + E2E 테스트 1건)
- 얻는 것: 시그널 loss 0건 보장, IETF 표준 준수 (TV/proxy integration 호환성)

---

## 부가 결정 (상세는 참조 문서)

| 결정 | 출처 | 영향 |
|------|------|------|
| `ensure_not_gated`를 `session.begin()` **안**, INSERT 직전으로 이동 | Eng E9 | Kill Switch race 제거 |
| `Order.filled_quantity: Decimal` 컬럼 추가 | Eng E7 | CCXT 부분체결 지원 |
| `trading.webhook_secrets.secret` → `secret_encrypted: bytes` (MultiFernet) | CSO-1 | DB leak 시 webhook 위조 방지 (spec §8 Open Item 1 해소) |

---

## 결과 및 타임라인 영향

- **Critical path:** 12.5d → **15.05d** (autoplan +1.85d + /cso +0.7d)
- **Buffer:** 1.5d → -1.05d 초과
- **대응:** M1을 M1a/M1b로 분할 + task 병렬화 확대 (CEO F6 권고)

Sprint 6 plan의 T1/T3/T4/T13/T15는 이 ADR의 결정대로 업데이트 완료 (commit `29492d1`, `0842fa9`).

---

## 남은 Open Items (Sprint 7+ 이연)

1. **Peak-based MaxDrawdownEvaluator** — equity snapshot 테이블 필요 (Sprint 7+ separate ADR)
2. **Telegram 알림 채널** (CEO F5) — 운영 백업 채널. /plan-eng-review 재논의 필요.
3. **Bybit testnet fallback → Binance testnet** (CEO F7) — Provider 1개 추가로 해결
4. **Real Bybit testnet smoke test** (CEO F6) — T6 뒤 수동 checklist로 부가

## 참조

- autoplan 전체 findings 41건: Sprint 6 plan 파일의 "/autoplan 리뷰 결과" 섹션 (축약 예정, 본 ADR로 대체)
- /cso 6 findings: `docs/audit/2026-04-16-trading-demo-security.md`
- Restore point: `~/.gstack/projects/quant-bridge/feat-sprint6-trading-demo-docs-autoplan-restore-20260416-203650.md` (로컬)
