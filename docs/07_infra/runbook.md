# QuantBridge — Runbook (Draft)

> **상태:** Draft — 현재 dev 환경 시나리오 위주. 프로덕션 시나리오는 배포 후 보강.
> **목적:** 운영 시나리오별 진단/대응 절차.
> 의존: [`./deployment-plan.md`](./deployment-plan.md), [`./observability-plan.md`](./observability-plan.md)

---

## 1. 사용 원칙

- 시나리오 발생 시 **재현 → 진단 → 대응 → postmortem** 순서
- 명령은 복사-실행 가능한 형태로 기록
- 임시 우회는 lessons.md에 기록 후 정식 fix sprint 생성

---

## 2. Worker Crash → Stale Backtest

### 증상

- 사용자가 백테스트 제출 후 진행률 무한 stuck
- DB `backtests.status='running'` + `started_at < now - 30분`

### 진단

```bash
docker compose exec db psql -U quantbridge -d quantbridge -c "
SELECT id, status, started_at, error_reason
FROM backtests
WHERE status IN ('running', 'cancelling')
  AND COALESCE(started_at, created_at) < NOW() - INTERVAL '30 minutes'
ORDER BY started_at;
"
```

### 자동 대응 (Sprint 4 §8.3)

- 워커 startup hook이 자동으로 reclaim → `status='failed'` + `error_reason='stale_reclaimed'`
- 새 워커 기동 시 즉시 동작

### 수동 대응 (자동 reclaim 미동작 시)

```bash
docker compose exec db psql -U quantbridge -d quantbridge -c "
UPDATE backtests
SET status='failed',
    error_reason='manual_reclaim',
    completed_at=NOW()
WHERE status IN ('running', 'cancelling')
  AND COALESCE(started_at, created_at) < NOW() - INTERVAL '30 minutes';
"
```

> 주의: 워커가 살아있는데 manual reclaim 시 race condition. 워커 정지 후 실행 권장.

### Sprint 5 개선

- Beat task 주기 reclaim (5분 간격)
- Multi-worker split-brain 방어 (`inspect().active()` 또는 Redis lock)

---

## 3. Cancel Stuck

### 증상

- 사용자가 cancel 요청 후 `status='cancelling'`에서 멈춤

### 진단 — 3-Guard 위치 확인

1. Guard #1 (pickup 직전) — 워커 pickup 전 cancel 요청 시 즉시 처리
2. Guard #2 (pre-engine) — engine 호출 직전
3. Guard #3 (post-engine) — 결과 저장 직전

워커 로그 확인:

```bash
# Celery worker가 어느 guard에 도달했는지 로그 추적
# (Sprint 5 structured logging 도입 후 grep 친화적)
```

### 대응

- 정상 흐름: 워커가 다음 guard에 도달하면 자동 finalize
- 워커 crash 시: stale reclaim 패턴 (위 §2)
- `finalize_cancelled` rows=0 시 fallback 동작 — logger.error 발생 → 강제 CANCELLED 처리

---

## 4. DB Migration 실패 / Rollback

### 자동 적용 (Docker entrypoint)

```bash
# 배포 시 컨테이너 entrypoint
alembic upgrade head
```

### Rollback

```bash
cd backend
uv run alembic downgrade -1   # 직전 버전
uv run alembic downgrade <revision>  # 특정 버전
```

### 데이터 파괴 변경 절차 (`.ai/stacks/fastapi/backend.md` §9)

- **2단계 배포**:
  1. 코드에서 사용 중단 (컬럼 read만 유지)
  2. 다음 배포에서 컬럼 삭제 + alembic migration

> 컬럼/테이블 즉시 삭제 금지 — 이전 버전 인스턴스 충돌 가능.

### Multi-head 감지

```bash
uv run alembic heads
# 1개 head만 정상. 2개 이상이면 merge revision 생성 필요
uv run alembic merge -m "merge heads" head1 head2
```

---

## 5. Clerk Webhook 검증 실패

### 증상

- API 로그에 `clerk_webhook_invalid_signature` 에러 burst

### 진단

- `CLERK_WEBHOOK_SECRET` 정확성 확인 (Clerk Dashboard → Webhooks → endpoint → Signing Secret)
- 서버 시간 동기화 확인 (timestamp drift)
- Endpoint URL 일치 확인

### 대응

1. 환경 변수 재확인/재배포
2. 시간 drift 시 NTP 재동기화
3. Clerk Dashboard에서 endpoint redeliver 시도

---

## 6. CCXT Rate Limit _(Sprint 5+)_

### 증상

