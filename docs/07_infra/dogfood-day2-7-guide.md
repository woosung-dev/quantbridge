# Dogfood Day 2-7 가이드 (BL-005)

> **목적**: 사용자 본인이 매일 5-15분 QuantBridge 를 실제로 사용하면서 "내가 돈 내고 쓰고 싶은가?" 를 평가. memory `feedback_dogfood_first_indie` (Trust ≥ Scale > Monetize) 의 quality bar.
>
> **전제**: Sprint 22 (BL-091 dispatch) + Sprint 23 (BL-102 snapshot) + Sprint 24a (WS 안정화 BL-011/012/013/016) 완료. Sprint 24b (자동 dogfood 회귀 가드) 가 매 commit 검증.
>
> **AI 가 대체 불가**: self-assessment ("매일 쓰고 싶은가") + Pain 발견 인사이트 + 비즈니스 의사결정. AI 는 자동 회귀 + 코드 작성 + Pain 분석 후 fix 만 가능.

---

## 0. 시작 전 준비 (1회)

### 0.1 격리 stack 가동

```bash
make up-isolated-build  # Sprint 24a BL-101 신규 타깃 — code 변경 후 image rebuild
# 또는 기존 image 재사용 (빠른 부팅)
make up-isolated
```

확인:

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}' | grep quantbridge
# 5개 모두 Up: db / redis / worker / beat / ws-stream
```

### 0.2 Bybit Demo 계정 준비

- https://demo.bybit.com 에서 Demo 계정 생성 (실 계정과 별도)
- API key 발급 (Read + Trade 권한, IP whitelist 옵션)
- Demo USDT 가상 자금 충전 (10,000 USDT 권장)

### 0.3 자동 dogfood baseline 1회 실행

```bash
TEST_DATABASE_URL=postgresql+asyncpg://quantbridge:password@localhost:5433/quantbridge \
TEST_REDIS_LOCK_URL=redis://localhost:6380/3 \
python3 backend/scripts/run_auto_dogfood.py
```

→ 6/6 PASS 확인. 이후 매 commit / 매일 1회 실행하여 회귀 자동 가드.

---

## 1. 매일 시나리오 (5-15분)

### Day 2: Strategy create + backtest

1. `http://localhost:3100` (격리 stack frontend) sign-in
2. `/strategies/new` → 본인이 쓰는 indicator 1개 import (RsiD / PbR / LuxAlgo / UtBot / DrFX / Custom)
3. backtest 실행 (BTC/USDT 1h, 최근 1개월)
4. 결과 4탭 (Equity / Trades / Sessions / Performance) 확인
5. **self-assessment 기록**: `docs/dev-log/2026-05-XX-dogfood-day2.md`

### Day 3: TestOrderDialog (Demo broker 도달 evidence)

1. `/trading` → ExchangeAccount 등록 (Bybit Demo API key)
2. Strategy 1건 선택 → "Test Order" 버튼 → TestOrderDialog
3. 발송 결과 확인:
   - **Pass**: `exchange_order_id` = `bybit-...` (실 broker hit) + `filled_price` round number 아님 + Bybit Demo 대시보드 reflects
   - **Fail (silent broker bypass)**: `exchange_order_id` = `fixture-1` + `filled_price = 50000.00` round → Sprint 22 BL-091 회귀 (즉시 BL 등록)
4. **BrokerBadge 색상**: 녹색 broker (실 hit) vs 오렌지 mock (fixture)

### Day 4: KillSwitch 시뮬

1. `/trading` → daily_loss 한도 (kill_switch_daily_loss_usd, default $500) 초과하도록 큰 order 강제
2. KillSwitch 발동 → KillSwitchBanner active 표시 + 추가 order disable 확인
3. Slack alert 수신 확인 (SLACK_WEBHOOK_URL 설정 시, Sprint 12 Phase A)
4. KillSwitch resolve 후 재개 검증

### Day 5: Multi-account (Sprint 24a BL-011/012 실 검증)

1. 두 번째 ExchangeAccount (OKX Demo) 추가
2. 두 strategy 가 각각 다른 account 로 동시 발송
3. WebSocket lease 확인:
   ```bash
   docker exec quantbridge-redis redis-cli -n 3 KEYS "ws:lease:*"
   # 두 lease key 모두 active
   ```
4. prefork 2 worker 각각 독립 stream 동작 확인

### Day 6: 안정성 (24h soak)

1. 24h 동안 격리 stack 유지
2. 다음 metrics 추적 (`http://localhost:8100/metrics`):
   - `qb_active_orders` 가 monotonically increasing 안 하는지
   - `qb_ws_auth_circuit_total` 가 unexpected block 없는지
   - `qb_order_snapshot_fallback_total{reason="missing"}` 가 legacy row 만 inc (신규 0)
3. WebSocket reconnect count 확인 (`qb_ws_reconnect_total`)

### Day 7: Self-assessment 종합

