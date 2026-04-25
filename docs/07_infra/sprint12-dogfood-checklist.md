# Sprint 12 Dogfood 셋업 체크리스트

> **작성:** 2026-04-25 · **대상:** H2 Sprint 12 머지 후 본인 dogfood 시작
> **codex G5 self-checklist 10 항목** (LLM 비용 절감 — G5 게이트는 LLM call 대신 본 체크리스트로 대체)

---

## 사전 발급 (외부)

### Slack incoming webhook

1. Slack workspace → **Apps** → **Incoming Webhooks** 검색 → Add to Slack
2. Channel 선택 (예: `#quantbridge-alerts`) → Allow
3. **Webhook URL 복사**: 형식 `https://hooks.slack.com/services/T.../B.../...`
4. `.env` 또는 `.env.local` 에 주입:
   ```bash
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T.../B.../...
   ```

### Bybit Demo Trading API key

1. https://www.bybit.com 로그인 → API → API Management
2. **Demo Trading 탭** 선택 → Create New Key
3. 권한: ✅ Read · ✅ Trade · ✅ Position (Withdraw 절대 X)
4. IP 화이트리스트: 본인 IP 또는 `0.0.0.0/0` (보안 위험 인지 후)
5. `.env` 주입:
   ```bash
   BYBIT_DEMO_KEY=...
   BYBIT_DEMO_SECRET=...
   ```
6. **Bybit Demo 지갑에 simulated USDT 1,000+ 충전** — 잔고 0 = 주문 불가

---

## G5 self-checklist 10 항목 (dogfood 첫날)

### G5-1. Slack webhook 환경변수 주입 확인

```bash
grep '^SLACK_WEBHOOK_URL=' .env  # 비어있지 않은지
docker compose config | grep SLACK_WEBHOOK_URL  # 컨테이너에 전달되는지
```

✅ 통과 조건: `.env` + docker-compose env 둘 다 값 존재

### G5-2. Slack ping 도달 검증

```bash
curl -X POST "$SLACK_WEBHOOK_URL" \
  -H 'Content-Type: application/json' \
  -d '{"text":"sprint12 G5 ping"}'
```

✅ 통과 조건: 5초 이내 Slack 채널에 `sprint12 G5 ping` 메시지 표시. `ok` HTTP 200 응답.

### G5-3. Bybit Demo API key 권한 검증

CCXT 로 직접 fetch_balance 시도:

```bash
cd backend && uv run python -c "
import os, asyncio, ccxt.async_support as ccxt
async def main():
    ex = ccxt.bybit({'apiKey': os.environ['BYBIT_DEMO_KEY'],
                    'secret': os.environ['BYBIT_DEMO_SECRET'],
                    'enableRateLimit': True})
    ex.enable_demo_trading(True)
    try:
        bal = await ex.fetch_balance()
        usdt = bal.get('USDT', {}).get('free', 0)
        print(f'USDT free: {usdt}')
    finally:
        await ex.close()
asyncio.run(main())
"
```

✅ 통과 조건: USDT free ≥ 1,000. AuthenticationError 없음.

### G5-4. docker compose 전체 UP

```bash
docker compose up -d
docker compose ps  # 6 services: db, redis, backend, backend-worker, backend-beat, backend-ws-stream
```

✅ 통과 조건: 6 services 전부 `Up (healthy)` 또는 `Up`. backend-ws-stream 이 누락되지 않음.

### G5-5. WebSocket auth + subscribe + first message

ExchangeAccount UI 로 등록 후:

```bash
docker compose logs -f backend-ws-stream | head -50
```

기대 로그 시퀀스:

1. `ws_stream_connected account=<UUID> endpoint=wss://stream-demo.bybit.com/v5/private reconnect_count=0`
2. (구독 ack 무시)
3. (실주문 시) `topic=order` 메시지 수신 → handle_order_event 호출 → DB transition

