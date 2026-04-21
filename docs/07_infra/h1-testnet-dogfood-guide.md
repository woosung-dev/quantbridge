# H1 Testnet Dogfood 운영 가이드

> **작성일:** 2026-04-21
> **목적:** QuantBridge H1→H2 게이트 dogfood를 Bybit Testnet에서 3~4주 운영하기 위한 실전 가이드.
> **컨텍스트:** 2026-04-21 결정 — 실자본 mainnet 대신 testnet only로 기술 검증 우선.
> 기술 검증은 testnet에서 90%+ 충분. 실자본 부담 없이 실거래 파이프라인 전체를 검증.

---

## 1. 전략 선정

### 권장 전략: `s1_pbr.pine` (Pivot Breakout Reversal)

**선정 이유:**

- Pine v2 인터프리터 6/6 corpus 완주 기준 검증된 전략 (Sprint 8b)
- 신호가 명확 (pivot high/low → breakout → reversal)하여 오작동 원인 분석 용이
- BTC/USDT:USDT 1h에서 충분한 신호 빈도 (일 1~3회) → 빠른 피드백 루프
- 과최적화 위험 낮음 (파라미터 3개 이하)

**대안:** `i3_drfx.pine` (Supertrend + DEMA) — 신호 빈도 낮지만 트렌드 추종 전략으로 비교 검증 가능.

**권장 설정:**

```
Symbol: BTC/USDT:USDT
Timeframe: 1h
Leverage: 1x (첫 2주)
Quantity: 0.001 BTC (약 $60~100, testnet 가상 자본)
Margin mode: cross
Order type: limit (market 주문 금지)
```

---

## 2. 환경 준비 (ONE-TIME)

### 2.1 Bybit Testnet 계정

1. https://testnet.bybit.com → 별도 계정 생성 (mainnet 계정과 독립)
2. API Key 발급: Read + Trade (Withdraw 비활성)
3. Testnet USDT 충전: Testnet 계정 → "Asset" → "Deposit" → "Test USDT 지급" (무제한)

### 2.2 환경 변수

```bash
# .env.testnet (커밋 금지, .gitignore 확인)
EXCHANGE_PROVIDER=bybit_futures
BYBIT_TESTNET_KEY=<testnet_api_key>
BYBIT_TESTNET_SECRET=<testnet_api_secret>

KILL_SWITCH_CAPITAL_BASE_USD=10000   # testnet 가상 자본 기준
KILL_SWITCH_DAILY_LOSS_USD=500
KILL_SWITCH_CUMULATIVE_LOSS_PERCENT=5
BYBIT_FUTURES_MAX_LEVERAGE=1
```

### 2.3 DB 설정 확인

```bash
cd backend
uv run alembic upgrade head           # 최신 마이그레이션 적용
uv run pytest tests/trading/ -v -x   # Kill Switch 회귀 테스트 pass 확인
```

### 2.4 Smoke Test 통과

```bash
cd backend
uv run python scripts/bybit_testnet_smoke.py \
    --api-key "$BYBIT_TESTNET_KEY" \
    --api-secret "$BYBIT_TESTNET_SECRET" \
    --symbol "BTC/USDT:USDT" --quantity 0.001
```

**기대 출력:**

```
[PASS] order submitted: order_id=abc123
[PASS] order cancelled
[PASS] DB row exists: trading.orders
```

Smoke test 실패 시 → 운영 시작 금지. `docs/TODO.md` Blocked 항목 추가.

---

## 3. 일일 운영 절차

### 오전 체크 (5분)

```sql
-- Kill Switch 이벤트 확인
SELECT trigger_type, triggered_at, strategy_id
FROM trading.kill_switch_events
WHERE created_at > NOW() - INTERVAL '24 hours';
```

- 0건 → 정상 진행
- 1건 이상 → **Level 2 대응** (§5 참조)

```sql
-- 밤새 미정리 포지션 확인
SELECT * FROM trading.orders
WHERE status NOT IN ('filled', 'cancelled', 'rejected')
  AND created_at < NOW() - INTERVAL '8 hours';
```

- 결과 있으면 → Bybit Testnet UI에서 수동 확인 + 원인 분석

### 주문 관찰 (신호 발생 시)

QuantBridge UI 또는 백엔드 로그에서 주문 흐름 추적:

```bash
docker compose logs -f backend | grep -E "order_executed|kill_switch|error"
```

**정상 흐름:**

1. 전략 신호 생성 → `POST /trading/orders` 호출
2. `order_executed` 로그 출력 (5 필드: order_id, symbol, side, notional, leverage)
3. `trading.orders` row `status = "submitted"` → `"filled"` 전환
4. Bybit Testnet "Orders" 탭에서 동일 주문 확인

### 저녁 리포트 (10분)

```sql
-- 일일 주문 성공률
SELECT status, COUNT(*) as cnt
FROM trading.orders
WHERE created_at::date = CURRENT_DATE
GROUP BY status;

-- PnL 집계 (체결된 주문 기준)
SELECT SUM(realized_pnl) as daily_pnl
FROM trading.orders
WHERE status = 'filled'
  AND filled_at::date = CURRENT_DATE;
```