- OHLCV 동기화 task 실패율 증가, exchange `429` 응답

### 대응

- Worker backoff 로직 동작 확인 (지수 백오프)
- 동기화 동시 작업 수 제한 (`--concurrency` 조정)
- 거래소별 rate limit 정책 확인 (Binance: 6000/분, Bybit: 50/s 등)

> Sprint 5 spec에서 backoff 정책 및 concurrency 가이드라인 확정 예정.

---

## 7. Redis 메모리 saturation

### 증상

- Celery enqueue 실패, 캐시 hit miss 폭증

### 진단

```bash
docker compose exec redis redis-cli INFO memory
# used_memory_human, maxmemory_human 확인
```

### 대응

- LRU eviction 정책 활성 — 캐시는 자동 회수 (DB 0)
- Celery 큐 (DB 1)는 별도, eviction 시 task 손실 가능 — `maxmemory` 증설 검토
- 임시: `redis-cli -n 0 FLUSHDB`로 캐시 flush

---

## 8. 백테스트 결과 정확도 회귀

### 증상

- snapshot 테스트 실패 (vectorbt 직접 실행 결과와 차이)

### 진단

```bash
cd backend && uv run pytest tests/backtest/snapshot/ -v
```

- 변경 의도된 결과 → snapshot 갱신 (`pytest --snapshot-update`)
- 의도 없는 회귀 → engine 변경 사항 git diff 검토

### 대응

- vectorbt 버전 확인 (`pyproject.toml`)
- 합성 fixture vs TimescaleProvider 결과 차이라면 `OHLCVProvider` 추상화 검증

---

## 9. 인시던트 후 절차

1. **타임라인 기록** — 발생 시각, 감지, 대응, 해소
2. **근본 원인 분석** (RCA) — 5 Whys
3. **lessons.md 업데이트** — 재발 방지 규칙
4. **CLAUDE.md 승격 검토** — 3회 반복 시 영구 규칙
5. **Postmortem 문서** — `dev-log/incident-YYYY-MM-DD-summary.md` (선택)

---

## 10. 일상 점검 체크리스트 (운영 후 도입)

| 주기 | 항목                                                         |
| ---- | ------------------------------------------------------------ |
| 일   | DB 디스크 사용률, Redis 메모리, 백테스트 fail 비율           |
| 주   | Stale reclaim 빈도, Webhook 검증 실패 추이, CI pass rate     |
| 월   | 의존성 업데이트 (uv lock, pnpm-lock), security advisory 검토 |
| 분기 | DR 시뮬레이션 (DB 백업 복원), 인시던트 리뷰                  |

---

## 11. 결정 대기 항목 (`[확인 필요]`)

- On-call 정책 / 채널 (Sprint 8+)
- SLA / SLO 정의
- DR 백업 정책 (RPO/RTO 목표)
- 보안 인시던트 대응 절차

---

## 12. Bybit Testnet → Mainnet 전환 (H1 Stealth 종료 게이트)

