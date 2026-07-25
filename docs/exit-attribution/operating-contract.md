<!-- exit-attribution 운영 계약 델타 — 신규/변경 계약만. 전체 배경 = context-notes.md -->

# exit-attribution 운영 계약 (델타)

> money-path-accuracy(#475) 후속. 거래소에만 존재하는 청산 기록을 **원장으로 흡수해 보이게** 만들고, 우리 주문의 손익만 정확히 계상한다. 귀속이 불확실한 것은 리스크 게이트에 넣지 않는다. **마이그레이션 1건**(`20260725_0002`, 신규 테이블 1개).
>
> **★범위 축소 반영 (2026-07-25, 머지 전).** 과거 90일 catch-up 기계장치를 걷어내고 **원장은 최근 7일만** 담는다. 폐기된 계약은 C-EXIT-WATERMARK(아래 보존), 개정된 계약은 C-SWEEP-V2 / C-PROVIDER-WINDOW, 신설은 C-LEDGER-HORIZON.

## 변경 계약

### C-EXIT-LEDGER — `trading.exchange_exits` 신설 (행 단위 원본 보존)

- 거래소 closed-pnl **원본 행 1개당 1행**을 저장한다. 집계해서 저장하지 않는다. Bybit 은 한 청산 주문을 여러 행으로 쪼갤 수 있고 7일 창을 나눠 조회하면 분할 행이 창 경계에 갈릴 수 있는데, 원본을 다 갖고 있으면 **언제든 재집계**할 수 있어 부분합이 CAS 로 영구 고정되지 않는다.
- 멱등 키 = `UNIQUE (exchange_account_id, row_hash)`. `ExchangeExit.compute_row_hash` 는 `orderId·createdTime·updatedTime·closedSize·closedPnl·avgEntryPrice·avgExitPrice·cumExitValue` 를 `\x1f` 로 join 해 sha256 한다.
  - **구분자는 제어문자여야 한다** — 인쇄 가능한 구분자는 값 안에 섞이면 필드 경계를 옮겨 서로 다른 행이 같은 해시를 얻는다.
  - **`None` 과 `""` 는 반드시 같게 정규화**한다. 거래소가 한 주기엔 빈 문자열을, 다른 주기엔 키를 생략하면 같은 행이 두 해시로 갈려 UNIQUE 를 통과하고 `aggregate_closed_pnl` 이 두 번 합산해 `realized_pnl` 이 실제의 2배로 백필된다.
  - `order_id` 가 비면 `ValueError`. 전 필드가 비면 해시가 한 값으로 축퇴해 서로 다른 행이 UNIQUE 에 흡수된다.
- **`side` 는 거래소 원본 `info.side`** 를 넣는다. ccxt `parse_position` 은 closed-pnl 행(`closedSize` 존재 = `isHistory`)에서 `Buy→short` / `Sell→long` 으로 **뒤집는다**.
- `raw` 는 `postgresql.JSONB(none_as_null=True)` + NOT NULL. `Order.webhook_payload` 는 이 지정이 없어 Python `None` 이 SQL NULL 이 아니라 JSONB `'null'` 로 저장돼 있고(실측 15/17행) `IS NULL` 술어가 무력하다. 같은 함정을 반복하지 않는다.
- `upsert_rows` 는 `on_conflict_do_nothing(...).returning(row_hash)` 로 **새로 들어간 행만** 돌려주고 커밋하지 않는다(호출자 책임). asyncpg 인자 상한 32767 때문에 500행 단위로 청킹한다.

### ~~C-EXIT-WATERMARK~~ — **폐기 (범위 축소, 머지 전)**

> 테이블·모델·리포지토리 메서드 전부 제거했다. **아래 내용은 다시 만들 때를 위해 보존한다** — 특히 첫 항목은 실측으로 반증한 함정이므로 재도입 시 같은 실수를 반복하지 말 것.
>
> **폐기 이유.** ① 이 테이블을 만든 직접적 목적(20일 전 미동기화 4건 회수)이 로컬 개발 DB 전소로 소멸 ② **실측 — 이 기계장치는 지속 기제가 아니라 ~13주기(약 65분) 후 영구 자기정지하는 일회성 catch-up 이었다.** 워터마크는 주기당 7일 후퇴하는데 horizon 은 매 주기 `now` 에서 재계산돼 전진하므로 `end_ms <= horizon_ms` 가 영구 latch 된다(DB 영속이라 프로세스 재시작으로도 안 풀림). 정상 상태에서 축소 전후 동작은 동일하다. 재도입은 상시 beat 경로가 아니라 **일회성 catch-up** 형태가 맞다 → [BL-452](../REFACTORING-BACKLOG.md#bl-452).

- **진행 상태를 원장의 `min(exchange_created_at)` 에서 파생하면 안 된다.** 청산이 한 건도 없던 과거 구간을 만나면 삽입이 0 이라 min 이 그대로여서 같은 빈 창을 영원히 다시 조회하고 그 이전 역사에 도달하지 못한다. **실측 반증** — 07-24 행 4건만 적재된 뒤 07-17~07-24 빈 구간에서 정지해 07-05 행 7건(백필 대상 전량)에 영영 도달하지 못했다.
- `set_backfilled_from` 은 **과거로만** 전진한다(`backfilled_from IS NULL OR > boundary` 조건부 upsert). 재실행이 경계를 앞당기면 이미 훑은 구간을 다시 판다.
- 경계 전진은 원장 upsert 와 **같은 트랜잭션**에서 커밋한다. 창 처리가 실패하면 경계가 그대로라 다음 주기에 같은 창을 재시도해 구멍이 안 생기고, 행이 0건인 창도 경계를 전진시켜 빈 구간에서 멈추지 않는다.

### C-SWEEP-V2 — `trading.sweep_closed_pnl` 재작성 (task 이름·beat 엔트리 불변)

- 후보 열거가 "우리 미동기화 주문"에서 **`ExchangeAccountRepository.list_by_exchange(bybit)` 계정 독립 열거**로 바뀐다. 우리 주문이 하나도 없어도 거래소 청산을 본다.
- **계정당 창 1개 — `[now−7d, now]`** (범위 축소로 개정. 과거 창·horizon 제거). 그보다 오래된 거래소 청산은 원장에 들어오지 않는다 → C-LEDGER-HORIZON.
- **심볼 없이 계정당 1콜.** ccxt `fetch_positions_history` 는 `symbols` 가 `None` 이면 `request['symbol']` 을 넣지 않고 `filter_by_array` 도 통과시킨다(4.5.49 소스 + raw API 양쪽 실측).
- **보강 조회는 조건부** — 매칭 안 된 `order_id` 가 있을 때만 `fetch_closed_orders` 1콜. 정상 상태에선 0콜. 실패는 삼키고 분류만 `unknown` 이 된다(적재를 막지 않는다).
- **백필은 원장 전체 집계**(`ExchangeExitRepository.aggregate_closed_pnl`)로 한다. 단일 fetch 결과가 아니므로 분할 행이 창 경계에 갈려도 부분합이 고정되지 않는다. 기존 `backfill_exchange_realized_pnl` 3-guard CAS 를 그대로 쓴다.
- **★이미 synced 된 주문도 원장과 대조해 정정한다**(`resync_exchange_realized_pnl`). 체결 직후 `refresh_closed_pnl` 은 원장을 거치지 않고 **단일 조회 결과**를 CAS 하므로, 분할 행 중 일부만 보이는 순간에 걸리면 부분합이 `synced_at` 과 함께 고정되고 미동기화 술어를 쓰는 백필 경로가 그 주문을 영영 건너뛴다. 값이 같으면 rowcount 0 이라 멱등하다.
- **잘림은 provider 가 로그로 알린다** (범위 축소로 개정 — 아래 C-PROVIDER-WINDOW). 호출자가 창을 하나만 보므로 워터마크로 대응할 수단이 없어졌다.
- **원장 필수 필드를 못 만든 행**(시각·심볼·방향 결측)은 `malformed_row` 로 계상한다. 로그만 남기면 소실이 관측되지 않는다.
- summary/metric 증가는 **커밋 성공 뒤**에만 한다. 반환 shape = `{"accounts","inserted","backfilled","resynced","alerted"}` (`windows` 키 제거 — 계정당 창이 항상 1이면 "commit 에 도달한 계정 수"의 중복이고 이름이 오독을 부른다. 실패 관측은 `qb_closed_pnl_backfill_total{outcome="failed_provider"}` 가 담당).
- **★원장 upsert 뒤 `commit` 은 필수다.** 알림(`_alert_new_exchange_exits`)과 백필은 **새 세션**으로 되읽으므로 커밋이 빠지면 둘 다 조용히 아무 일도 하지 않는데 `summary["inserted"]` 는 여전히 N 을 보고한다. 테스트 페이크가 트랜잭션을 흉내내(커밋 시에만 행이 보이게) 이 슬립을 잡는다 — 커밋을 지우면 3건이 red 가 되는 것을 실증했다.
- **`orphan_row` 계상 제거** — 대조 집합이 후보 그룹뿐이라 이미 synced 된 우리 주문까지 orphan 으로 셌고, 계정 단위 열거에선 매 주기 영구 재계상된다. 신호는 `qb_exchange_exit_rows_total` 이 준다. `qb_closed_pnl_backfill_total` 의 8-outcome 계약은 **불변**.

### C-EXIT-CLASSIFY — 분류·귀속은 라벨 전용 (게이트 입력 아님)

- `classification` 7종 — `ours` / `bracket_tp` / `bracket_sl` / `trailing` / `liquidation` / `external_manual` / `unknown`. `createType` 우선, 비거나 낯설면 `stopOrderType` 폴백, 그래도 모르면 정직하게 `unknown`.
- `orderLinkId` 는 **UUID 형식일 때만** `ours` 로 본다. 우리 앱은 `orderLinkId = str(Order.id)` 를 싣는다(`tasks/trading.py:354`). 값이 있다는 것만으로 `ours` 로 보면 외부 도구가 임의 client order id 를 단 주문이 미귀속 알림에서 조용히 빠진다.
- `attribution_confidence` 3종 — `exact`(우리 Order 와 id 매칭) / `inferred`(가격 일치 **AND** 그 시각 앱 보유 포지션 존재, 둘 다) / `none`.
- **★`inferred` 는 이번 스프린트에서 머니-패스에 절대 들어가지 않는다.** 실측 표본 4건에서 4/4 정답이었지만 그 기간 활성 세션이 사실상 하나여서 검정력이 없다. 같은 계정·심볼에 서로 다른 전략의 활성 세션이 공존할 수 있다(`uq_live_sessions_active_unique` 는 `(user, strategy, account, symbol)` 부분 인덱스).
- `list_filled_for_attribution` 은 **최근 N건**(DESC LIMIT 후 ASC 재정렬)을 준다. 오름차순 LIMIT 로 자르면 오래된 주문만 남아 최근 청산의 진입이 표본 밖으로 밀리고 순포지션 합산이 절단 부산물이 된다.

### C-EXIT-ALERT — 신규 미귀속 행 알림 (1회성)

- 새로 적재된 행 중 `classification != ours` 인 것만 `send_rule_alert(channel=both)` 로 계정당 1회. **원장 UNIQUE 가 "본 적 있음"을 영속하므로 같은 행으로 재발화하지 않는다.**
- 조회부터 알림까지 전부 try 안에 둔다. 원장은 이미 커밋됐고 provider 도 정상인데 알림 실패가 계정 핸들러로 새면 `outcome="failed_provider"` 로 잘못 계상된다.

### C-PROVIDER-WINDOW — 7일 창 계약

- Bybit 은 `endTime − startTime > 7일` 을 `retCode=10001` 로 거부한다(실측). `_CLOSED_PNL_MAX_WINDOW_MS = 604_800_000`, `_validate_closed_pnl_window` 가 앱 경계에서 먼저 막는다.
- **★커서 경계는 포함이다 — `until = oldest_ms`(`oldest_ms - 1` 금지).** 한 청산 주문의 분할 행은 `createdTime` 을 공유할 수 있어(구분은 `updatedTime`), 같은 밀리초 행이 페이지 상한을 넘으면 커서를 그 아래로 내리는 순간 남은 tie 행을 다시 조회할 방법이 없다. 게다가 다음 페이지가 짧으면 완전 조회라고 보고해 **500행 상한에 걸리지 않고도 조용히 누락**된다. 누락 행이 우리 주문의 분할이면 부분합이 `realized_pnl` 로 영구 고정된다. 겹쳐 읽힌 중복은 원장 `UNIQUE(row_hash)` 가 흡수하므로 이중 합산이 없다. **꽉 찬 페이지에서 커서가 더 못 가면 완전 조회를 주장하지 않는다** — 유일한 증거는 상한 미만 페이지다. (`fetch_closed_order_meta` 는 분류 라벨 전용 + `setdefault` 멱등이라 예외로 두었다 → BL-452.)
- **페이징 커서 축은 서버 필터와 같아야 한다.** Bybit `startTime/endTime` 과 ccxt `filter_by_since_limit` 은 모두 `createdTime` 기준인데 `updatedTime` 으로 당기면(며칠 열려 있던 브래킷 주문은 둘이 크게 벌어진다) 커서가 **앞으로 가** 창이 7일을 넘고 같은 페이지를 `max_pages` 만큼 헛돈다. 커서가 진행하지 않거나 창을 벗어나면 중단한다.
- `fetch_closed_pnl_page` 는 기존 호출자 계약을 유지한 채 창을 최근 7일로 클램프한다. 오래된 `since` 가 와도 예외 대신 최근 7일만 본다.
- **주문 이력은 `fetch_closed_orders`** 를 쓴다. ccxt `fetch_orders` 는 Bybit UTA 계정에서 `NotSupported` 를 던진다.
- **`fetch_closed_pnl_window` 는 `list[ClosedPnlSnapshot]` 을 돌려준다** (범위 축소로 `ClosedPnlWindow(rows, truncated)` dataclass 제거). 잘림은 반환값이 아니라 **발생 지점 로그**로 알린다 — `logger.warning("closed_pnl_window_truncated", extra={... , **log_context})`.
  - **최종 `truncated` 값에 로그한다.** 이 플래그는 3경로로 True 가 된다 — `max_pages` 소진(루프 fall-through) · 꽉 찬 페이지에 쓸 커서가 없음 · 커서 정지. 소진만 로그하면 나머지 2건이 기존 신호보다 후퇴한다.
  - **`log_context` 로 어느 조회인지 식별한다.** 이 함수는 `creds` 만 받고 스윕은 `symbol=None` + 모든 계정에 같은 창을 넘기므로 로그 줄이 계정 간 바이트 동일해진다. 게다가 체결 직후 refresh 경로(`fetch_closed_pnl` → `fetch_closed_pnl_page`)도 같은 함수를 쓰는데 그쪽 잘림은 의미가 다르다(창이 `[since−1h, now]` 이고 대상 주문 행이 가장 오래된 쪽에 있어 역방향 페이징이 먼저 자른다). 스윕은 `account_id`, refresh 는 `symbol` 을 싣는다.
  - **메트릭 라벨은 추가하지 않는다** — `qb_closed_pnl_backfill_total` 의 8-outcome 계약이 불변이고 `metrics.py` 는 `account_id` 를 라벨로 금지한다.
- `ClosedPnlSnapshot` 확장 필드는 **끝에 default 로** 붙였다(기존 위치 인자 5개 호환). 기존 3필드(`closedSize`/`avgExitPrice`/`updatedTime`)는 **strict 파싱을 유지**한다 — 파싱 실패를 None 으로 삼키면 행이 살아남아 `malformed_row` 관측치가 사라지고 분할 청산에서 `closed_size` 만 과소 합산돼 손익과 수량이 모순된 원장 행이 생긴다.
- `aggregate_closed_pnl_by_order` 의 반환 `raw` 와 비합산 필드는 `rows[-1]` 값이라 합산 `closed_pnl` 과 어긋난다. **이 결과를 원장에 영속하면 안 된다** — 원장은 `fetch_closed_pnl_window` 의 행 단위 스냅샷만 적재한다.

### C-LEDGER-HONESTY — 원장 표면 정직성 (FE)

- 손익 셀·CSV 는 `state === "filled"` 일 때만 `realized_pnl` 을 노출한다. 판정은 `displayRealizedPnl` 한 곳에서만 하고 화면·CSV·부호 톤이 공유한다. 감춘 셀에는 상태별 사유 `title` 을 붙인다.
- CSV 는 손익 출처·부분체결 마커·시각의 날짜를 함께 싣는다. 손익 출처는 화면 12열 SSOT(`ORDER_TABLE_HEADER`)가 아니라 `ORDER_CSV_EXTRA_HEADER` 에서 온다(화면 열 수와 어긋나면 안 된다).

### C-LEDGER-HORIZON — 원장은 최근 7일만 담는다 (신설, 범위 축소)

> 숨은 제약이 아니라 **명시적 계약**이다. 넷 다 의도된 트레이드오프이며 [BL-452](../REFACTORING-BACKLOG.md#bl-452) 에 등재했다.

1. 스윕은 매 주기 `[now−7d, now]` **한 창**만 조회한다. 그보다 오래된 거래소 청산은 원장에 들어오지 않는다.
2. 따라서 **백필·재동기화도 7일 안에서만** 동작한다(#475 의 24시간 한계를 7일로 넓힌 것). 7일 넘게 미동기화로 남은 주문은 자동으로 안 고쳐진다.
3. 워커가 7일 넘게 죽어 있으면 그 구간은 영영 조회되지 않는다.
4. 7일 500행(`_CLOSED_PNL_MAX_PAGES=5` × `limit=100`) 상한을 넘는 계정은 가장 오래된 행을 잃는다. **관측은 로그뿐.**

**★2·3 은 축소 전에도 정상 상태의 동작이었다.** 과거 catch-up 이 ~13주기 후 영구 latch-off 되기 때문이다(C-EXIT-WATERMARK 폐기 사유 ②). 실제로 없어진 것은 일회성 90일 역사 수입 하나다.

**dogfood 정직 각주** — 로컬 개발 DB 전소로 주문 이력이 없고, 07-05 측정 행 7건(백필 대상 전량)은 20일 전이라 **7일 창으로는 구조적으로 도달하지 않는다.** 백필 종단 검증(우리 주문이 거래소 확정값으로 정정되는 대조)은 이번 스프린트에서 불가하다.

### C-TESTDB-GUARD — 파괴적 마이그레이션 테스트 가드 (안전)

- `tests/test_migrations.py` 는 `command.downgrade(cfg, "base")` 로 전 테이블을 드롭한다. `_resolved_test_db_url()` 이 `TEST_DATABASE_URL` 없이 `DATABASE_URL` 로 폴백하면 그 대상이 개발 DB 가 된다. **DSN 의 DB 이름이 `_test` 로 끝나지 않으면 `RuntimeError`.**

## 이연 (후속 BL)

- ② 거래소 exit(브래킷·트레일링·외부 수동)의 **머니-패스 계상** — 이번엔 원장 관측까지. 다음 스프린트가 이 원장 데이터를 근거로 결정한다.
- loss-limit 알림이 `live_signal_events.order_id` 조인이라 수동 청산·거래소 exit 을 못 본다.
- `cumulative_loss` 분자(전 기간 누적)/분모(현재 잔고) 시간축 불일치.
- `exchange_order_id` write 2경로의 `""`/`"None"` sanitize — unique index 도입의 선행 조건.
- `replay_orphan` 프로덕션 호출자 0.
- 세션 에쿼티 커브가 `(strategy, account)` 튜플 스코프.
- `Order.webhook_payload` 의 JSONB `'null'`.
- `get_daily_summary` 테넌트 스코프 부재.
- 원장 7일 한계 4종 + `list_unsynced_reduce_only` 의 `ASC LIMIT 500` head-of-line → [BL-452](../REFACTORING-BACKLOG.md#bl-452).

## 운영 레시피 (상속 + 신규)

- BE pytest = **3-env 전체**(`DATABASE_URL` + `TEST_DATABASE_URL` …5436/quantbridge_test + `TEST_REDIS_LOCK_URL` …6380/3). `backend/.env.local` 의 5433 은 stale.
- **★`TEST_DATABASE_URL` 없이 `DATABASE_URL` 만 export 한 셸에서 `tests/test_migrations.py` 를 돌리지 마라.** 이번 스프린트에서 실제로 로컬 개발 DB 가 전소했다(주문 17행 · 거래소 계정의 암호화 API 키 · 전략 6종). 이제 C-TESTDB-GUARD 가 막지만, 서브에이전트에 env 를 넘길 때는 항상 둘을 함께 준다.
- 신규 테이블 추가 시 `tests/test_migrations.py` 의 **스키마 완전 열거 센티널**(`test_trading_schema_round_trip`)을 함께 갱신한다. 현재 `trading` = **10 테이블**.
- **★적용된 마이그레이션 파일을 머지 전에 수정할 때** — 개발 DB 는 `alembic downgrade` 를 쓰지 말고 **차이나는 객체만 직접 DROP** 하고 `alembic_version` 을 유지한다(`alembic/env.py:40` 이 `settings.database_url` 을 주입하므로 수동 alembic 은 가드 없이 개발 DB 를 향한다 — BL-451 사고와 같은 형태). 마이그레이션 자체 검증은 `quantbridge_test` 에서 `pytest tests/test_migrations.py` 가 `downgrade base` → `upgrade head` 전 체인으로 수행하며 `_assert_disposable_database` 가드가 걸린다.
- **★`upgrade()` 에서 지운 테이블의 `DROP ... IF EXISTS` 는 `downgrade()` 에 남긴다.** 수정 전 리비전을 이미 적용한 DB 가 살아남은 테이블 때문에 `downgrade base` 에서 깨진다 — `20260416_2206` 의 평문 `drop_table('exchange_accounts')` 가 의존 FK 로 거부되고 안전망인 `DROP SCHEMA ... CASCADE` 는 그 뒤라 도달하지 못한다. `test_alembic_roundtrip` 이 `test_migrations.py` 의 첫 테스트라 파일 전체가 연쇄 실패하고 재실행으로도 안 낫는다. 실제로 이 줄이 `quantbridge_test` 의 stale 테이블을 자기치유하는 것을 확인했다.
- 로컬 `quantbridge_test` stale 시 `test_migrations.py` 가 유령 실패한다 — DB 재생성 후 재실행.
- worker/beat 재빌드 = `docker compose up -d --build --no-deps backend-worker backend-beat`.
- 독립 오라클 = `bybit_oracle.py`(asyncpg 로 `trading.exchange_accounts` 암호문 조회 → MultiFernet 복호화 → `api-demo.bybit.com` raw HMAC). **거래소 계정 행이 없으면 오라클도 못 돈다.**
