<!-- money-path-accuracy 운영 계약 델타 — 신규/변경 계약만. 전체 배경 = context-notes.md + ~/.claude/plans/money-path-accuracy-fluttering-tiger.md -->

# money-path-accuracy 운영 계약 (델타)

> close-completeness(#474) 후속. 체결된 reduce-only 청산의 실현 손익을 **거래소가 확정한 closedPnl** 로 교체하고, 죽어 있던 `filled_quantity` 를 4 체결 경로에 되살리며, BL-362 발산 알림을 텔레그램까지 팬아웃한다. **마이그레이션 1건**(핸드오프의 "마이그레이션 0" 은 설계 충돌로 대체 — 아래 C-PNL-SOURCE 참조).

## 변경 계약

### C-PNL-SOURCE — `Order.realized_pnl` 의 의미가 바뀐다 (breaking, 내부 소비 5곳)

- **이전:** 항상 pine*v2 시뮬레이션 값. close 주문 *생성 시점\_(state=`pending`)에 기록. `(sim_exit − sim_entry) × 진입 전량 × sign`, 수수료 0(`strategy_state.py:551-552`), 바 종가 기준, 실제 체결가·체결수량 무시. 체결 후 보정 없음.
- **이후:** reduce-only 주문이 `filled` 에 도달하면 Bybit `/v5/position/closed-pnl` 의 `closedPnl`(**수수료 포함 net**)로 덮어쓴다. 실측 검증 = `closedPnl == gross − (openFee + closeFee)` 정확 성립.
- **신규 컬럼 `Order.realized_pnl_synced_at`**(`TIMESTAMPTZ NULL`, 마이그레이션 `20260725_0001`). **NULL = pine_v2 추정값 / 값 있음 = 거래소 확정.** 백필 없음 — 기존 행은 전부 NULL(정직).
- 영향받는 소비처 5곳이 전부 자동으로 거래소 진실을 본다 — `kill_switch.py:97`(cumulative_loss) · `kill_switch.py:150`(daily_loss) · `order_repository.py:84`→`router.py:483-501`(세션 에쿼티 커브) · `order_repository.py:98`→`tasks/alert_rules.py:62`(loss-limit 알림) · `order_repository.py:262`→`tasks/dogfood_report.py`(일일 보고).
- 엔진 gross 값은 소실되지 않는다 — `LiveSignalEvent.realized_pnl`(`models.py:559`)에 그대로 남는다.
- **★동작 변화(의도적):** `close_service.py:78` 의 수동 청산은 `realized_pnl` 을 안 실어 지금까지 NULL 이었고 위 5곳 **전부에서 안 보였다**. backfill 이 채우므로 **수동 청산 손실이 Kill Switch 한도에 계상되기 시작한다.**

### C-CLOSEDPNL — 신규 provider 조회 (read-time, BybitFuturesProvider 전용)

- `BybitFuturesProvider.fetch_closed_pnl(creds, symbol, *, order_id, since=None) -> ClosedPnlSnapshot | None` · `fetch_closed_pnl_page(creds, symbol, *, since, limit=100) -> list[ClosedPnlSnapshot]`.
- **`ExchangeProvider` Protocol 에 넣지 않는다** — `fetch_open_positions` / `fetch_open_conditional_orders` 와 동일한 Bybit-futures 전용 메서드.
- ccxt 에 `fetch_closed_pnl` 은 **없다**. 실제 경로 = `exchange.fetch_positions_history([linear_symbol], ...)` → `privateGetV5PositionClosedPnl`. 심볼은 **정확히 1개**여야 서버측 필터가 걸린다(ccxt 가 `len(symbols)==1` 일 때만 `request['symbol']` 을 세팅).
- **값은 `position["info"]["closedPnl"]` 원본 문자열 → `Decimal`.** ccxt 파싱값 `position["realizedPnl"]` 은 `safe_number` = float 이라 사용 금지(Decimal-first).
- `since` 를 주면 `since_ms = filled_at − 120s`(클럭 스큐) + `until_ms = now` 를 **함께** 보낸다(Bybit 제약 `until − since ≤ 7일`). 안 주면 둘 다 생략 — 실측상 동작한다.
- 동일 `orderId` 행이 복수일 수 있으므로 **합산**한다. 매칭 0건 → `None`(예외 아님). `closedPnl == "0"` 은 유효값이라 `None` 이 아니다.
- API 에 orderId 필터가 없다 — 페이지를 받아 앱에서 매칭한다. ccxt 는 `nextPageCursor` 를 버린다.

### C-BACKFILL — post-fill 비동기 보정 (신규 Celery task)

- `_enqueue_closed_pnl_refresh(order)` 를 **4 체결 winner 전부**에서 호출(`tasks/trading.py` 동기 REST/watchdog + `websocket/state_handler.py` + `websocket/reconciliation.py`). `_enqueue_trailing_if_intended` 와 동일한 winner-only 계약이라 구조적으로 1회만 발화 — idempotency 컬럼 불요. `reduce_only` 아니면 no-op.
- `trading.refresh_closed_pnl` — countdown 5초 후 조회, bounded 지수 재시도(5·10·20·40초). closedPnl 미등장/provider 오류에도 **기존 값을 절대 덮어쓰지 않는다**(UPDATE 는 `snapshot is not None` 분기 안에만 존재 = 구조적 보장). 소진 시 metric + critical alert.
- `OrderRepository.backfill_exchange_realized_pnl(order_id, *, realized_pnl: Decimal, synced_at)` — `realized_pnl` 은 **non-optional**(실패가 시뮬값을 NULL 로 날리는 회귀를 타입 레벨에서 차단). CAS = `id` + `state == filled` + `realized_pnl_synced_at IS NULL` → 재호출 rowcount 0(멱등).
- provider 선택은 registry 경유 금지 — registry 는 `BybitDemoProvider`/`OkxDemoProvider`/`BybitLiveProvider` 를 돌려줄 수 있고 이들엔 이 메서드가 없다. bybit + leverage 가드 후 `BybitFuturesProvider` 직접 생성.

### C-SWEEP — 누락 보정 beat 스윕

- `trading.sweep_closed_pnl`, 5분 주기(`options.expires: 240`), 기본 `celery` 큐(라우팅 불요).
- 대상 = `list_unsynced_reduce_only_since(now − 24h)` — `state == filled` **필수**(`filled_at` 은 rejected/cancelled 도 쓰는 오버로드 컬럼) + `reduce_only` + `exchange_order_id IS NOT NULL` + `realized_pnl_synced_at IS NULL`.
- `(exchange_account_id, symbol)` 그룹당 provider **1콜**(ORDER BY 로 groupby 연속성 보장). 그룹 실패는 격리 — 나머지 그룹을 중단시키지 않는다.
- **orphan 카운터** — 페이지 안에서 우리 Order 와 매칭 안 되는 closedPnl 행 = `outcome="orphan_row"`. **계상·알림·행 생성 없음, 수치만.** ★단 이 카운터는 **구멍 크기의 하한선일 뿐이다** — 스윕 후보가 _우리_ 미동기화 주문이라, 백필이 정상이면 후보 0 → 페이지 미조회 → orphan 도 0 으로 읽힌다. 실측하려면 활성 계정·심볼 독립 열거가 필요하다(BL-438 첫 step).

### C-FILLED-QTY — 죽은 컬럼 소생 (4 경로 + 관측성 + API)

- 이전엔 watchdog(`tasks/trading.py:724`)만 write 했고 나머지 3 경로는 `transition_to_filled` 의 무조건 write 때문에 **오히려 NULL 로 덮었다**. 4 경로 전부 값을 싣는다.
- `OrderReceipt` += `filled_quantity`(ccxt `filled`). WS 는 **Bybit 원본** dict 라 `cumExecQty` 우선, reconciler 는 **ccxt 통합** dict 라 `filled` 우선 — 두 경로의 키 관례가 다르다.
- `qb_partial_fill_total{source}` — `rest|ws|watchdog|reconciler`. 증가는 `_apply_transition` 내부가 아니라 **호출자의 `rowcount == 1` 블록**(부수효과는 호출자 책임).
- `OrderResponse` += `filled_quantity` · `realized_pnl` · `realized_pnl_synced_at`. FE 주문 원장 **10 → 12열** + 손익 셀에 **거래소 확정 / 추정** 배지.

### C-DIVERGENCE-CH — BL-362 알림 양채널 (behavior change)

- `_alert_live_divergence` 가 Slack 전용 `send_critical_alert` → `send_rule_alert(settings, channel=AlertChannel.both, ...)`(채널별 예외 격리). 텔레그램 미설정이면 silent-skip(`telegram_alert.py:109-115`)이라 prod-without-creds 에서도 안전.
- **`run_live_error` 경로는 호출부에서 raw 예외 문자열을 제거**하고 클래스명만 싣는다(`live_signal.py` ~519). 이 텍스트는 미감사 경로(SyntaxError 스니펫 등)라 지금까지 의도적으로 Slack 전용이었다. 원문은 `logger.exception` 에 그대로 남는다. 나머지 두 호출부(preflight 심볼 / PineRuntimeError 텍스트)는 이미 감사된 경로라 불변.
- `_alert_live_divergence` 의 외곽 `try/except` 는 **유지**(중복 아님 — `send_rule_alert` 는 채널별 격리일 뿐 자기 호출 실패는 전파).

## 이연 (후속 BL)

- **거래소 네이티브 TP/SL·트레일링 청산 손익 미계상 (P1).** 브래킷 exit 는 우리 DB 에 아무 행도 안 남긴다(WS 고아 이벤트 5초 버퍼 후 폐기 · `execution` 토픽 미구독 · reconciler 는 local→exchange 단방향). 다음 바에서 pine 이 같은 청산을 추측해 flat 포지션에 close 를 쏘고 → rejected → 모든 손익 쿼리가 `state==filled` 로 걸러낸다. 스윕 orphan 카운터가 규모를 제공한다.
- 부분체결 후 `cancelled` 로 종료된 청산의 실체결 손익 누락(시장가 경로에선 `PartiallyFilledCanceled`→`filled` 라 현재 미도달).
- per-execution ledger(`order_executions`) — BL-014 원안의 잔여.
- entry 부분체결 시 warmup-replay 사이즈 발산.
- CSV 내보내기에 손익 출처 미표기 — 화면 배지와 달리 CSV 는 확정/추정을 구분하지 않는다.

## 운영 레시피 (상속 + 신규)

- BE pytest = **3-env 전체**(`DATABASE_URL` + `TEST_DATABASE_URL` …5436/quantbridge_test + `TEST_REDIS_LOCK_URL` …6380/3). `backend/.env.local` 의 5433 은 stale.
- **★codex 샌드박스는 localhost:5436 접속을 막는다**(`Operation not permitted`) — 워커는 DB 비의존 테스트만 돌릴 수 있으므로 **전체 스위트는 평가자가 메인 venv 로 직접** 돌려야 한다. 워커 자기보고 신뢰 금지.
- **★codex 워커는 자기가 건드린 파일에 prettier 를 돌린다** — FE 1차에서 `globals.css` 전체 재포맷(3989줄)이 나와 되돌리고 의도한 1줄만 재적용했다. 워커 종료 직후 `git diff --stat` 로 범위 검사 의무.
- worker/beat 재빌드 = `docker compose up -d --build --no-deps backend-worker backend-beat`. plain `up <svc>` 은 db/redis 를 base 5432/6379 로 되돌린다.
- **beat 엔트리는 이미지에 구워진다** — `--schedule=/data/celerybeat-schedule` 은 마지막 실행시각 shelve 일 뿐이라 스윕 추가 후 beat 재빌드 필수(§7.2 sentinel 로 stale 이미지 자동 검출).
- 독립 오라클 = `bybit_oracle.py`(asyncpg 로 `trading.exchange_accounts` 암호문 조회 → MultiFernet 복호화 → `api-demo.bybit.com` raw HMAC). `pnl` 명령 = `/v5/position/closed-pnl`.