```markdown
## Dogfood 1주 self-assessment

### 매일 사용 횟수 / 가치

- Day 2 (backtest): X회 / 평가 N/10
- Day 3 (Test order): X회 / 평가 N/10
- Day 4 (KillSwitch): X회 / 평가 N/10
- Day 5 (Multi-account): X회 / 평가 N/10
- Day 6 (24h soak): 안정성 N/10

### Pain 발견 (BL 등록 candidates)

- Pain #1: ...
- Pain #2: ...

### 종합 self-assessment: N/10

- N ≥ 7: H1→H2 gate 통과 → Sprint 25+ Path A Beta 오픈 진입 (BL-070~072)
- N = 5-6: dogfood Pain 처리 sprint
- N ≤ 4: 회귀 분석 emergency
```

---

## 2. Pain 발견 시 BL 등록 흐름

1. `docs/REFACTORING-BACKLOG.md` 에 신규 BL ID (다음 번호) 추가
2. **Trigger** 명시 (어떤 시나리오에서 발견)
3. **Priority** + **Est** + **Resolved 조건**
4. AI 가 다음 sprint 에 plan v2 surgery 후 처리

예시:

```markdown
| **BL-116 (신규)** | TestOrderDialog 발송 후 broker error 시 toast 표시 부재 (dogfood Day 3 발견) — 사용자 silent fail 인식 | P2 | S (1-2h) |
```

---

## 3. 자동 회귀 가드 (Sprint 24b 자동 dogfood)

매일 1회 또는 commit 후 실행:

```bash
TEST_DATABASE_URL=postgresql+asyncpg://quantbridge:password@localhost:5433/quantbridge \
TEST_REDIS_LOCK_URL=redis://localhost:6380/3 \
python3 backend/scripts/run_auto_dogfood.py
```

**산출물**:

- `docs/reports/auto-dogfood/<YYYY-MM-DD>.json` — pytest 결과 + 시나리오 metadata
- `docs/reports/auto-dogfood/<YYYY-MM-DD>.html` — 사람 친화적 요약

**검증 시나리오 6건**:

1. Strategy + WebhookSecret atomic create (Sprint 13 broken bug 회귀)
2. Backtest engine smoke (Pine v5 detection)
3. Order dispatch_snapshot (Sprint 22+23 BL-091/102)
4. Snapshot drift detection (Sprint 23 G.2 P1 #1 split-brain)
5. Multi-account dispatch (Sprint 24a BL-011/012)
6. Summary parser smoke

**FAIL 발생 시**: 즉시 stop + AI 에 보고 → 회귀 분석 + fix.

---

## 4. 운영 명령 reference

### 격리 stack 관리

```bash
make up-isolated         # 빠른 부팅 (image cache)
make up-isolated-build   # 코드 변경 후 image rebuild (Sprint 24a BL-101)
make down-isolated       # 정리
make logs-isolated       # logs tail

docker logs quantbridge-worker | tail -50
docker logs quantbridge-ws-stream | grep -E "lease acquired|circuit_open"
```

### 수동 fix 명령

```bash
# WS auth circuit breaker 수동 해제 (Sprint 24a BL-013, 1h block 만료 전 즉시 재개)
docker exec quantbridge-redis redis-cli -n 3 DEL ws:auth:blocked:{account_id} ws:auth:failures:{account_id}

# Stuck pending order 강제 reject (Sprint 15 BL-001 watchdog 가 자동 처리하지만 즉시 정리 시)
docker exec quantbridge-db psql -U quantbridge -c "UPDATE trading.orders SET state='rejected', error_message='manual cleanup' WHERE state='pending' AND created_at < NOW() - INTERVAL '1 hour';"

# WS lease 강제 해제 (1 worker stuck 시)
docker exec quantbridge-redis redis-cli -n 3 DEL ws:lease:{account_id}
```

### Metrics 확인

```bash
curl http://localhost:8100/metrics | grep -E "qb_active_orders|qb_ws_|qb_order_snapshot_fallback"
```

---

## 5. 다음 단계 분기 (Day 7 self-assessment 후)

| Self-assessment | 다음 sprint                                                           |
| --------------- | --------------------------------------------------------------------- |
| **≥ 7/10**      | Sprint 25+ Path A — Beta 오픈 번들 (BL-070~072 도메인 + DNS + Resend) |
| **5-6/10**      | Sprint 25 dogfood Pain 처리 (발견된 BL 우선순위)                      |
| **≤ 4/10**      | Emergency — Sprint 22+23+24 회귀 분석 + 핵심 fix                      |

---

## 6. 참조

- Sprint 22 dev-log (BL-091): `docs/dev-log/2026-05-03-sprint22-bl091-architectural.md`
- Sprint 23 dev-log (BL-098/099/101/102/103): `docs/dev-log/2026-05-03-sprint23-c3-bundle.md`
- Sprint 24a dev-log (BL-011/012/013/016): `docs/dev-log/2026-05-03-sprint24a-ws-stability.md`
- Sprint 24b dev-log (자동 dogfood): `docs/dev-log/2026-05-03-sprint24b-auto-dogfood.md`
- BL 백로그 전체: `docs/REFACTORING-BACKLOG.md`
- Sprint 12 dogfood checklist: `docs/07_infra/sprint12-dogfood-checklist.md`