✅ 통과 조건: connected log 출현. auth 실패 (Slack alert) 없음.

### G5-6. 강제 reconnect + reconciliation 검증

```bash
docker compose restart backend-ws-stream
sleep 30
docker compose logs --tail=80 backend-ws-stream
```

기대:

- 첫 30s 내 `ws_stream_connected ... reconnect_count=0`
- (Reconciler 가 wired 됐으니) reconcile 1회 실행 → exchange open/recent fetch log

✅ 통과 조건: 60s 내 재구독. CCXT fetch_open_orders / fetch_closed_orders log 1회 이상.

### G5-7. Multi-account guard (process-level)

ExchangeAccount 2개 등록 (테스트 목적). 두 번째 계정에 대해 `run_bybit_private_stream.delay(<id2>)` 수동 enqueue:

```bash
docker compose exec backend-worker uv run python -c "
from src.tasks.websocket_task import run_bybit_private_stream
run_bybit_private_stream.delay('<account-id-2>')
"
docker compose logs --tail=20 backend-ws-stream | grep duplicate
```

기대:

- 두 번째 task 가 같은 worker process 진입 시 `ws_stream_duplicate_skip account=...` 로그
- `qb_ws_duplicate_enqueue_total` metric 증가

✅ 통과 조건: 두 번째 stream 미시작 (process-level set 보호).

### G5-8. /metrics endpoint 노출

```bash
curl -s -H "Authorization: Bearer $PROMETHEUS_BEARER_TOKEN" \
  http://localhost:8000/metrics | grep -E 'qb_(active_orders|ws_|kill_switch_triggered)'
```

기대 metrics (Sprint 12 신규 6종 포함):

- `qb_active_orders` (Gauge)
- `qb_ws_orphan_event_total` / `_buffer_size`
- `qb_ws_reconcile_unknown_total` / `_skipped_total`
- `qb_ws_duplicate_enqueue_total` / `qb_ws_reconnect_total`
- `qb_kill_switch_triggered_total{trigger_type=...}`

✅ 통과 조건: 6 신규 metric 모두 노출 (값 0 도 OK).

### G5-9. Worker SIGTERM graceful shutdown

```bash
# 타이밍: ws_stream 이 active 인 상태에서
docker compose logs --tail=20 backend-ws-stream  # connected 확인
docker compose stop backend-ws-stream
docker compose logs --tail=30 backend-ws-stream | grep -E 'stop_signaled|shutdown|signal'
```

기대:

- `ws_streams_signaled_on_shutdown count=1` (worker_shutdown hook)
- `ws_stream_stop_signaled account=<UUID>`
- supervisor 가 stop_event 받고 ws.close → task graceful exit (5초 이내)

✅ 통과 조건: hang 없이 컨테이너 종료. `--pool=solo` 가 핵심.

이후 재시작 + Beat reconcile 검증:

```bash
docker compose start backend-ws-stream
# 5분 대기 (reconcile_ws_streams cron)
docker compose logs --tail=20 backend-ws-stream | grep ws_stream_reenqueued
```

✅ 통과 조건: Beat 가 누락 stream task 자동 재enqueue (`ws_stream_reenqueued account=...`).

### G5-10. Rollback 절차 리허설

```bash
# 현재 main commit hash 기록
git rev-parse origin/main > /tmp/sprint12-rollback-anchor.txt
cat /tmp/sprint12-rollback-anchor.txt

# 롤백 명령 (실 실행 X — 절차만 확인)
echo "git revert <hash> --no-edit && git push origin main"
echo "또는: git push origin <pre-merge-hash>:main --force-with-lease  (force push 위험 인지)"
```

✅ 통과 조건: rollback hash 파일 보관. 실제 발동 시 3분 내 main 복구 가능.

---

## dogfood 첫 주문 시나리오

