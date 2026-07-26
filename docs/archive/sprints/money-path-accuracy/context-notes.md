<!-- money-path-accuracy 의사결정·발견 기록 (append-only). 상속 체인 = opspack-ws2 → perf-surface → position-cockpit → trading-surface-pack → close-completeness → money-path-accuracy -->

# money-path-accuracy context-notes

> close-completeness(#474) 후속. BL-014(부분) 거래소 확정 손익 + BL-362 텔레그램 팬아웃. **마이그레이션 1건**(핸드오프의 "0" 을 설계 충돌로 대체).

## #1. 착수 시점 프레임 교정 — "부분체결 추적" 이 아니라 "손익이 시뮬레이션"

핸드오프는 BL-014 를 "부분체결 `cumExecQty` 추적"으로 프레이밍했지만, grounding 결과 진짜 리스크는 다른 곳이었다.

- `Order.realized_pnl` 은 **close 주문 생성 시점**(state=`pending`)에 pine_v2 가 계산한 값으로 기록되고 **체결 후 한 번도 보정되지 않는다**(`transition_to_filled` 의 4 호출자 전원이 인자를 안 넘김).
- 그 값은 gross 정도가 아니라 **순수 시뮬레이션**이다 — `(sim_exit − sim_entry) × 진입 전량 × sign`, 수수료 0 명시(`strategy_state.py:551-552`), 바 종가, 실제 체결가·수량 무시. `run_historical` 에는 commission 파라미터 자체가 없다.
- 이 숫자를 **머니-패스 5곳이 SSOT 로 소비**한다(Kill Switch 2 · 에쿼티 커브 · loss-limit 알림 · 일일 보고). 즉 리스크 게이트가 시뮬레이션으로 돌고 있었다.
- **실발견:** `close_service.py:78` 의 수동 청산(#473 로 넣은 청산 버튼)은 `realized_pnl` 을 아예 안 실어 **NULL** 로 저장됐다 → 5곳 **전부에서 안 보임**. DB 실측으로 07-24 수동 청산 3건이 전부 NULL 인 것을 확인했다.

`filled_quantity` 는 부차적 문제였다 — write 는 watchdog 1곳뿐이고 read 사이트 0(완전 dead), 게다가 `transition_to_filled` 의 무조건 write 때문에 나머지 3 경로는 **오히려 NULL 로 덮고** 있었다.

## #2. codex G0 = REJECT → §7.3 전건 코드 대조 후 절반만 수용

**수용(맞음).**

- repository 안에 거래소 호출 금지 → 4 winner 공용 post-fill helper 가 정답. `_enqueue_trailing_if_intended` 가 이미 그 패턴으로 4곳 전부 배선돼 있어 그대로 미러.
- "거부되면 Kill Switch 오계상" 은 **틀린 전제** — rejected 는 `state==filled` 필터로 이미 제외된다. 핸드오프의 "MDD" 표현도 실체 없음(`cumulative_loss`/`daily_loss` 뿐).
- 병행 저장할 JSONB 없음 — `dispatch_snapshot` 은 provider 라우팅 계약, `webhook_payload` 는 책임 불일치.
- `run_live_error` 의 raw 예외 문자열은 **의도적 Slack-only 경계**(`live_signal.py:512-517`). 무조건 both 로 바꾸면 미감사 텍스트가 텔레그램에 샌다.

**반박(틀림 — 실측).**

- BLOCKING "부분체결→취소면 hook 이 놓친다" → 이 레포 청산은 **전부 `OrderType.market`**(`live_signal.py:925`, `close_service.py:83`). Bybit 시장가 부분체결 = `PartiallyFilledCanceled` → ccxt `parse_order_status` 가 **`closed`** → 우리 `_map_ccxt_status` 가 **`filled`**. 즉 부분체결 청산도 `filled` 에 도달해 옵션 A 가 정확히 커버한다. 잔여는 "limit 청산"뿐인데 그 경로는 존재하지 않는다.
- "BL-362 는 이미 Resolved 기록" → **오독**. 백로그 BL-362 항목엔 상태 라인 자체가 없다(codex 가 BL-374 의 출처 줄을 읽음).

## #3. 계획 중 실발견 2건 (핸드오프·codex 모두 놓침)

### 3.1 거래소 네이티브 TP/SL 청산은 DB 에 아무 행도 안 남긴다 (후속 BL)

브래킷 TP 가 체결되면 — WS `order` 고아 이벤트는 5초 버퍼 후 폐기(`state_handler.py:97-102`, `logger.debug` 만, 알림 없음) · `execution` 토픽 미구독 · reconciler 는 local→exchange 단방향이라 INSERT 없음 · Order INSERT 지점은 `OrderService.execute` 2곳뿐. 그 다음 바에서 pine 이 **같은 청산을 스스로 추측**해 이미 flat 인 포지션에 reduce-only close 를 쏘고 → `ProviderError` → `state=rejected` → 모든 손익 쿼리가 `state==filled` 로 걸러낸다. **브래킷 익절 손익이 통째로 유실 중이다.**

사용자 확정 = 후속 BL 등재만. 단 스윕이 closed-pnl 페이지를 어차피 읽으므로 매칭 안 되는 행을 `orphan_row` 로 **계상만** 하게 했다.

★**자체 정정(마감 직전 발견).** 이 카운터는 구멍 크기를 **측정하지 못한다.** 스윕 후보가 `list_unsynced_reduce_only_since()` = _우리_ 미동기화 주문이라, 백필이 정상 동작하는 steady state 에선 후보가 0 → 페이지를 아예 안 가져와 orphan 이 영영 0 이다(dogfood 에서 `groups=0` 실측). 하한선으로만 유효하며, 실측하려면 활성 계정·심볼을 독립 열거하는 조회가 선행돼야 한다. BL-438 의 첫 step 을 그 측정 스파이크로 잡았다.

### 3.2 마커 컬럼 없이는 스윕이 종료 조건을 못 갖는다 (마이그레이션 0 → 1)

overwrite 만으로는 `realized_pnl` 한 컬럼에 시뮬값과 확정값이 **구분 없이** 섞인다 → 스윕에 "미동기화" 술어가 없어 윈도우 안 전 주문을 5분마다 영구 재조회하고, `never_found` 로 시뮬값이 남은 행을 쿼리로도 화면으로도 식별할 수 없다. 사용자 확정 = **`realized_pnl_synced_at` 1컬럼 추가**(nullable, 백필 없음). 스윕 술어 + 멱등 CAS + 행별 출처 + staleness 를 한 번에 해결.

## #4. 사용자 인터뷰 11건 (2 라운드 + 1 보강)

D1 `filled` 도달 전량 커버(시장가 부분체결 포함) · D2 `realized_pnl` 전면 overwrite · D3 전용 Celery task + 4 winner helper · D4 raw 제거 후 전 경로 both · D5 네이티브 exit 은 후속 BL 등재만 · D6 filled_quantity 4경로+관측성+API · D7 보정 스윕 포함 · D8 전량 청산 종단 + 픽스쳐 부분체결 · D9 마이그레이션 1건 허용 · D10 orphan 카운터 포함 · D11 OrderResponse 에 realized_pnl 도 노출.

## #5. 생성/평가 분리가 실제로 값을 했다 — 평가자가 프로덕션 파손 2건 발견

codex 워커 2기(be 2-pass / fe) 자기보고는 전부 "통과" 였으나, **BE 는 인도 시점 FAIL** 이었다.

- **MAJOR — `since` 창이 대상 행을 조용히 버렸다.** `fetch_closed_pnl_page` 가 `since = filled_at − 120초` 를 썼는데, ccxt `fetch_positions_history` 는 마지막에 `filter_by_since_limit` 를 태우고 `parse_position` 의 `timestamp` 는 **`createdTime`(거래소 청산주문 생성시각)** 이다. 우리 `filled_at` 은 *우리가 체결을 감지한 시각*이라, reconciler(300초 주기)나 늦은 watchdog 경로에선 창이 행보다 뒤에 놓여 ccxt 가 **클라이언트 측에서 행을 버린다**. 결과 = `None` → 재시도 4회 전부 같은 잘못된 창 → 영구 `never_found` + **거짓** critical alert + 시뮬값 영구 잔존. 오프라인 재현: 감지 지연 0/60/119초 → 1행, **121/300/600초 → 0행**. → `_CLOSED_PNL_LOOKBACK_MS = 3_600_000` + 반증 테스트.
- **MAJOR — malformed 행 폭발 반경.** 행 파서가 `ProviderError` 를 던지고 페이지를 리스트 컴프리헨션으로 파싱해, 한 행만 깨져도 페이지 전체가 죽었다. 스윕에선 해당 `(account, symbol)` 그룹이 **알림 없이 5분마다 영구 실패**한다. → skip + `malformed_row` 계상.
- BLOCKING — 스프린트가 쓴 잘못된 단언 2건(`DailyLossEvaluator` 는 **부호 있는** 합을 반환 / `Numeric(18,8)` 은 `"0.00500000"` 으로 직렬화).

## #6. 평가 후 내가 추가로 고친 4건

- **§7.3 Surface Trust 회귀 — `_decimal_or_none` 공용화가 의미를 바꿨다.** 원래 `fetch_open_positions` / `fetch_open_conditional_orders` 의 클로저는 파싱 실패 시 **예외를 던져** `ProviderError` 로 fail-loud 했는데, 공용 헬퍼가 `None` 을 돌려주게 되면서 파싱 불가한 손절가가 코크핏에 **"손절 없음(—)"** 으로 조용히 렌더될 수 있었다. 사용자가 무방비라 오판하고 수동 개입할 수 있는 false negative. → `strict=True` 파라미터로 원래 의미 복원 + 회귀 테스트 2건(positions / conditional-orders).
- 백필 실패 알림이 Slack 전용이었다 — 같은 스프린트가 발산 알림을 both 로 올렸는데, "리스크 게이트가 추정값으로 돌고 있다" 는 쪽이 오히려 더 money-critical 이라 `send_rule_alert(channel=both)` 로 통일.
- 스윕이 `summary["applied"]` 와 metric 을 **커밋 전에** 증가시켰다 → 커밋 실패 시 "보정 완료" 로 과다계상. 커밋 성공 뒤 계상으로 이동.
- give-up metric(`never_found` / `failed_provider`)과 provider 예외 소진 분기에 테스트가 없었다 → 3건 추가.

## #7. ★함정 (상속 + 신규)

- **상속**: BE pytest 3-env(`.env.local` 의 5433 은 stale) / `ruff format` 은 게이트 아님(단 pre-commit 훅은 돌린다 — 커밋 후 재게이트 의무) / docker 포트 오버레이 `--no-deps` / DB 스키마 prefix / 3000=nexus·3100=QuantBridge·8100·5436·6380 / em-dash 래칫 / authed spec testMatch 열거식 / QB_PRE_PUSH_BYPASS=1.
- **★codex 샌드박스가 localhost:5436 을 막는다**(`Operation not permitted`). 워커는 DB 비의존 테스트만 돌릴 수 있으므로 **전체 스위트는 평가자가 메인 venv 로 직접** 돌려야 한다. 이번에 워커 자기보고를 믿었다면 빨간 스위트를 그대로 PR 에 올렸을 것이다.
- **★codex 워커는 자기가 건드린 파일에 prettier 를 돌린다.** FE 1차에서 `globals.css` 전체 재포맷 **3989줄** diff 가 나왔다(의도한 변경은 `min-width` 1줄). 되돌리고 1줄만 재적용 → 197줄로 정리. **워커 종료 직후 `git diff --stat` 범위 검사 의무.**
- **★ccxt `fetch_positions_history` 의 클라이언트측 시간 필터**(#5 참조) — `since` 는 거래소 `createdTime` 기준이지 우리 감지 시각이 아니다. 이 계열 API 를 쓸 때마다 재확인할 것.
- **★`filled_at` 은 오버로드 컬럼** — `transition_to_rejected`/`transition_to_cancelled` 도 terminal 시각으로 쓴다. 시간창 쿼리엔 `state==filled` 필수.
- **★ccxt 파싱값 vs 원본** — `position["realizedPnl"]` 은 `safe_number` = **float**. 금액은 반드시 `info` 의 원본 문자열에서 `Decimal` 로.
- **★로컬 `quantbridge_test` 스키마 stale** — conftest 의 `create_all` 이 신컬럼 포함 테이블을 만든 뒤 `alembic upgrade` 가 `ADD COLUMN` 하면 `DuplicateColumn` 으로 `test_migrations.py` 5건이 유령 실패한다. DB 재생성 후 base 부터 체인 실행이 정답(CI 는 fresh DB 라 미발생).

## #8. dogfood — 새 거래 없이 실자금 데이터로 종단 검증

**대조 쌍을 기존 데이터에서 확보했다.** 07-24 수동 청산 3건이 `realized_pnl=NULL` 로 남아 있었고, 각각의 `exchange_order_id` 가 오라클 closed-pnl 행과 1:1 로 연결됐다.

| DB 주문    | exchange_order_id | 오라클 closedPnl | 백필 후 DB         |
| ---------- | ----------------- | ---------------- | ------------------ |
| `e9026276` | `9f1d7420…`       | -0.04524449      | **-0.04524449** ✅ |
| `fc28e6f5` | `e2face86…`       | -0.08623685      | **-0.08623685** ✅ |
| `c5de321e` | `f6540828…`       | 0.08781055       | **0.08781055** ✅  |

- **오라클 자체 검증** — `closedPnl = gross − (openFee+closeFee)` 정확 성립(`(64144−64118.7)×0.001 = 0.0253`, fees `0.07054449`, net `-0.04524449`). `e9026276` 은 **시뮬값 기준 이익이던 거래가 실제로는 손실**이라 부호가 뒤집힌다.
- **ccxt 실계약** — `fetch_positions_history` 가 오라클 raw 와 바이트 일치. **프로덕션이 타는 `since`/`until` 창 호출**로 3건 전부 매칭(창 2.0h/10.7h/10.8h → 행 1/2/3, 시간 필터 정상).
- **스윕 종단** — run 1 `{scanned:3, applied:3, orphan:0, groups:1}`(그룹당 provider 1콜), run 2 `{scanned:0, applied:0}` = **멱등·종료 조건 실증**.
- **Kill Switch 반영** — 계정 SUM `42.46070000` → **`42.41702921`**, 정확히 `-0.04367079`(백필 3건 합) 이동. 수동 청산이 리스크 게이트에 계상되기 시작한 것이 실증됐다.
- **authed 브라우저**(3100) — 헤더 **12열** 정확, 첫 행이 `-0.04524449` + **"거래소 확정"** 배지, 두 배지 모두 렌더, **body 가로 스크롤 false**(canon 유지), **콘솔 error 0**.
- **BL-362 실수신** — `channel=both`, 메시지에 클래스명 있고 raw 텍스트 없음, 실발송 결과 **`{'slack': False, 'telegram': True}`**. ★부수 발견: `SLACK_WEBHOOK_URL` 이 이 환경에 **미설정**이라 **이번 스프린트 전까지 발산 알림은 아무에게도 도달하지 않았다.** 채널 격리(Slack 실패가 텔레그램을 막지 않음)도 동시에 실증됐다.
- **부분체결** — Bybit demo BTCUSDT 시장가로는 유동성상 실제 부분체결 자극이 비현실적이라 결정론적 픽스쳐 테스트로 커버했다(정직 각주).

## #9. 게이트

BE **2651 passed / 46 skipped / 0 failed**(baseline 2611, +40) · ruff·mypy clean · FE **1088**(baseline 1084) · tsc·lint clean · alembic 왕복 + base 부터 전체 체인 + 드리프트 0 · 마이그레이션 **1**(`20260725_0001`).
