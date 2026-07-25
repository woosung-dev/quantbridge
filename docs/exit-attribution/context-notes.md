<!-- exit-attribution 의사결정·발견 기록 (append-only). 상속 체인 = perf-surface → position-cockpit → trading-surface-pack → close-completeness → money-path-accuracy → exit-attribution -->

# exit-attribution context-notes

> money-path-accuracy(#475) 후속. BL-438 부분. **마이그레이션 1건**(신규 테이블 2개).

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

## #8. 게이트

BE **2703 passed / 46 skipped / 0 failed**(baseline 2653, +50) · ruff·mypy clean · FE **1094 passed**(baseline 1088, +6) · tsc·lint clean · alembic 왕복 + head `20260725_0002` · 마이그레이션 **1**(신규 테이블 2개).