1. **Strategy 등록** — Pine 전략 1~2개 (예: `s1_pbr.pine`)
2. **백테스트** 1회 → equity curve / metrics 정상
3. **ExchangeAccount 등록** — Bybit Futures (Linear) + Demo + leverage cap **5x** (보수적)
4. **Trading Session 활성화** — 1h 짧게 (UTC 시간 기준 현재 hour 포함)
5. **Kill Switch 임계값** — daily_loss `100 USDT`, cumulative_loss `300 USDT` (보수적)
6. **첫 주문 1건** — 작은 quantity (예: 0.001 BTC)
7. **WebSocket 이벤트 수신** 확인 (ws-stream logs)
8. **DB 상태 확인** — `SELECT id, state, exchange_order_id FROM trading.orders ORDER BY created_at DESC LIMIT 5;`
9. **Frontend 5초 이내 반영** 확인 (active orders > 0 → 5s polling)

### KS alert 시뮬 (선택)

작은 손실 만들어 daily_loss 임계 도달:

- 또는 `KILL_SWITCH_DAILY_LOSS_USD=10` 으로 임시 낮춤
- 의도적으로 이익 없는 주문 1~2회 → daily_loss < -10 USDT
- `Slack` 채널에 `[critical] Kill Switch — daily_loss` 5초 이내 도착

---

## 운영 중 모니터링

### 매일 (5분)

```bash
# 1. Service health
docker compose ps

# 2. ws-stream 연결 상태
docker compose logs --tail=20 backend-ws-stream | grep -E 'connected|reconnect_count|auth_failed'

# 3. 오늘 주문 + KS 이벤트
docker compose exec db psql -U quantbridge -c "
  SELECT count(*), state FROM trading.orders
  WHERE created_at > NOW() - INTERVAL '1 day' GROUP BY state;"
docker compose exec db psql -U quantbridge -c "
  SELECT count(*) FROM trading.kill_switch_events
  WHERE triggered_at > NOW() - INTERVAL '1 day' AND resolved_at IS NULL;"

# 4. orphan buffer (unbounded growth 감지)
curl -s localhost:8000/metrics | grep qb_ws_orphan_buffer_size
```

### 주 1회 (15분)

- Bybit Demo 지갑 잔고 변화 vs DB realized_pnl 합산 일치 확인
- `qb_ws_reconcile_unknown_total` > 0 시 → 어느 order 가 미스매치인지 조사
- WebSocket reconnect_count 추이 (1주 동안 < 10 이 정상. > 100 이면 endpoint 문제 의심)

---

## 알림 임계 조정 (운영 1주 후)

dogfood 1주차 데이터 기준:

- Slack 알림이 너무 자주 → KS 임계 완화 또는 alert 채널 분리
- Slack 알림이 너무 드물 → KS 임계 강화 또는 partial fill 시도 추가
- WebSocket 안정성 양호 → Sprint 13 prefork 복귀 검토 (현재 solo pool)

---

## 알려진 한계 (Sprint 13 이관)

- **Multi-account scaling**: 현재 process-level set + `--pool=solo`. 2계정 이상은 Redis lease 필요.
- **Auth circuit breaker**: 미구현. credentials 만료 시 Beat 5분마다 재시도 → Slack 반복. 사용자 수동 fix.
- **Partial fill cumExecQty tracking**: terminal status 만 DB transition. Sprint 13 `order_executions` table 검토.
- **Phase B Grafana**: dropped. 운영 1주 후 본인 필요 데이터 식별 후 별도 세션.
- **OKX Private WS**: Bybit dogfood 안정화 후 Sprint 13.

---

## 참조

- Plan: `~/.claude/plans/h2-sprint-12-swift-tiger.md`
- 신규 모듈: `backend/src/trading/websocket/{bybit_private_stream,state_handler,reconciliation,reconcile_fetcher}.py`
- 신규 metrics: `backend/src/common/metrics.py:163-200`
- Celery 운영: `backend/src/tasks/{celery_app,websocket_task}.py`
- Slack alert: `backend/src/common/alert.py`
