<!-- exit-attribution 의사결정·발견 기록 (append-only). 상속 체인 = perf-surface → position-cockpit → trading-surface-pack → close-completeness → money-path-accuracy → exit-attribution -->

# exit-attribution context-notes

> money-path-accuracy(#475) 후속. BL-438 부분. **마이그레이션 1건**(신규 테이블 **1개**).
>
> **★#1~#8 은 축소 전 기록이다**(append-only — 지우지 않는다). 머지 전 범위 축소로 과거 전진 기계장치를 걷어낸 경위·실측·추가 발견은 **#9** 를 읽어라. #8 의 게이트 수치도 #9.6 이 대체한다.

## #1. §0.5 측정 스파이크가 핸드오프 전제를 뒤집었다

핸드오프는 "브래킷 TP/SL 청산 손익이 통째로 유실 중" 을 전제로 스코프를 짰다. 착수 첫 작업으로 독립 오라클(raw HMAC, 앱 미경유)로 계정 `0f666fae` 의 07-01~07-25 전량을 재고 나서 전제가 셋 다 무너졌다.

| 항목                           | 값                                   |
| ------------------------------ | ------------------------------------ |
| `/v5/position/closed-pnl` 전체 | 11 행                                |
| 우리 `exchange_order_id` 매칭  | 7 행                                 |
| **거래소에만 있는 행**         | **4 행 — 행 36.4% / \|손익\| 55.8%** |
| 거래소 확정 실현손익 합        | **−0.79748097**                      |
| 앱 머니-패스가 보는 합         | **−0.08297079 = 10.4%**              |

누락 89.6% 가 정확히 닫힌다 — 거래소 전용 행 **−0.44513721**(55.8%) + 07-05 시뮬 오차 **−0.26937297**(33.8%).

**반박 1 — 거래소 전용 4행은 브래킷이 아니다.** 전부 `createType=CreateByUser` · `stopOrderType` 없음 · **`orderLinkId` 없음** = 앱 밖에서 발주된 수동 reduce-only 청산.

**반박 2 — 브래킷 체결은 전 기간 0건.** 거래소 조건부 주문 4건(TP 66000 / SL 62000 / PartialTP / PartialSL)은 **전부 `Deactivated`**(미발화). 더구나 **DB 17행 중 `take_profit`/`stop_loss`/`trailing_stop` 을 실은 주문이 0건** — 앱이 브래킷을 부착한 적 자체가 없다. 경로(`live_signal.py:939-949` → `_merge_exit_params`)는 살아 있으므로 **잠복 구멍**이다.

**반박 3 — 거래소 전용 4행 중 우리 포지션은 1건뿐.** `avgEntryPrice` 대조상 62846.2 만 우리 진입 `7324c0b9` 와 일치하고 나머지 3건은 진입도 앱 밖이었다. "고아 = 전부 우리 것" 전제로 자동 계상하면 **남의 거래로 우리 전략을 차단**한다.

→ 스코프를 "브래킷 청산 계상" 에서 **"거래소 청산 사실을 원장으로 흡수 + 우리 주문만 계상"** 으로 재정의했다.

## #2. codex G0 = REJECT → 전건 코드 대조 후 절반 수용 / 절반 반박

**수용(맞음).** 소비처 5곳이 균질하지 않다 — `order_repository.py:90-102` → `alert_rules.py:62` loss-limit 알림만 `live_signal_events.order_id` 서브쿼리라 **합성 Order 만으로는 무반응**이다. "합성 행을 넣으면 5곳이 자동으로 정확해진다" 는 통념이 여기서 깨진다. `Order.strategy_id` NOT NULL FK 라 완전 외부 거래를 표현할 전략이 없다는 지적도 맞다.

**반박(틀림 — 실측).** "계정 단위 열거는 현 API 가 심볼을 요구해 불가" → ccxt `fetch_positions_history` 는 `symbols=None` 이면 `request['symbol']` 을 안 넣고 `filter_by_array` 도 통과시킨다(4.5.49 소스 + raw API 양쪽 확인). **심볼 없이 계정당 1콜로 전 심볼 열거가 실제로 된다.** 우리 래퍼만 심볼 필수였다.

## #3. 사용자 인터뷰 10건

D1 ①계상+②③관측 원장 · D2 별도 원장 테이블(합성 Order 금지) · D3 완전 외부 거래는 게이트 제외·알림만 · D4 마이그레이션 필요한 만큼 · D5 스윕을 7일 창 분할로 고쳐 영구 해결 · D6 전체 ExchangeAccount × 심볼리스 1콜 · D7 주문이력 보강 조회 함 · D8 과거 로컬 데이터는 A+B 삭제·C 는 백필로 정정 · D9 구조 결함 2건은 BL 등재만 · D10 소품 = BL-442 CSV + rejected 추정손익 정직성.

★D8 은 사용자가 "고아 행이 과거 DB 잔재라면 지워도 된다" 고 물으며 열린 축이다. 용어를 정정하고(고아 = 거래소 쪽 사실, 우리 테이블을 지워도 안 사라짐) 실제로 지울 가치가 있는 것을 실측으로 분리했다 — 손익값을 든 10행 중 **거래소 대응 주문이 없는 3행**(`f165f1c1` −1007.7 · `e7185d32` +42.5 E2E 시드 · `643d1651` +0.0087 rejected)이 대시보드 KPI 와 일일보고를 왜곡하는 주범이었다.

## #4. ★내 설계 결함 — 원장 min 파생 워터마크가 빈 창에서 영구 정지

Plan 압박검증이 잡았다. 나는 "진행 상태를 원장의 `min(exchange_created_at)` 에서 파생하면 워터마크 테이블이 불필요하다" 고 설계했는데, **청산이 한 건도 없던 과거 구간을 만나면 삽입이 0 이라 min 이 안 움직여 같은 빈 창을 영원히 재조회**한다.

실측 시각으로 시뮬레이션해 반증했다.

```
cycle 1: [07-18~07-25]:4행           원장=4행  min=07-24 11:40
cycle 2: [07-18~07-25]:0 [07-17~07-24]:0  원장=4행  min=07-24 11:40
cycle 3~6: 동일 (영구 정지)
최종 = 4/11,  07-05 행 = 0/7
```

**백필 대상 33.8% 전량에 영영 도달하지 못한다.** `trading.exchange_exit_sync_state` 워터마크로 전환하고 같은 시뮬레이션으로 재검증했다 — **2주기에 11/11 적재, 07-05 행 7/7 도달.**

직전 스프린트의 "마커 컬럼 없이는 스윕이 종료 조건을 못 가진다" 와 **같은 구조의 결함이 한 층 위에서 재발**한 것이다. 원장은 *행이 존재한 사실*만 영속하지 *스캔한 사실*은 영속하지 못한다.

## #5. 생성/평가 분리가 또 값을 했다 — 평가자 4기가 BLOCKING 4 + MAJOR 4

워커 4기(provider / 원장 / 스윕 / FE)는 전부 "게이트 통과" 라 보고했으나 평가자 3기가 FAIL 을 냈다.

- **BLOCKING — 기존 회귀 테스트 4건이 red.** HEAD 에서 green 이던 `test_provider_fetch_closed_pnl.py` 가 빨갛다. 픽스처가 에포크 근처/절대 시각 고정이라 7일 클램프와 충돌했다. 그중 3건은 직전 스프린트가 프로덕션 파손을 잡았던 머니패스 가드다. → 픽스처를 상대 시각으로 고쳐 시간 의존성을 함께 제거.
- **BLOCKING — 신규 테이블이 스키마 완전 열거 센티널을 깼다**(`test_trading_schema_round_trip`).
- **BLOCKING — `fetch_closed_order_meta` 페이징이 축을 섞었다.** 커서는 `updatedTime`, 서버 필터는 `createdTime`. `updatedTime ≥ createdTime` 이라 커서가 **앞으로 가** 창이 7일을 넘고(`retCode 10001`) 같은 페이지를 `max_pages` 만큼 헛돈다. 며칠 열려 있다 체결되는 브래킷 주문이 정확히 이 스프린트가 겨냥하는 케이스다.
- **MAJOR — 기존 필드까지 fail-loud 를 삼킴으로 강등.** `closedSize`/`avgExitPrice`/`updatedTime` 파싱 실패가 `None` 이 되면서 행이 살아남아 `malformed_row` 관측치가 사라지고, 분할 청산에서 `closed_size` 만 과소 합산돼 **손익과 수량이 모순된 원장 행**이 CAS 로 고정된다. 직전 스프린트의 `_decimal_or_none` 공용화 회귀(§7.3)와 같은 부류다.
- **MAJOR — `list_filled_for_attribution` 이 ASC LIMIT.** 오래된 500건만 줘서 최근 청산의 진입이 표본 밖으로 밀리고 순포지션 가드가 절단 부산물이 된다.
- **MAJOR — 원장 계약이 순환 검증.** 테스트가 전부 mock 이라 UNIQUE·Decimal·NOT NULL·워터마크 단조성 중 어느 것도 실제로 지켜지지 않았다. → 실 DB 통합 테스트 7건 추가.

**★내가 넣은 회귀 1건도 평가자가 잡았다.** `compute_row_hash` 를 구분자 하드닝하면서 `None` 과 `""` 를 다르게 만들었다. 거래소가 한 주기엔 빈 문자열을, 다른 주기엔 키를 생략하면 같은 행이 두 해시로 갈려 UNIQUE 를 통과하고 **`realized_pnl` 이 실제의 2배로 백필**된다. 회귀 테스트와 함께 되돌렸다.

**반박한 것.** "합산 스냅샷의 `raw` 가 원장에 영속된다" → `aggregate_closed_pnl_by_order` 는 `providers.py:1149` 단건 refresh 경로에서만 쓰이고 스윕은 행 단위 스냅샷을 적재한다. 원장에 도달하지 않는다(docstring 경고만 추가).

## #5.5. 최종 codex 누적 diff = DO-NOT-SHIP — 여기서 또 2건이 더 나왔다

생략하면 안 되는 단계라는 것이 이번에도 확인됐다. 평가자 4기를 다 통과한 뒤에도 머니-패스 완전성 결함 2건이 남아 있었다.

- **DO-NOT-SHIP — 체결 직후 refresh 가 원장을 우회한다.** `_refresh_closed_pnl_with_session` 은 원장이 아니라 **단일 조회 결과**를 CAS 한다. 분할 행 `-0.02`/`-0.03` 중 t+5s 에 첫 행만 보이면 `-0.02` 가 `synced_at` 과 함께 확정되고, 미동기화 술어를 쓰는 스윕은 그 주문을 **영영 건너뛴다**. C-SWEEP-V2 의 "원장 전체 집계 후 CAS" 가 이 경로에서만 깨져 있었다. → `resync_exchange_realized_pnl`(값이 다를 때만 UPDATE, 같으면 rowcount 0 = 멱등) + 스윕의 synced 주문 대조 경로 신설.
- **DO-NOT-SHIP — `max_pages` 소진을 성공으로 취급했다.** 7일 창에 501행 이상 있으면 가장 오래된 행을 못 읽는데 워터마크는 **창 시작까지 전진**해 그 구간을 다시 보지 않는다. 원장에 영구 구멍이 생긴다. → `ClosedPnlWindow(rows, truncated)` 로 잘림을 알리고, 잘린 창에서는 **실제로 읽은 가장 오래된 행까지만** 경계를 전진시킨다(한 주기에 최소 `max_pages` 만큼 전진하므로 진행은 보장).
- **MAJOR — 시각을 못 만든 행이 로그만 남기고 사라졌다.** `malformed_row` 로 표면화.
- **MINOR — downgrade 의 인덱스 drop 이 무조건 실행.** `DROP INDEX IF EXISTS` 로 통일.

네 건 모두 회귀 테스트를 붙였다.

## #6. ★사고 — 로컬 개발 DB 전소

W1b 적대 평가자에게 alembic 왕복 실측을 지시하며 `export DATABASE_URL=<개발 DB>` 를 줬고, 평가자가 **같은 셸에서 `pytest tests/test_migrations.py` 를 돌렸다.** `_resolved_test_db_url()` 이 `TEST_DATABASE_URL` 없이 `DATABASE_URL` 로 폴백하고 `test_alembic_roundtrip` 이 `command.downgrade(cfg, "base")` 를 실행해 **개발 DB 의 전 테이블이 드롭·재생성**됐다.

- **잃은 것** — 주문 17행 · 거래소 계정 1(암호화된 Bybit demo API 키) · 전략 6종의 Pine 소스 · 세션 4 · 이벤트 10 · 백테스트. `.env.local` 에 평문 키 없음.
- **살아남은 것** — `trading.orders` 17행 SQL 스냅샷(A+B 삭제 대비로 미리 떠둠). 단 부모 행이 없어 단독 복원 불가.
- **원인은 내 지시** — 서브에이전트에 env 를 넘길 때 `TEST_DATABASE_URL` 을 함께 주지 않았다.
- **재발 방지** — `_assert_disposable_database` 가 DSN 의 DB 이름이 `_test` 로 끝나지 않으면 `RuntimeError`. 실제로 개발 DB DSN 으로 돌려 파괴 대신 예외가 나는 것을 실증했다.

사용자 확정 = 거래소 계정을 재등록하고 **새 데이터로 dogfood**. 그 결과 우리 주문 이력이 없어 **모든 closed-pnl 행이 미귀속으로 분류**되므로 분류·알림·멱등·창 전진은 검증 가능하지만 **백필(33.8%) 종단 검증은 이번 스프린트에서 불가**하다(정직 각주).

## #7. ★함정 (상속 + 신규)

- **상속**: BE pytest 3-env(`.env.local` 의 5433 은 stale) / `ruff format` 은 게이트 아님 / docker 포트 오버레이 `--no-deps` / DB 스키마 prefix / 3000=nexus·3100=QuantBridge·8100·5436·6380 / em-dash 래칫 / authed spec testMatch 열거식 / QB_PRE_PUSH_BYPASS=1 / codex 샌드박스가 5436 차단 / codex 워커 prettier.
- **★파괴적 테스트의 env 폴백** — `tests/test_migrations.py` 는 `downgrade base` 를 돌린다. 서브에이전트든 사람이든 이 파일을 돌리는 셸에는 반드시 `TEST_DATABASE_URL` 을 함께 준다(#6).
- **★신규 테이블 = 스키마 완전 열거 센티널 갱신 의무.** `test_trading_schema_round_trip` 이 `trading` 테이블 집합을 리터럴로 고정한다.
- **★페이징 커서 축 = 서버 필터 축.** Bybit `startTime/endTime` 과 ccxt `filter_by_since_limit` 은 `createdTime` 기준이다. `updatedTime` 으로 당기면 커서가 앞으로 간다. 직전 스프린트가 같은 축 불일치로 프로덕션 파손 1건을 겪었고, 창을 나누면 그때의 미봉책(`_CLOSED_PNL_LOOKBACK_MS`)이 안 통한다.
- **★ccxt `fetch_orders` 는 UTA 에서 `NotSupported`.** 주문 이력은 `fetch_closed_orders`.
- **★ccxt 가 closed-pnl 행의 `side` 를 뒤집는다**(`isHistory` 분기, `Buy→short`). 방향은 raw `info.side`.
- **★해시 구분자는 제어문자 + 결측 정규화.** 인쇄 가능한 구분자는 필드 경계를 옮기고, `None`/`""` 를 다르게 보면 같은 행이 두 번 적재돼 손익이 2배가 된다.
- **★`postgresql.JSONB(none_as_null=True)`** — 지정하지 않으면 Python `None` 이 SQL NULL 이 아니라 JSONB `'null'` 로 저장돼 `IS NULL` 술어가 무력해진다(`Order.webhook_payload` 실측 15/17행).
- **★alembic 마이그레이션을 적용 후에 수정하면 downgrade 가 깨진다.** 이미 적용된 환경에서 나중에 추가한 테이블을 drop 하려다 실패한다 — `DROP TABLE IF EXISTS` 로 쓴다.

## #8. 게이트 (축소 전 — 현재 수치는 #9.6)

BE **2710 passed / 46 skipped / 0 failed**(baseline 2653, +57) · ruff·mypy clean · FE **1094 passed**(baseline 1088, +6) · tsc·lint clean · alembic 왕복 + head `20260725_0002` · 마이그레이션 **1**(신규 테이블 2개).

---

## #9. ★범위 축소 — 사용자가 옳았다 (2026-07-25, 같은 브랜치·머지 전)

#1 의 측정이 전제를 뒤집었는데 **뒤집힌 결과를 스코프에 충분히 반영하지 못했다.** 브래킷 체결 0건 · 거래소 전용 4행 중 우리 것 1건뿐 · 나머지는 이전 세션 dogfood 오라클이 만든 앱 밖 거래였는데도, 과거 90일을 훑는 기계장치(워터마크 테이블 · 창 전진 · 잘림 처리)를 만들었다. 그걸 만든 직접적 이유였던 "20일 전 미동기화 4건 회수" 는 #6 의 DB 전소로 사라졌다.

**사용자 판정 = 줄인다.** 원장 + 최근 7일 창만 남긴다.

### #9.1 실측 반전 — 과거 전진은 애초에 "일회성" 이었다

축소를 "커버리지 90일 → 7일 축소" 로 이해하고 있었는데, 코드를 다시 재면 그게 아니었다.

`_closed_pnl_windows` 의 `horizon_ms` 는 **매 주기 `now` 에서 재계산**되고 `backfilled_from` 은 **과거로만** 전진한다. beat 주기는 300초(`celery_app.py:138`)이므로 워터마크는 주기당 7일 후퇴하고 horizon 은 5분 전진한다. **~13주기(약 65분) 후 `end_ms <= horizon_ms` 가 영구 latch** 되고, 워터마크가 DB 영속이라 프로세스 재시작으로도 풀리지 않는다.

→ **정상 상태에서 축소 전후 동작은 동일하다.** 없어지는 것은 일회성 90일 역사 수입 하나다. 그래서 BL-452 제목도 "90일 커버리지 복원" 이 아니라 **"일회성 과거 catch-up 재도입"** 으로 적었다 — 다음 세션이 상시 기제를 재설계하지 않도록.

### #9.2 축소가 드러낸 결함 2건 (함께 고침)

- **★커밋 누락을 탐지할 테스트가 없었다.** 제거 대상 블록이 `upsert_rows` 와 `await session.commit()` **사이**에 있어 커밋을 함께 지우기 쉬운데, 페이크 세션이 `session.commit = AsyncMock()` 이고 아무도 assert 하지 않아(파일 전체에서 `commit` 문자열 1회) **어떤 테스트도 실패하지 않았다.** 커밋이 없으면 `summary["inserted"]` 는 N 을 보고하는데 알림·백필은 새 세션으로 되읽어 빈 원장을 본다 = 조용한 무동작. → 페이크를 **트랜잭션처럼** 만들었다(upsert 는 staging, commit 이 원장으로 이동). 커밋을 지우면 **3건이 red** 가 되는 것을 실증했다(이전엔 0건).
- **★마이그레이션 downgrade 가 깨질 뻔했다.** 워터마크 `create_table` 을 지우면서 downgrade 의 `DROP TABLE IF EXISTS` 도 함께 지우는 것이 자연스러워 보이지만, 그러면 **수정 전 리비전을 이미 적용한 DB**(내 로컬 dev·`quantbridge_test`)에서 테이블이 살아남아 `downgrade base` 가 `20260416_2206` 의 평문 `drop_table('exchange_accounts')` 에서 의존 FK 로 거부된다. 안전망 `DROP SCHEMA ... CASCADE` 는 그 뒤 줄이라 도달하지 못한다. `test_alembic_roundtrip` 이 `test_migrations.py` 의 **첫 테스트**여서 파일 전체가 연쇄 실패하고 재실행으로도 안 낫는다. → **drop 줄을 의도적으로 남기고 왜 남기는지 주석**을 붙였다. `quantbridge_test` 의 stale 테이블이 실제로 자기치유되는 것을 확인했다(10 테이블).

### #9.3 절차 이탈 1건 (사용자 승인)

핸드오프 §8 은 "개발 DB `alembic downgrade -1` → 파일 수정 → `upgrade head`" 를 지시했으나, `alembic/env.py:40` 이 `settings.database_url` 을 주입하므로 **수동 alembic 은 가드 없이 개발 DB 를 향한다** — #6 사고와 같은 형태의 명령이고, 개발 DB 는 사용자가 거래소 계정을 재등록할 곳이다. 사용자 승인으로 **개발 DB 는 `DROP TABLE trading.exchange_exit_sync_state` 한 줄**(alembic_version 은 `20260725_0002` 유지 → 수정된 `upgrade()` 산출 스키마와 비트 동일)로 처리하고, 마이그레이션 검증은 가드가 걸리는 `quantbridge_test` 의 `test_migrations.py` 에 맡겼다. 드롭 전 실측 = sync_state 0행 · 원장 0행 · 계정 0 · 주문 0(전소 확인).

### #9.4 다른 판단 3건

- **`created_at_bounds` 제거** — 이 브랜치가 만든 자기 고아(프로덕션 호출자 0)이고 docstring 이 **기각된 min-파생 설계**를 문서화하고 있었다. 남기면 다음 세션이 오독한다. 실 DB 통합 테스트 7건 → 5건.
- **`summary["windows"]` 제거** — 계정당 창이 항상 1이면 "commit 에 도달한 계정 수" 의 중복이고 이름이 오독을 부른다. 프로덕션 소비자 0.
- **`list_unsynced_reduce_only` 의 `ASC LIMIT 500` 은 등재만**(사용자 확정). 7일 밖 청산은 원장에 못 들어와 영구 좀비가 되고 ASC 라 앞줄을 차지하지만, #9.1 대로 축소 전에도 위험이 동일했고 1인 로컬 앱에서 좀비 500건은 멀다. → BL-452.

### #9.5 ★최종 codex 누적 diff 가 또 P1 을 잡았다 (이 단계 생략 금지의 3번째 근거)

축소가 본론이었는데, 누적 diff 리뷰가 **축소와 무관한 머니-패스 P1** 을 하나 더 찾았다. 전건 코드 대조로 확인했다.

**동일 `createdTime` tie 행이 페이지 경계에서 조용히 사라진다.** `fetch_closed_pnl_window` 의 커서가 `until = oldest_ms - 1` 이었다. 한 청산 주문의 분할 행은 **createdTime 을 공유**할 수 있고(구분은 `updatedTime` — 그래서 `row_hash` 가 둘 다 넣는다), 같은 밀리초의 행이 페이지 상한(100)을 넘으면 커서가 그 밀리초 **아래로** 내려가 남은 tie 행을 다시 조회할 방법이 없어진다. 게다가 다음 페이지가 짧으면 `truncated = False` 로 **완전 조회라고 보고**한다 — 500행 상한에 걸리지도 않았는데 잘림 신호조차 없다. 누락 행이 우리 주문의 분할이면 `aggregate_closed_pnl` 이 부분합을 돌려주고 **틀린 `realized_pnl` 이 CAS 로 영구 고정**된다. 기존 커서 테스트는 서로 다른 createdTime 만 써서 이 경우를 통과시켰다.

**수정 = 경계를 포함해 다시 읽는다**(`until = oldest_ms`). Bybit 은 tie-breaker 커서를 주지 않으므로 이게 유일한 무손실 방법이고, 겹쳐 읽힌 중복은 **원장 `UNIQUE(exchange_account_id, row_hash)` 가 흡수**하므로 이중 합산이 없다(스윕의 `new_hash_set.remove()` 도 중복 행을 두 번 계상하지 않게 이미 설계돼 있었다). 꽉 찬 페이지에서 커서가 더 못 가면 이제 **완전 조회를 주장하지 않는다** — 완전 조회의 유일한 증거는 상한 미만 페이지다. 회귀 테스트를 붙이고 **구 커서로 되돌리면 red 가 되는 것을 실증**했다.

**같은 패턴이 `fetch_closed_order_meta`(`providers.py:1410`)에도 있으나 고치지 않았다** — 분류 라벨 전용이고 `setdefault` 라 재조회가 멱등하다. tie 누락의 결과는 일부 행이 `unknown` 으로 분류되는 것뿐이며 머니-패스에 들어가지 않는다. BL-452 에 적었다.

### #9.6 신규 함정

- **★caplog 은 전체 스위트에서 격리가 깨진다.** 잘림 경고 검증을 `caplog` 로 썼더니 **파일 단독 실행은 통과(608 passed)하는데 전체 스위트에서 `caplog.records` 가 비어 실패**했다. `propagate=False` 를 세팅하는 코드는 레포에 없어 원인 모듈은 특정하지 못했다. 이 레포의 기존 교훈대로 **logger mock**(`monkeypatch.setattr(providers_mod.logger, "warning", mock)`)으로 전환해 전역 logging 상태 의존을 제거했다. 발화 지점을 직접 관찰하므로 순서 의존이 없다.
- ruff `RUF003` — 주석의 `×`(MULTIPLICATION SIGN)가 걸린다. `*` 로 쓴다.

### #9.7 축소 후 게이트

BE **2706 passed / 46 skipped / 0 failed**(축소 전 2710). 감소분의 내역 = 워터마크·창 전진 테스트 **6건 삭제**(`_closed_pnl_windows` 2 · 과거 창 재시도 1 · 잘린 창 경계 1 · `backfilled_from` 단조성 1 · `created_at_bounds` 1) + **2건 신설**(계정당 창이 정확히 1개이고 `[now−7d, now]` 인지 · #9.3.5 의 createdTime tie 누락 회귀). 회귀가 아니다. ruff·mypy clean · alembic base→head 왕복 + 스키마 10 테이블 센티널 green · 마이그레이션 **1**(신규 테이블 **1개**) · **FE 미변경**(1094 불변, tsc·lint clean).

### #9.8 축소 후 라이브 검증 — 계정 없이도 되는 것은 다 했다

거래소 계정 재등록 전이라 원장 적재·분류·백필 dogfood 는 못 하지만, **계정에 의존하지 않는 항목은 전부 실측했다.**

- **★§7.2 sentinel 이 실제로 stale 워커를 잡았다.** 재빌드 전 워커는 `_closed_pnl_windows` · `_EXIT_LEDGER_HORIZON_DAYS` · `ExchangeExitSyncState` 를 아직 갖고 있으면서 `ClosedPnlWindow` 는 **없었다** — 이미지가 정확히 `78ceadd` 시점에 baked 됐다는 뜻이다(`ClosedPnlWindow` 는 다음 커밋 `2ad3b11` 에서 추가됐다). 재빌드(`docker compose up -d --build --no-deps backend-worker backend-beat`) 후 4종 전부 부재 + 단일 창 인라인 + `log_context` 전달 확인. **워커가 조용히 구 코드를 돌리는 위험이 문서상 가정이 아니라 이 세션의 실제 상태였다.**
- **§9.5 라이브(운영 계약)** — 같은 child(`ForkPoolWorker-2`)에서 스윕 **4회 연속 성공**(수동 3 + **beat 자체 발화 1**, `sweep-closed-pnl-backfill` 300s). 라이브 반환 shape 이 `{'accounts','inserted','backfilled','resynced','alerted'}` 로 나와 **`windows` 키 부재를 실환경에서 확인**했다(테스트 기대값 ↔ 프로덕션 동작 일치).
- **canon 32 passed** · **FE 1094 passed**(tsc·lint clean).
- **authed 58 passed / 1 skipped / 6 failed** — 6건은 전부 **채워진 표를 단정하는 데이터 의존** 스펙(`/strategies/:id/edit` · `/optimizer/:id` · `/backtests/:id` · `/backtests` 11열 · 전략목록 `backtest_count` · 전략목록 11+ items)이고 개발 DB 는 `strategies 0 · backtests 0 · orders 0` 이다. 실패 메시지도 populated-table locator 의 `element(s) not found`. 축소 diff 가 `frontend/`·router·service 를 **한 파일도 건드리지 않았고** `/orders` 계열은 **5/5 green**(A2 취소 2 · B2 배지 · kill-switch disabled)이라 인과가 없다.
  - **정직 고지** — 이 브랜치에는 **authed 녹색 baseline 이 없다**(원 스프린트가 authed 를 dogfood 로 이연했다). 따라서 "이전에도 빨갰다"를 기록으로 증명할 수는 없고, 무인과는 **diff 범위 + 실패 양태**로 판정했다. 데이터 복원 후 재실행이 남은 확인이다.
- **★3000 은 nexus-core, 3100 이 QuantBridge** 를 title 프로브로 재확인하고 `PLAYWRIGHT_BASE_URL=http://localhost:3100` 으로 돌렸다.

## #9.9 ★사용자 계정 재등록 후 dogfood 완주 — 또 P1 을 잡았다

사용자가 Bybit demo 계정을 재등록(`19a8166a-...`)해 §6 dogfood 를 완주했다.

**독립 오라클 실측** — 앱 provider 코드를 전혀 거치지 않고 `asyncpg` 로 `trading.exchange_accounts` 암호문을 직접 읽어 `MultiFernet` 복호화 후 `api-demo.bybit.com` 에 raw HMAC 서명 요청을 보냈다(`/v5/position/closed-pnl`, 최근 7일). 결과 = **4행, 합계 −0.12392537**. 스윕 1회 실행 후 원장도 **4행, 합계 −0.12392537** — 완전 일치. 분류는 4행 중 3행이 `orderLinkId` 가 우리 앱 관례(`Order.id` UUID4)와 형식이 일치해 `ours`(이 판정은 `orders` 테이블 존재 여부와 무관 — orderLinkId 형식만으로 성립하는 별도 경로), 나머지 1행은 `orderLinkId` 없음 + `createType=CreateByUser` → `external_manual`. **이 4행은 DB 전소 이전에 이 앱이 직접 발주했던 흔적**이라는 뜻이다(3/4가 우리 관례의 orderLinkId 를 달고 있다) — 다만 원 주문 행 자체는 사라졌으므로 `attribution_confidence` 는 전부 `none`, 백필 종단 검증은 여전히 불가하다.

**★알림이 죽어 있었다 — 진짜 P1.** 1회차 스윕에서 `alerted:0`(기대 1)이 나왔다. 조사 결과 `_alert_new_exchange_exits`(`tasks/trading.py`)는 `list_by_row_hashes` 로 **새 세션에서 원장을 재조회**하는데, `ExchangeExit.classification` 컬럼이 평문 `String(24)`(Sprint 26 의 `UndefinedObjectError` 회피 워크어라운드, `models.py:438-440` 주석)라 SQLAlchemy 가 재수화할 때 `ExitClassification` StrEnum 이 아니라 **plain str** 을 그대로 준다. 방금 만든 메모리 객체일 때만 진짜 enum 이다. `Counter(row.classification.value for row in external_rows)` 의 `.value` 접근이 plain str 에는 없어 `AttributeError` 를 던지고, 함수 전체를 감싼 `except Exception:` 이 그걸 삼켜 **신규 미귀속 행 알림이 매 사이클 조용히 죽고 있었다** — 로그에는 `exchange_exit_alert_failed` 만 남고 원인은 별도 확인 전엔 안 보인다.

이 경로가 이번 세션 전엔 실 DB 라운드트립으로 exercise 된 적이 없었다 — 유닛테스트는 fake repo(이미 enum 인스턴스)를 썼고, 원 스프린트의 dogfood 는 DB 전소로 여기 도달하기 전에 끊겼다. **dogfood 가 정확히 이런 걸 잡으라고 있는 것**이다.

**수정** — `str(row.classification)` 로 교체(`StrEnum.__str__` 은 값 자체를 돌려주므로 reload 된 plain str 과 메모리상 enum 인스턴스 양쪽에 안전). 회귀 테스트는 실 DB 에 커밋 후 `session.expire_all()` 로 강제 재조회시켜 SQLAlchemy 의 실제 hydration 경로를 태운다(fake 로는 재현 불가) — 구 코드로 되돌리면 정확히 이 `AttributeError` 로 red 가 되는 것을 확인했다. ★테스트 작성 중 부수 함정 1건 — `expire_all()` 뒤에 `row.row_hash`/`account.id` 를 **동기 접근**하면 SQLAlchemy 가 그 자리에서 강제 재조회를 시도해 `MissingGreenlet` 이 뜬다. 넘길 값은 expire 전에 미리 로컬 변수로 꺼내둬야 한다.

**감사 — 같은 패턴이 다른 곳에도 있는가.** `StrEnum` 타입인데 평문 `String` 컬럼인 필드가 5개 더 있다(`LiveSignalSession.interval` · `LiveSignalEvent.status` · `AlertRule.rule_type`/`channel` · `ExchangeExit.attribution_confidence`) — 전부 Sprint 26 의 동일 워크어라운드다. 호출부 전수 조사 결과 **실제 크래시 사이트는 이 한 곳뿐**이었다(나머지는 `==`/`!=`/`str()` 만 쓰거나 호출부 자체가 없음, `StrEnum` 이 `str` 서브클래스라 비교 연산은 reload 여부와 무관하게 안전). → 재발 방지를 위한 최소 등재 [BL-453](../../../backlog.md#bl-453).

**재검증** — 알림 fix 적용 + 워커 재빌드 → 원장 TRUNCATE(거래소에서 7일 안에 언제든 재조회 가능한 관측 캐시라 안전) → 재스윕 → **`alerted:1`**, `exchange_exit_alert_failed` 로그 0건. 2회차 재스윕 → `inserted:0`·`alerted:0`(멱등 확인). 최종 상태 = 활성 세션 0 · 미체결 주문 0 · 계정 1(사용자 등록분 보존) · 원장 4행 · 포트 보존.

### #9.10 축소+dogfood 최종 게이트

BE **2707 passed**(축소 2706 + 알림 회귀 테스트 1) / ruff·mypy clean. push `325e5f3`.
