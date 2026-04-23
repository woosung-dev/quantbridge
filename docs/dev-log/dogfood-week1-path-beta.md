# Dogfood Week 1 — Path β 병행 운영 기록

> **운영 기간:** 2026-04-24 ~  
> **전략:** `s1_pbr.pine` (Pivot Breakout Reversal)  
> **환경:** Bybit Demo Trading (`api-demo.bybit.com`)  
> **연관 문서:** [h1-testnet-dogfood-guide.md](../07_infra/h1-testnet-dogfood-guide.md)  
> **체크리스트:** [dogfood-checklist.md](../guides/dogfood-checklist.md)

---

## 초기 설정값 (Baseline)

| 항목                                | 값                         |
| ----------------------------------- | -------------------------- |
| Symbol                              | BTC/USDT:USDT              |
| Timeframe                           | 1h                         |
| Leverage                            | 1x                         |
| Quantity                            | 0.001 BTC                  |
| Margin mode                         | cross                      |
| Order type                          | limit (market 주문 비활성) |
| Demo USDT 초기 잔고                 | — (시작 시 기입)           |
| KILL_SWITCH_CAPITAL_BASE_USD        | 10,000                     |
| KILL_SWITCH_DAILY_LOSS_USD          | 500                        |
| KILL_SWITCH_CUMULATIVE_LOSS_PERCENT | 5                          |
| BYBIT_FUTURES_MAX_LEVERAGE          | 1                          |

---

## s1_pbr 백테스트 Baseline (기록 시 채우기)

> 최근 백테스트 run 기준 — `/backtests` UI 또는 DB `backtest_runs` 테이블에서 확인  
> 기간: 최소 90일 이상 권장

| 지표                   | 값                                                          |
| ---------------------- | ----------------------------------------------------------- |
| Sharpe Ratio           | —                                                           |
| Win Rate (%)           | —                                                           |
| Max Drawdown (%)       | —                                                           |
| Profit Factor          | —                                                           |
| Total Trades           | —                                                           |
| Avg Trade Duration (h) | —                                                           |
| Avg Slippage (bp)      | — (백테스트 기준 0bp, 실거래 비교용)                        |
| Coverage Score (%)     | — (Coverage Analyzer `used_functions / total_called * 100`) |
| 백테스트 기간          | — (예: 2025-01-01 ~ 2026-04-24)                             |
| Run ID                 | —                                                           |
| 실행 일시              | —                                                           |

---

## 환경 준비 체크리스트 (최초 1회)

- [ ] `.env.demo` 파일 생성 (`EXCHANGE_PROVIDER`, `BYBIT_DEMO_KEY`, `BYBIT_DEMO_SECRET` 포함)
- [ ] `.env.demo`가 `.gitignore`에 포함됨 확인
- [ ] Demo USDT 잔고 충전 (Bybit Demo Trading → Asset → USDT 지급)
- [ ] `docker compose up -d` 모든 서비스 UP
- [ ] `alembic upgrade head` 완료
- [ ] Smoke test PASS (`backend/scripts/bybit_demo_smoke.py`)
- [ ] Exchange Account (Demo) UI 등록
- [ ] s1_pbr.pine 전략 백테스트 baseline 기록 (위 표 채우기)

---

## 일일 로그

### 2026-04-24 (Day 1)

**환경 준비 상태:**

- [ ] Docker 서비스 UP
- [ ] DB 마이그레이션 최신
- [ ] Smoke test PASS
- [ ] Exchange Account (Demo) 등록

**Demo USDT 잔고:** —

**주문 실행 현황:**

| 시각(UTC) | Symbol | Side | Qty | 진입가 | 청산가 | 슬리피지(bp) | state | Kill Switch | 비고            |
| --------- | ------ | ---- | --- | ------ | ------ | ------------ | ----- | ----------- | --------------- |
| —         | —      | —    | —   | —      | —      | —            | —     | N           | 첫 주문 대기 중 |

