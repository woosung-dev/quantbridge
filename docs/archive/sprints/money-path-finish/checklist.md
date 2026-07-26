# money-path-finish 체크리스트

> BL-457 (P2) + BL-454 (P2) + BL-458 (P2) + 신규 BL-464 — 머니-패스 정확도 마감 팩. 마이그레이션 **0**.
> 플랜 SSOT = `~/.claude/plans/claude-plans-quantbridge-moneypath-fini-vectorized-cosmos.md`. 계약 = [`operating-contract.md`](operating-contract.md). 결정 이력 = [`context-notes.md`](context-notes.md).

---

## §0 전제 게이트

- [x] PR [#480](https://github.com/woosung-dev/quantbridge/pull/480) main 머지 확인 (`b97ac57`) · 트리 클린
- [x] 브랜치 `stage/money-path-finish` (main 베이스)
- [x] 스택 — db **5433** healthy · redis **6380** · worker/beat/ws-stream/optimizer-heavy up
- [x] BE **8100 → 401**(정상) · FE **3100 → 200**
- [x] alembic head `20260725_0002` · 리비전 파일 34
- [x] baseline 재측정 — BE **2972 passed / 46 skipped** · FE **1115 / 194 files** · design-canon **32** · BE ruff·mypy clean · FE typecheck·lint clean
- [x] **마이그레이션 판정 재확인** — `trading.orders` **0행** · `live_signal_sessions` **0행** → 백필 비용 0 창 유효
- [x] codex G0 — BLOCKING **0** · P1 **4** · P2 **1** (전건 코드 대조 후 반영, §7.3)

### ★게이트 실체 정정 — `format:check` 는 통과 가능한 게이트가 아니다

- [x] `pnpm format:check` 가 **main 에서 이미 356 파일 red**. 트리 클린 상태에서 실패하므로 내 회귀가 아니다
- [x] 원인 규명 — `package.json:14-26` lint-staged 가 FE `{ts,tsx,js,jsx}` 에 **eslint 만** 돌린다(prettier 없음) → 드리프트 누적. 내가 만질 `hooks.ts` 조차 baseline 에서 dirty
- [x] 대응 — 이번 스프린트 FE 포맷 기준은 "주변 스타일 일치", `format:check` 는 **baseline 356 대비 불변**만 확인. 356 파일 일괄 포맷은 스코프 밖(거대 diff)
- [x] BE `.py` 는 커밋 시 `ruff format` 이 도므로 **커밋 후 재게이트 의무**

## §0.5 실측 스파이크 — 백로그 서술을 믿지 않았다

- [x] `exchange_exits` 4행 구성 실측 — **전부** `create_type='CreateByUser'` · `stop_order_type=NULL` · `matched_order_id=NULL` · `attribution_confidence='none'`
- [x] **`ours` 3행과 `external_manual` 1행을 가른 유일한 차이 = `order_link_id` UUID 유무** → branch 3(형식 판정)이 원장의 모든 `ours` 를 만들었다는 것을 데이터로 확인
- [x] canonical 심볼 확인 — FE 폼 기본값·placeholder `BTC/USDT`, `toBybitTickerSymbol` 이 raw 로 내림, 거래소 원장은 `BTCUSDT`
- [x] **BL-457 "새 쿼리 불필요" 는 틀렸다** — `attribution_facts` 는 `limit=500` + `state==filled` 로 좁혀졌고 branch 3 은 정의상 filled 매칭 실패 행에서만 도달 → 순진한 membership 은 진짜 우리 청산을 external 로 뒤집는다
- [x] **BL-458 "소비처 5곳" 은 정확** — SQL 4 + 파이썬 1. 레포가 이미 Site 1~5 어휘를 쓰므로 재사용
- [x] **6번째 소비처 없음 확인** — `LiveSignalState` 영속 컬럼은 pine 값이고 `/state` 가 버린다
- [x] **★신규 결함 발견 (BL-464)** — `attribute_exit` 이 `order.symbol`(`BTC/USDT`)을 `snapshot.symbol`(`BTCUSDT`)과 비교 → 구조적으로 절대 매칭 불가. 생산부·축약부·비교부 3지점 코드 확인 + DB 4행 `attributed_strategy_id=NULL` 로 정합

## §1 사용자 인터뷰 — 답 없이 구현 금지

- [x] D1 스코프 = **BL-457 + 454 + 458**(+ BL-464). BL-446 제외
- [x] D2 BL-458 = **라벨 + 소계 · 사람이 읽는 2표면**(Site 3·4). 게이트 수식 무변경 · 필터링 기각
- [x] D3 과거 원장 = **불변 · 신규만 엄격** (마이그레이션 0)
- [x] D4 정규화 = **공용 도메인 프리미티브 타입**(`src/common/normalized_symbol.py`, 선례 `strict_decimal_input.py` 미러)
- [x] D5 실패 정책 = **거부 + 전용 관측**(장식 제거 추측 코드 금지)
- [x] D4·D5 근거를 1차 출처로 조사 — CCXT 계약 · TV `{{ticker}}` 문서 · Parse-don't-validate. ★TV 퍼프 `.P` 여부는 **확인 실패 → 그래서 fail-closed + 관측**

## §2 슬라이스

### S1 — BL-464 심볼 공간 정렬

- [x] **C-red** — `_snapshot` 기본 심볼 `BTC/USDT` → `BTCUSDT`(거짓말하는 픽스처 정정) + 귀속 테스트 신규
- [x] red 확인 — `ExitAttribution.none` vs `inferred`(축이 죽은 것을 테스트로 증명)
- [x] **C-green** — `_order_facts` + `attribute_exit` 호출 양쪽에 `to_bybit_raw_symbol`
- [x] `normalize_symbol` 을 쓰지 않은 이유 명시 — raise 시 계정 루프의 outer except 에 삼켜져 **그 계정 원장 적재 전체를 잃는다**

### S2 — BL-457 실재 확인

- [x] **A-red** — 버그를 계약으로 못박은 순수 테스트 2건 재작성(`:56` · `:152`)
- [x] red 확인 — `TypeError: unexpected keyword 'known_order_ids'`
- [x] **A-green** — `classify_exit(known_order_ids=...)` **required** + 분기 8 신규 + `parse_our_order_link_id` 공개화
- [x] **A-repo** — `OrderRepository.list_existing_ids`(술어 2개 · **state 무필터**)
- [x] 실DB 테스트 — `state=submitted` 반환 · 타 계정 미반환 · 빈 입력 short-circuit
- [x] 스윕 배선 — 후보를 기존 `async with sm()` 블록에서 조회(왕복 추가 없음)
- [x] 스윕 레벨 테스트 2건 — 미확인 UUID → `unknown` + **알림 발화** / 실재 확인 → `ours` + 알림 0
- [x] **A-obs** — `qb_exchange_exit_link_unverified_total` · `qb_exchange_exit_attribution_total{confidence}` + `exchange_exit_link_id_unverified` 경고(orderLinkId 원문 포함) + 카운터 delta 테스트

### S3 — BL-454 ingress 정규화

- [x] **B-primitive** — `src/common/normalized_symbol.py` 신설, `normalize_symbol` 이동 + `market_data` 에서 `__all__` 로 명시 재수출
- [x] **순수 이동 증명** — `tests/market_data/test_constants.py` **git diff 0 으로 12 passed**
- [x] 강화는 `normalize_symbol_input` 안에만 — 이동한 함수를 엄격화하면 `backtest`·`market_data` 기존 저장값 동작이 바뀐다
- [x] 콜론 표기 처리 — settle ≠ quote 거부(`BTC/USD:BTC`) + `BTCUSDT:USDT` → `BTCUSDT:/USDT` 쓰레기 트랩 제거
- [x] unified 정규식으로 `/`-passthrough 구멍(`BTC/USDT.P`) 봉쇄
- [x] **B-ingress** — `RegisterLiveSessionRequest.symbol = NormalizedSymbol` + `parse_tv_payload` 동일 함수 + `qb_webhook_symbol_rejected_total` + 원문 로그
- [x] **길이 순서 증명** — `"A"*30+"USDT"` 가 `ValidationError`(BeforeValidator 가 str 제약보다 먼저 돈다는 것을 추론이 아니라 테스트로)
- [x] 경계→영속 종단 — `repo.save.await_args.args[0].symbol == "BTC/USDT"`
- [x] **B-flip** — D5 characterization 테스트 개명·독스트링(본문 불변) + 모듈 독스트링 + `SessionScope` 독스트링 정정
- [x] **유니크 충돌 테스트** — `BTCUSDT`/`BTC/USDT` 가 한 문자열로 붕괴해 `IntegrityError`(의도된 동작 변경 고정)

### S4 — BL-458 라벨 + 소계

- [x] 순수층 — `RealizedPnlSource` · `SessionEquityPoint`(형제 TypedDict — `EquityPoint` 는 영속 형태라 무변경) · `label_curve_provenance(strict=True)`
- [x] Site 3 리포 — `sum_filled_realized_pnl_for_session` → `realized_pnl_split_for_session -> SessionRealizedPnl`(PG `FILTER` 한 문장 5 스칼라)
- [x] 호출부 전수 갱신 8곳(prod 1 + test 7) — codex P1-1 목록 대조
- [x] Site 3 알림 — 한국어 본문 + `거래소 확정`/`추정` FE 어휘 재사용 + `unrecorded` 절 조건부
- [x] **codex P2 수용** — context 는 5키가 아니라 **6키**(`scope` 포함)이고 인용한 real-DB 테스트는 두 값만 단정 → 11키 전수 단정 신규
- [x] Site 4 — 스키마 평면 4필드 + 라우터 triple 한 리스트(필터 복제 금지) + Decimal-first 소계
- [x] **codex P1-2 수용** — pending 정확-dict 테스트에 신규 4키 명시(약화 금지)
- [x] Site 4 종단 — **리포 SQL 술어와 라우터 파이썬 라벨이 반전되지 않았는지** 고정
- [x] 분할 정확성 실DB — 확정/추정/미기록 세 카운트가 스코프를 정확히 분할
- [x] **가드레일 강화** — 대조군 seed 에 `synced_at` 심음 → Site 1/2/5 값 불변 확인(출처 마커가 게이트 술어로 새지 않았다는 증명)

### S5·S6 — FE

- [x] **zod + strip 가드를 컴포넌트 작업보다 먼저** — 없으면 기능 전체가 green 으로 출하되고 아무것도 안 그려진다
- [x] `.optional()`(`.default()` 금지 — 추론 출력 타입이 필수가 되어 기존 픽스처 전부 깨짐) + `curvePointSource` 폴백(부재 → 추정)
- [x] 집계 — `number | null`, **모든** 채워진 세션이 보고할 때만 합산(부분 분할은 없는 것보다 나쁘다) · 기존 루프에 누적(추가 순회 0)
- [x] 세션 상세 칩 2개 — `@/features/trading/labels` **직접 import**(복사 금지)
- [x] 대시보드 §01 KPI foot 분할 줄 + null 이면 미렌더
- [x] `utils.ts` carry-forward 에 출처 동반(값만 옮기면 색이 값과 어긋난다)
- [x] `trading-chart.tsx` per-point color 보존 + **색 미지정 시 출력 불변** 테스트(공유 컴포넌트 10여 호출자 무영향 증명)
- [x] `activity-timeline-chart.tsx` 추정 구간 muted(새 팔레트 토큰 0)
- [x] **★병합 커브 제약 해소** — `mergeCumulativeCurves` 는 carry-forward 합산이라 포인트별 출처가 **표현 불가** → 곡선은 집계 수준 고지, 구간별은 세션 상세
- [x] `/vercel-react-best-practices` 호출 — 알려진 줌-리셋 함정 재발 없음 확인 + 지적 1건(빈 객체 스프레드) 수정

## §3 게이트 (CI 미기동 → 로컬이 유일 관문)

- [x] BE `ruff check src/ tests/` — All checks passed
- [x] BE `mypy src/` — 205 files, no issues
- [x] BE `pytest -q` — **3000 passed / 46 skipped** (baseline 2972 → **+28**)
- [x] FE `pnpm test` — **1124 passed / 194 files** (baseline 1115 → **+9**)
- [x] FE `typecheck` · `lint` — clean
- [x] FE `build` — 성공
- [x] `format:check` — 선재 356 red **불변**(§0 참조)
- [x] design-canon e2e — **32 passed 불변**
- [x] `alembic heads` — `20260725_0002` **불변** · 리비전 파일 34 **불변** → **마이그레이션 0**

## §4 마감

- [x] `docs/archive/sprints/money-path-finish/{checklist,operating-contract,context-notes}.md`
- [ ] `docs/archive/sprints/exit-money-path/operating-contract.md` §1·§3.2·§4 갱신
- [ ] `docs/backlog.md` — BL-457/454 Resolved · BL-458 부분 · **BL-464 신규** · ★BL-457 의 잘못된 "권장 접근" 제자리 정정 · `:2287` stale ID 범위 정정
- [ ] `docs/status.md` · `docs/dev-log/` 회고 + `INDEX.md` · `docs/roadmap.md` 체크박스
- [ ] 커밋 1개 → push → PR (squash 는 사용자)