> **목적:** 본인 실자본 1~2주 dogfood 전 안전 체크 + 소액 검증.
> **전제:** Sprint 8+ Kill Switch capital_base 동적 바인딩 완료 (PR #38).
> 상세 체크리스트: [`./bybit-mainnet-checklist.md`](./bybit-mainnet-checklist.md).

### 12.1 전환 전 사전 체크 (ONE-TIME)

**API Key 발급 + 권한 설정 (Bybit 웹):**

- [ ] API Key 권한: `Read + Trade` 만 활성. **Withdraw 절대 비활성**.
- [ ] IP whitelist 등록 (고정 IP 필요 — Cloud Run 사용 시 static egress)
- [ ] 계정에 2FA 활성 (TOTP + 이메일)
- [ ] API Key에 레이블 지정 (`quantbridge-mainnet-v1`)

**환경 변수 준비:**

```bash
# .env.mainnet (프로덕션 전용, 절대 커밋 금지)
BYBIT_API_KEY=...
BYBIT_API_SECRET=...
EXCHANGE_PROVIDER=bybit_futures
BYBIT_FUTURES_MAX_LEVERAGE=1  # 초기 1:1. 검증 후 점진 상향
KILL_SWITCH_CAPITAL_BASE_USD=100  # mainnet 첫 주는 fallback도 소액
KILL_SWITCH_DAILY_LOSS_USD=10
KILL_SWITCH_CUMULATIVE_LOSS_PERCENT=5
```

**BybitFuturesProvider testnet 하드코딩 해제:**

- [ ] `backend/src/trading/providers.py` — `"testnet": True` → `Credentials.testnet` 필드 기반으로 분기
- [ ] `ExchangeAccount.mode == "live"`일 때만 mainnet URL 사용
- [ ] 해당 PR은 별도 (이번 H1 범위 밖, dogfood 직전 단발성)

### 12.2 Dry-run (Demo Smoke)

**목표:** 실제 mainnet 주문 전 demo 환경에서 전체 경로 1회 검증.

```bash
# backend/scripts/bybit_demo_smoke.py — 소액 BUY 1건 → 즉시 CANCEL
cd backend
uv run python scripts/bybit_demo_smoke.py \
    --api-key "$BYBIT_DEMO_KEY" \
    --api-secret "$BYBIT_DEMO_SECRET" \
    --symbol "BTC/USDT:USDT" \
    --quantity 0.001 \
    --leverage 1
```

**검증 포인트 (스크립트 출력으로 확인):**

- [ ] `fetch_balance` USDT > 0
- [ ] `set_margin_mode` + `set_leverage` 성공
- [ ] `create_order` exchange_order_id 수신
- [ ] `cancel_order` 정상 종료

### 12.3 Mainnet 1st Order 체크리스트

**반드시 사람이 눈으로 확인 후 실행:**

1. **DB 잔고 확인** — ExchangeAccount.exchange == bybit + mode == live 계정 등록 완료?
2. **Kill Switch 설정** — 위 환경 변수 모두 conservative (daily loss $10, cumulative 5%)
3. **소액 주문** — `quantity=0.0001`, `leverage=1` (notional ≤ $6 at BTC $60k)
4. **실행 직후 확인 (30초 이내):**
   - [ ] Bybit Web UI에 포지션 표시
   - [ ] QB DB `trading.orders` row status='filled' (또는 'submitted' 경과)
   - [ ] structured log `order_executed` 필드 5종 출현
5. **즉시 close** — 수동 close 또는 반대 주문으로 포지션 0

### 12.4 일주일 Dogfood 운영 체크

**매일 (5분):**

- [ ] `SELECT count(*), status FROM trading.orders WHERE created_at > NOW() - INTERVAL '24h' GROUP BY status` — fail 비율 확인
- [ ] Bybit Web UI "Trade History" vs QB DB 대조 (5건 샘플)
- [ ] Kill Switch 이벤트 `SELECT * FROM trading.kill_switch_events WHERE created_at > NOW() - INTERVAL '24h'`

**매주 (30분):**

- [ ] API key rotate (`Bybit Web → Revoke old → 새 key 발급 → .env 교체 → 재배포`)
- [ ] PnL 리포트 (fee 차감 후) — Bybit export CSV와 QB 계산 비교
- [ ] Runbook §9 인시던트 절차 재검토

### 12.5 Emergency Kill

**수동 kill switch 트리거 (긴급):**

```bash
# DB 직접 삽입으로 모든 전략 차단
docker compose exec db psql -U quantbridge -d quantbridge -c "
INSERT INTO trading.kill_switch_events (strategy_id, trigger_type, trigger_value, threshold, reason)
SELECT id, 'api_error', 999, 1, 'manual_emergency_kill_2026_04_XX'
FROM trading.strategies WHERE user_id = '<user_uuid>';
"
```

**API Key revoke (완전 차단):**

1. Bybit Web → API Management → 해당 key REVOKE
2. QB 서비스에서 `trading.exchange_accounts` status='disabled' UPDATE
3. 오픈 포지션이 있으면 Bybit Web에서 수동 close

### 12.6 H2 진입 게이트

본 섹션의 1~5주 dogfood 완료 + 아래 정량 기준 충족 시 H2 진입:

- 실자본 drawdown < 10%
- Kill Switch false positive < 1건/주
- 시스템 다운타임 0분
- 본인 "이 시스템을 친한 지인 5명에게 추천할 수 있다" 주관 평가 PASS

---

## 13. 참고

- Backtest 3-guard pattern: `docs/superpowers/specs/2026-04-15-sprint4-backtest-api-design.md` §5.1
- Stale reclaim: 동일 spec §8.3
- Sprint 4 D1~D10 교훈: [`../guides/sprint-kickoff-template.md`](../guides/sprint-kickoff-template.md)
- Alembic: `.ai/stacks/fastapi/backend.md` §9

---

## 변경 이력

- **2026-04-16** — Draft 초안 작성 (Sprint 5 Stage A)
- **2026-04-20** — §12 Bybit Testnet → Mainnet 전환 게이트 추가 (H1 Stealth 종료 준비, Step 4)