**목표값:**

- `filled : (filled + rejected) ≥ 95%`
- QB PnL vs Bybit Testnet PnL 차이 < 1% (fee 포함)

**PR-D 이후:** Celery beat 22:00 UTC → `docs/reports/dogfood/YYYY-MM-DD.html` 자동 생성.

---

## 4. 주간 절차 (30분/주)

- [ ] **Fee 정확성 검증** (PR-C 이후): QB 수수료 계산 vs Bybit Testnet 수수료 내역 대조
- [ ] **Funding rate 반영 확인** (PR-C 이후): 8시간마다 fetch → 포지션 PnL 반영 여부
- [ ] **Kill Switch 설정값 재확인** (`CAPITAL_BASE`, `DAILY_LOSS`, `MAX_LEVERAGE`)
- [ ] **교훈 기록:** `.ai/project/lessons.md` 업데이트 (새 발견 사항)
- [ ] **주간 리포트:** 누적 PnL + 신호 빈도 + 오류 패턴 문서화

---

## 5. 리스크 대응

### Level 1 — Kill Switch 자동 발동 (정상 동작)

**증상:** 새 주문 시 `422 kill_switch_active` 에러.

**조치:**

1. `trading.kill_switch_events.trigger_type` 확인
2. `daily_loss` → 당일 거래 중지, 익일 UTC 00:00 자동 해제 또는 수동 해제
3. `cumulative_loss` → 해당 전략 일시 중지 + 백테스트 재검증
4. `lessons.md` 기록 (첫 발생 시)

### Level 2 — 시스템 이상 (예상외 상태)

**증상:** `trading.orders` row가 Bybit에 없음 / Bybit에 있는데 DB 없음 / PnL 불일치 > 1%.

**조치:**

1. **즉시 전략 비활성:** `UPDATE trading.exchange_accounts SET status='disabled' WHERE id=<id>`
2. Bybit Testnet UI에서 수동으로 오픈 포지션 0 정리
3. `docs/dev-log/` ADR 신규 작성 (타임라인 기록 → RCA)
4. Fix 완료 후 smoke test 재통과 확인 후 재개

### Level 3 — 코드 버그 반복 (시스템 신뢰도 의문)

**증상:** 동일 오류 3회 이상 반복 / PnL 차이 > 5% 지속.

**조치:**

1. **dogfood 일시 중단** (H2 진입 계획 재검토)
2. `docs/TODO.md` Blocked 항목 추가: 원인 명시
3. 관련 Sprint (9 or 10) 우선순위로 격상
4. 수정 완료 + 회귀 테스트 green 확인 후 dogfood 재개

---

## 6. 종료 기준

### 6a. 만족 종료 (Testnet 완료 → H2 직진입)

아래 **모두 충족** 시:

- Testnet 운영 기간: 3주 이상
- Kill Switch false positive: < 1건/주 평균
- 시스템 다운타임: 0분
- QB/Bybit PnL 차이: < 1%
- 주관 평가: "지인 5명에게 추천 가능" YES

→ `/office-hours` (H2 kickoff) 세션. 선택: mainnet 72h 진행 후 H2.

### 6b. 시간 종료 (4주 경과)

4주 후 일부 기준 미충족이어도:

- 미충족 항목 원인을 `docs/dev-log/` ADR로 문서화
- Sprint 9+ 우선순위 조정 후 H2 진입 (기준 미충족 항목은 Sprint 9 tech debt)

### 6c. 실패 종료 (중대 결함 발견)

- 데이터 손실 / 중복 주문 / 포지션 불일치 반복 발생 시
- Trust Pillar 인터럽트 규칙 적용 (roadmap.md 가드레일 참조)
- 현재 Sprint 즉시 중단 → Fix 우선 → 재시작

---

## 7. 참조 문서

| 문서                                                                                             | 목적                                     |
| ------------------------------------------------------------------------------------------------ | ---------------------------------------- |
| [`./bybit-mainnet-checklist.md`](./bybit-mainnet-checklist.md)                                   | 환경 설정 체크리스트 (testnet + mainnet) |
| [`./runbook.md`](./runbook.md) §12                                                               | Testnet → Mainnet 전환 절차              |
| [`../dev-log/006-kill-switch.md`](../dev-log/006-kill-switch.md)                                 | Kill Switch 설계 근거                    |
| [`../superpowers/plans/2026-04-20-h2-kickoff.md`](../superpowers/plans/2026-04-20-h2-kickoff.md) | H2 Sprint 9~11 분해                      |
| `docs/reports/dogfood/YYYY-MM-DD.html`                                                           | 자동 생성 일일 리포트 (PR-D 이후)        |

---

## 변경 이력

- **2026-04-21** — 초안 작성. Testnet dogfood 결정(실자본 → testnet) 반영.
