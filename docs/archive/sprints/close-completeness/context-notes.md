<!-- close-completeness 의사결정·발견 기록 (append-only). 상속 체인 = tier-c → opspack-ws2 → perf-surface → position-cockpit → trading-surface-pack → close-completeness -->

# close-completeness context-notes

> trading-surface-pack(#473) 후속. 청산/TP-SL 완성도 3건(B1 즉시 flat / B2 청산 margin_mode 503 회피 / B3 완전 TP/SL 보고). 마이그레이션 0.

## #1. 인터뷰 확정 (2 라운드)

1라운드(착수):

1. **B3 표시 형태 = 포지션 행 병합 합산** — 익절/손절 셀에 포지션-부착값 + 조건부값 합산, 다중=마크 근접순 콤마(포지션-부착값 앞), 유형(Limit/Stop) 구분은 각주.
2. **B3 청산 스윕 = 포지션 방향 귀속** — reducing side + positionIdx(hedge forward). 벤치마킹(Bybit positionIdx / Binance positionSide / 터미널 flatten)으로 "방향 귀속"이 롱·숏 공존 시 유일 안전 확인.

2라운드(codex G0 후 — 프레임 체인지 재인터뷰):

3. **청산 스윕 = 후속 BL 이연** — G0 이 스윕에서 2 BLOCKING(타이밍 accept≠fill / account+symbol 공유 세션 오취소)을 드러냄. B3 = 완전 보고(display)만 + hedge 가드.
4. **트레일링 = 각주 표기만** — 트레일링 스톱은 포지션 속성(거리값, 가격 아님) → 가격 셀에 미표시, has_trailing_stop 시 각주.

## #2. codex G0 = REJECT, 전건 코드 대조 검증(§7.3) 후 개정

- **B2 [BLOCKING] marginMode 신뢰 불가 → skip 전환**: `create_order`(:545-556)는 reduce-only 포함 항상 set_margin_mode/set_leverage. ccxt `marginMode` 는 Bybit v5 tradeMode deprecated 로 신뢰 불가. → "포지션 marginMode 읽기" 폐기, **`if not order.reduce_only:` 로 set 자체 skip**(reduce-only 는 기존 포지션 유지). reduce_only 는 이미 Order 영속·OrderSubmit 운반 → **마이그레이션 0**(PositionSnapshot.margin_mode 불요).
- **B1 [MAJOR] cache-inval ≠ immediate flat + close 는 async Celery**: accept 직후 DEL 은 close 실행 전이라 무효. → **post-fill Celery DEL**(`_execute_with_session` reduce_only fill 승자, list_active_by_account 세션 캐시 best-effort DEL).
- **B3 [BLOCKING] 2콜 union 중복**: `fetch_open_orders(sym, {..})` 는 dict 를 since 로 넘김(→`params=` 키워드). trigger 미지정 시 Bybit 가 StopOrder 도 반환 → union 중복 → **orderId dedupe**. [MAJOR] `stopOrderType=Stop`/미상은 TP/SL 단정 불가 → 엄격분류(TP/SL/Trail 만, 그외 other 표시제외). [MAJOR] Full 포지션-부착 vs 조건부 중복 → source-dedup.
- **B3 [BLOCKING] trail = position 필드**(set_trading_stop, 주문 아님) → PositionSnapshot += trailing_stop + has_trailing_stop.
- **B3 [BLOCKING] hedge 미차단**: zero-size leg 버림 → 1-leg hedge 통과, close 가 positionIdx 미전달 → positionIdx≠0 409 가드.
- **B3 [BLOCKING] 스윕 타이밍/교차세션** → 이연(위 #1.3).
- **codex 자기 철회**: cancel_order 는 orderFilter 없이 StopOrder 취소 가능(linear). B1 키 SSOT 3콜 정당.
- codex 최종 diff = **[P1] 1건**(has_trailing_stop 이 조건부 trail 무시) → `or any(kind=="trail")` + 회귀테스트 추가.

## #3. ★함정 (상속 + 신규)

- **상속**(trading-surface-pack §3): BE pytest 3-env / ruff check(format 아님)+mypy+pytest / codex resume `-s` 는 resume **앞**·`-C` 거부(cd 후) / DB 스키마 prefix(trading./public.·killswitch enum 소문자) / next build↔dev .next 공유 / 신선 JWT=Clerk.session.getToken / 3000=nexus·5436·8100·6380 / em-dash 래칫 / QB_PRE_PUSH_BYPASS=1.
- **★docker db/redis 포트 오버레이 클로버(신규·중대)**: 스택은 db 5436·redis 6380 **커스텀 오버레이**인데 base docker-compose.yml 은 5432/6379 하드코딩. **`docker compose up -d --build backend-worker`(plain)가 depends_on 인 db/redis 를 재생성해 base 포트로 되돌림**(볼륨 보존). 증상 = pytest 411 errors + BE dev 서버(8100) 접속불가(2195 pure-unit 만 통과). 복구 = 포트 오버레이 파일(`ports: !override [5436:5432]/[6380:6379]`)로 `docker compose -f base -f override up -d db redis`. **worker 만 재빌드 = `--no-deps` 필수**.
- **★ruff B023(루프 내 중첩함수)**: get_reconciliation 루프 안 `def prices` 가 loop 변수(position/belonging_orders) 캡처 → B023×3 + mypy operator(mark_price narrow 미전파). → 모듈레벨 `_merged_prices(kind, full_price, belonging_orders, mark_price)` hoist(명시 파라미터 + 로컬 narrow). codex resume 로 수정.
- **★authed dogfood spec 발견 함정**: chromium-authed testMatch 열거식 → 파일명 미등재 시 미발견. 임시 등재 후 실행·revert.
- **★Pyright IDE 경고 오탐**: venv 미해석(fastapi/sqlalchemy/ccxt import) + SimpleNamespace mock 타입 = 프로젝트 게이트 아님(mypy `[mypy-tests.*]` 제외 + venv 해석). ruff/mypy in-venv 로 판정.

## #4. dogfood — 2계통 오라클(앱↔독립 curl HMAC) + BE end-to-end + authed 브라우저 전 PASS

- **독립 오라클** = `bybit_oracle.py`(Fernet 복호화 + api-demo.bybit.com raw HMAC, GET/POST). balance 190679 USDT 일치.
- **B3 셋업+대조**: 오라클 POST(place Buy 0.001 → set-trading-stop tpslMode=Partial TP=66000/SL=62000) → **오라클 raw = PartialTakeProfit trigger=66000 / PartialStopLoss trigger=62000, side=Sell reduceOnly posIdx=0, 포지션 tp/sl 필드 비어있음(Partial 이라 갭 실증)**. 앱 provider(`app_provider_check.py`) `fetch_open_conditional_orders` = **kind=tp/sl trigger 66000/62000 정확 분류 + count=2(ALL·StopOrder 중복을 dedupe)** → 오라클과 정확 일치. BE end-to-end(`dogfood_be.py get_reconciliation`) = **[MERGED] 익절=['66000.0'] 손절=['62000.0'] trailing=False**(기존엔 None→"—").
- **B1/B2 청산 종단(authed 브라우저 spec)**: §03 이 66000/62000 병합 표시 + 병합 각주 → 청산 버튼→모달→청산 실행 → §03 flat(66000 미표시) → **콘솔 error 0**. 오라클 대조 = 포지션 flat(size 0) + **조건부 주문 0(Bybit 가 flat 시 Partial 자동취소 → 스윕 이연 안전성 실증)** + DB Order `sell reduce_only=true filled` + **redis `qb_pos_snapshot:*` 키 부재(B1 post-fill DEL 확정)** + worker 로그 fill(set_margin_mode/503 없음 = B2 skip).
- 상태 복구: 세션 601e56eb 비활성(is_active=false, last_eval NULL) + active 세션/KS 0 + 포지션 flat + docker 포트 5436/6380 복구 + alembic 20260724_0002(head) 무변경. psql 재검증.

## #5. 게이트 / 검증 체인

- generator(codex 2워커 병렬, be/fe 교집합 0) ↔ **evaluator(Claude 서브에이전트 per-worker, 게이트 직접 실행)** 엄격 분리. W2 fe PASS(즉시). W1 be = pytest 2610 그린·correctness clean 이나 ruff B023×3+mypy 1(중첩함수) → codex resume hoist → PASS.
- codex G0(REJECT, 전건 코드 대조 개정) → 2워커 생성 → per-worker 적대평가 → codex 최종 diff([P1] 1 해소+테스트) → dogfood 3계통.
- 게이트: BE **2611**(+10: W1 9 + trail 1)·FE **1084**(+1)·ruff/mypy/tsc/lint 0·canon **32 불변**·마이그레이션 0(alembic 무변경).
