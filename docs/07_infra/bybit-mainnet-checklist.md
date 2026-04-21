# Bybit Mainnet Dogfood — 체크리스트

> **목적:** QuantBridge H1 Stealth 종료 조건인 본인 실자본 1~2주 dogfood를 안전하게 수행하기 위한 사전·일일·긴급 체크리스트.
> **전제:** Kill Switch `capital_base` 동적 바인딩 완료 (PR #38), Sprint 7a Bybit Futures + Cross Margin 동작.
> **참조:** [`./runbook.md`](./runbook.md) §12 Bybit Testnet → Mainnet 전환.

---

## 📋 사전 체크리스트 (ONE-TIME, Mainnet 첫 주문 전)

### 🔐 보안 (건너뛸 수 없음)

- [ ] **Bybit 계정 2FA 활성** (TOTP + 이메일 2중)
- [ ] **API Key 권한 최소화:** `Read + Trade` 만. **Withdraw 비활성** (이체 권한 없음)
- [ ] **IP Whitelist 등록:** 프로덕션 서버 고정 IP만 허용 (Cloud Run static egress)
- [ ] **API Key 별칭 지정:** `quantbridge-mainnet-v1-YYYYMMDD`
- [ ] **복구 코드 별도 보관:** 2FA 분실 대비
- [ ] **이메일 알림 활성:** API key 생성/삭제, 출금, 로그인 이벤트
- [ ] **.env.mainnet 파일 생성 + `.gitignore` 확인:** 커밋되지 않는지 `git check-ignore` 통과

### 💰 자본 & 리스크 설정

- [ ] **초기 자본:** $100~500 (이 금액을 잃어도 감당 가능한 수준)
- [ ] **환경 변수 설정:**
  ```bash
  BYBIT_FUTURES_MAX_LEVERAGE=1        # 첫 주 1:1, 이후 점진 상향
  KILL_SWITCH_CAPITAL_BASE_USD=100    # fallback. 동적 바인딩 실패 시 이 값
  KILL_SWITCH_DAILY_LOSS_USD=10       # 일일 $10 초과 시 자동 중지
  KILL_SWITCH_CUMULATIVE_LOSS_PERCENT=5  # 누적 5% 손실 시 전략 차단
  EXCHANGE_PROVIDER=bybit_futures     # Futures 모드
  ```

### 🛠 코드 준비

- [ ] **BybitFuturesProvider testnet 플래그 해제 PR 생성 + 리뷰:**
  - `providers.py`의 `"testnet": True` 하드코딩 → `Credentials.testnet` 필드로 분기
  - ExchangeAccount.mode가 `live`일 때만 mainnet URL 사용
- [ ] **Alembic migration 확인:** 최신 `alembic upgrade head` 적용됨
- [ ] **Kill Switch 회귀 테스트 pass:** `uv run pytest tests/trading/ -v`
- [ ] **Observability 최소 로그 활성:**
  - `order_executed` 5 필드 structured log 동작 (PR #38 이후 trading service 경유)

### ✅ Dry-run (Testnet)

- [ ] **Testnet smoke script 성공:**
  ```bash
  cd backend
  uv run python scripts/bybit_testnet_smoke.py \
      --api-key "$BYBIT_TESTNET_KEY" \
      --api-secret "$BYBIT_TESTNET_SECRET" \
      --symbol "BTC/USDT:USDT" \
      --quantity 0.001
  ```
- [ ] **DB 상태 확인:** testnet 주문이 `trading.orders` 테이블에 row 생성됨
- [ ] **Bybit Testnet UI:** 포지션/취소 내역 확인

---

## 🌅 Day 0 — Mainnet 첫 주문 체크리스트

**반드시 두 사람이 확인 (본인 + pair check 권장):**

### 주문 직전 (1분)

- [ ] 모든 사전 체크리스트 ✅
- [ ] 계정 잔고 UI 확인 (Bybit Web) vs QB `fetch_balance_usdt` 일치
- [ ] Kill Switch 이벤트 테이블 빈 상태 확인
- [ ] 시장 급변 없음 (뉴스/공휴일/대형 이벤트 X)

### 소액 주문 실행 (2분)

- [ ] **Quantity:** 0.0001 BTC (약 $6~8 at $60k)
- [ ] **Leverage:** 1x
- [ ] **Margin mode:** cross
- [ ] **Type:** limit (반드시 한도 주문, market 아님)
- [ ] **Side:** buy
- [ ] **Price:** 현재 best_bid보다 0.1% 낮게 (즉시 체결 안 되도록)

### 주문 후 확인 (30초 이내)

- [ ] Bybit Web에 주문 표시
- [ ] QB DB `SELECT * FROM trading.orders ORDER BY created_at DESC LIMIT 1` row 존재
- [ ] status `submitted` 또는 `filled`
- [ ] structured log `order_executed` 출력:
  ```json
  {
    "event": "order_executed",
    "order_id": "...",
    "strategy_id": "...",
    "symbol": "BTC/USDT:USDT",
    "side": "buy",
    "notional": "6.0",
    "leverage": 1
  }
  ```

### 포지션 정리 (1분)

- [ ] 즉시 `cancel_order` (limit이 체결 전이면)
- [ ] 체결되었으면 반대 주문으로 close
- [ ] 최종 포지션 0 확인 (Bybit Web "Positions" 탭)

---

## 📅 일일 체크리스트 (5분/일, 한 주간)

### 아침 (작업 시작 전)

- [ ] **잔고 확인:** Bybit Web USDT balance vs 어제 종료 시점 대비 변동
- [ ] **오픈 포지션 확인:** 0건이어야 정상 (밤새 포지션 금지 정책 시)
- [ ] **Kill Switch 이벤트 확인:**
  ```sql
  SELECT * FROM trading.kill_switch_events
  WHERE created_at > NOW() - INTERVAL '24 hours';
  ```
  0건 = 정상. 1건 이상 = 원인 분석 + Kill Switch 해제 검토

### 저녁 (작업 종료 후)

- [ ] **주문 성공률 확인:**
  ```sql
  SELECT status, COUNT(*) FROM trading.orders
  WHERE created_at > NOW() - INTERVAL '24 hours'
  GROUP BY status;
  ```

  - `filled` : `rejected` 비율 ≥ 95% 정상
  - `pending`이 1시간 이상 남아있으면 stale 조사
- [ ] **Bybit PnL vs QB 계산 PnL 대조 (5건 샘플):** 차이 < 0.5% 정상
- [ ] **API 에러 burst 확인 (application log):** 분당 5건 이상이면 조사

---

## 📆 주간 체크리스트 (30분/주)

- [ ] **API Key Rotate:**
  1. Bybit Web → 새 key 발급 (Read + Trade, Withdraw X)
  2. `.env.mainnet` 값 교체
  3. 서비스 재배포
  4. 구 key REVOKE
  5. 재배포 후 smoke test 1회 (testnet)
- [ ] **Fee 차감 후 실제 PnL 집계:** Bybit export CSV vs QB DB
- [ ] **Runbook §9 인시던트 절차 재검토:** 지난 주 발생한 이슈 lessons.md 기록
- [ ] **환경 변수 재확인:** `MAX_LEVERAGE` / `CAPITAL_BASE` / `DAILY_LOSS` 값이 의도대로

---

## 🚨 긴급 대응 체크리스트

### 레벨 1 — Kill Switch 자동 발동 (정상 동작)

**증상:** API 에러 `kill_switch_active` 422 응답, 새 주문 거부.

**조치:**

1. `trading.kill_switch_events` 테이블에서 `trigger_type` 확인
2. `cumulative_loss`: 해당 strategy 일시 중지 + 백테스트 재검증
3. `daily_loss`: 당일 거래 중지, 다음 날 UTC 00:00 자동 해제 대기 또는 수동 해제
4. lessons.md 기록 (첫 발생 시)

### 레벨 2 — 시스템 이상 (예상외 상태)

**증상:** `trading.orders` row가 Bybit에 없음 / Bybit에 있는데 DB 없음 / 잔고 불일치

**조치:**

1. **즉시 서비스 paused 모드로 전환:** ExchangeAccount status='disabled'
2. Bybit Web에서 수동으로 포지션 0 정리
3. Runbook §9 인시던트 절차 시작 (타임라인 기록 → RCA → lessons.md)

### 레벨 3 — API Key 유출 의심

**증상:** 예상 외 주문 발생 / IP 외부 접근 로그 / Bybit 로그인 알림 (본인 아님)

**즉시 조치 (5분 이내):**

1. Bybit Web → API Management → **ALL keys REVOKE** (모든 key 즉시 무효화)
2. Bybit Web → Account → 2FA 재설정
3. Bybit Web → Account → 비밀번호 변경
4. 오픈 포지션 수동 close (Bybit Web)
5. 서비스 `ExchangeAccount` 전체 status='disabled' UPDATE
6. 인시던트 리포트 작성 (영구 기록)

---

## 🎯 H2 진입 게이트 (dogfood 완료 조건)

1~2주 후 아래 정량 기준 **모두 충족** 시 H2 진입 검토:

- [ ] **실자본 drawdown < 10%** (초기 자본 대비)
- [ ] **Kill Switch false positive < 1건/주** (정상 주문을 잘못 차단한 경우)
- [ ] **시스템 다운타임 0분** (API 응답 불가 또는 db 접근 불가)
- [ ] **본인 주관 평가:** "이 시스템을 친한 지인 5명에게 추천할 수 있다" YES
- [ ] **주간 PnL 리포트 QB 계산 vs Bybit 실제 차이 < 1%** (fee 반영)

모두 PASS → `/office-hours` (H2 kickoff) 세션 스케줄링.

---

## 변경 이력

- **2026-04-20** — 초안 작성 (H1 Stealth 클로징 5-Step 풀패키지 Step 4)