**Kill Switch 이벤트:** 없음

**Pine Coverage 현황:**

- [ ] `parse-preview` API 호출하여 `unsupported_functions` 빈 배열 확인

**특이사항:**

- 환경 세팅 중

---

## 주간 요약 템플릿

> 매 주 마지막 날(일요일) 작성 후 `docs/dev-log/dogfood-week{N}-summary.md`로 복사

| 항목                          | 값  | 참고                                                                                  |
| ----------------------------- | --- | ------------------------------------------------------------------------------------- |
| 총 주문 수                    | —   | `SELECT COUNT(*) FROM trading.orders WHERE created_at > '<week_start>'`               |
| 체결 성공률 (%)               | —   | `state='filled' / total * 100`                                                        |
| 총 P&L (demo USDT)            | —   | Bybit Demo UI 포트폴리오                                                              |
| 예상 P&L vs 실현 P&L 편차     | —   | 백테스트 baseline 대비                                                                |
| Avg 슬리피지 (bp)             | —   | 진입가 vs 예상가                                                                      |
| Kill Switch 발동 횟수         | —   | `SELECT COUNT(*) FROM trading.kill_switch_events WHERE triggered_at > '<week_start>'` |
| Kill Switch 사유              | —   | `trigger_type` 값 나열                                                                |
| Coverage Analyzer 미지원 함수 | —   | `parse-preview` 응답 `unsupported_functions`                                          |
| 발견된 버그/이슈 수           | —   | `docs/TODO.md` Blocked 항목                                                           |
| 주요 발견/이슈                | —   | 자유 기술                                                                             |

---

## 에스컬레이션 절차

### Kill Switch 발동 시 (Day 1~7)

1. Bybit Demo UI 에서 오픈 포지션 수동 확인
2. `trading.kill_switch_events` 테이블에서 `trigger_type`, `trigger_value` 확인
3. `docs/TODO.md` Blocked에 발동 사유 기록
4. Kill Switch 임계값이 너무 낮다고 판단 시 `KILL_SWITCH_DAILY_LOSS_USD` 조정 → `docs/07_infra/h1-testnet-dogfood-guide.md` §3 "리스크 설정" 재검토

### 서비스 다운 시

```bash
docker compose logs -f backend    # 에러 원인 파악
docker compose restart backend    # 재시작 시도
cd backend && uv run alembic current  # DB 마이그레이션 상태 확인
```

### Smoke test 미통과 시

- 원인별 대응: `docs/superpowers/plans/2026-04-24-h2-sprint1-phase-a.md` §T4-c 참조
- 잔여 주문 정리 필수: `backend/scripts/cancel_all_demo_orders.py` 또는 Bybit Demo UI

### 잔여 오픈 포지션 발생 시 (비정상 종료)

```sql
-- 미체결 주문 확인
SELECT id, exchange_order_id, state, created_at
FROM trading.orders
WHERE state IN ('pending', 'submitted')
ORDER BY created_at DESC;
```

Bybit Demo UI에서 수동 취소 후 DB 상태 수동 업데이트 (개발 환경 한정):

```sql
UPDATE trading.orders SET state = 'cancelled' WHERE id = '<id>';
```

---

## 주요 발견 사항 및 버그

<!-- 운영 중 발견된 이슈를 여기 기록. 형식: [날짜] [심각도] 제목 — 내용 -->

---

## 참조

- [ADR-011 Pine Execution Strategy v4](011-pine-execution-strategy-v4.md)
- [Path β Trust Layer CI 설계](013-trust-layer-ci-design.md)
- [Sprint Y1 Coverage Analyzer](016-sprint-y1-coverage-analyzer.md)
- [Dogfood Checklist](../guides/dogfood-checklist.md)
- [H2 Sprint 1 Phase A SDD](../superpowers/plans/2026-04-24-h2-sprint1-phase-a.md)
