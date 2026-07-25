<!-- exit-attribution 실행 체크리스트 — 계약은 operating-contract.md, 결정 기록은 context-notes.md -->

# exit-attribution 체크리스트

## §0 전제 게이트

- [x] PR #475 main 머지 확인(`6b200e5`) + 트리 클린 → `stage/exit-attribution` 생성 (main 베이스)
- [x] 스택 기동 확인 — db 5436 · redis 6380 오버레이 정상 · worker/beat/ws-stream up
- [x] baseline 재현 — BE **2653 passed / 46 skipped**, FE **1088 passed**, alembic head `20260725_0001`

## §0.5 구멍 규모 측정 스파이크 (설계보다 먼저)

- [x] 독립 오라클로 07-01~07-25 closed-pnl **11행** 전량 수집 (7일 창 분할)
- [x] `exchange_order_id` 대조 → 매칭 **7** / 거래소 전용 **4**(행 36.4% · |손익| 55.8%)
- [x] 산술 폐쇄 확인 — 거래소 `−0.79748097` vs 앱 `−0.08297079` = **10.4%**, 잔여 = 고아 55.8% + 시뮬 오차 33.8%
- [x] `/v5/order/history` 로 고아 4건 분류 → 전부 `CreateByUser`·`orderLinkId` 없음 = **앱 밖 수동 청산**
- [x] **브래킷 체결 0건 실증** — 조건부 주문 4건 전부 `Deactivated`, DB 17행 중 TP/SL/트레일링 실은 주문 **0**
- [x] `avgEntryPrice` 대조 → 고아 4건 중 우리 포지션은 **1건뿐**

## 계획 · 검증

- [x] codex G0 (핸드오프 read-only) — **REJECT**, 전건 코드 대조(§7.3) 후 절반 수용 / 절반 실측 반박
- [x] Explore 3-리더 grounding (손익 소비처 / 주문 생성·#475 자산 / WS·FE) — 핸드오프 좌표 **3건 실측 반박**
- [x] Plan 압박검증 — **설계 결함 6건**, 그중 원장 min 파생 워터마크가 빈 창에서 영구 정지
- [x] 사용자 인터뷰 **10건 확정** (D1~D10)
- [x] ccxt 실계약 검증 — 심볼리스 열거 · 7일 창 `retCode=10001` · `side` 뒤집힘 · `fetch_orders` UTA `NotSupported`

## S1 provider — 창·심볼리스·보강 조회

- [x] `ClosedPnlSnapshot` 9필드 확장 (끝에 default, 위치 인자 5개 하위호환)
- [x] `fetch_closed_pnl_window` 신설 + `_validate_closed_pnl_window`(7일 상한)
- [x] `fetch_closed_pnl_page` 를 래퍼로 재정의(기존 호출자 계약 불변 + 최근 7일 클램프)
- [x] `_fetch_closed_pnl_rows` 심볼 옵셔널 → **계정당 1콜 전 심볼 열거**
- [x] `fetch_closed_order_meta` + `ClosedOrderMeta` (`fetch_closed_orders` 경유)
- [x] 페이징 커서를 **createdTime 축**으로 교정 + 단조 전진 강제
- [x] **커서 경계 포함**(`until = oldest_ms`) — 같은 createdTime tie 행 조용한 누락 차단 (§S6, 최종 codex diff P1)
- [x] 기존 3필드 **strict 파싱 복원**(fail-loud 삼킴 회귀 차단)

## S2 원장 — 마이그레이션 · 모델 · 리포지토리

- [x] `trading.exchange_exits`(행 단위 원본 + provenance JSONB) + 3 인덱스
- [x] ~~`trading.exchange_exit_sync_state`(과거 스캔 경계)~~ → **범위 축소로 제거**(§S6)
- [x] 마이그레이션 `20260725_0002` (신규 테이블 **1개**, downgrade `DROP TABLE IF EXISTS`)
- [x] `ExchangeExit.compute_row_hash` — `\x1f` 구분자 · `None`/`""` 동일 정규화 · 빈 order_id 거부
- [x] `ExchangeExitRepository` — upsert(청킹 500) / aggregate (`bounds`·워터마크 get·set 은 §S6 에서 제거)
- [x] `ExchangeAccountRepository.list_by_exchange`
- [x] `qb_exchange_exit_rows_total{classification}` (기존 8-outcome 계약 불변)

## S3 스윕 재작성

- [x] 계정 독립 열거 + 계정별 실패 격리
- [x] 창 선택 = ~~최근 1 + 워터마크 파생 과거 1 (horizon 90일)~~ → **최근 7일 1창**(§S6 축소)
- [x] 조건부 보강 조회 (정상 상태 0콜, 실패 시 `unknown` 으로 진행)
- [x] **원장 전체 집계 백필** (단일 fetch 아님 → 창 경계 부분합 고정 없음)
- [x] 커밋 후 계상 · 새 행만 metric · 알림 1회성(조회까지 try 안)
- [x] `orphan_row` 계상 제거 (호출부만)

## S4 분류 · 귀속

- [x] `classify_exit` 7종 + `stopOrderType` 폴백 + `orderLinkId` UUID 형식 검증
- [x] `attribute_exit` 두 조건 AND (가격 일치 **AND** 그 시각 보유 포지션), 후보 2개 이상이면 `none`
- [x] `list_filled_for_attribution` **DESC LIMIT 후 ASC 재정렬**(절단 부산물 차단)
- [x] `inferred` 가 머니-패스에 새지 않음을 테스트로 못박음

## S5 FE 소품

- [x] `displayRealizedPnl` SSOT — 화면·CSV·부호 톤 공유, `state==="filled"` 만 노출
- [x] `isPartialFill` / `realizedPnlSource` 도 SSOT 로 통합
- [x] 감춘 손익 셀에 상태별 사유 `title`
- [x] CSV — 손익 출처 열 신설 + 날짜 복원 + 부분체결 마커 (화면 12열 SSOT 불변)

## 안전 (사고 대응)

- [x] `_assert_disposable_database` — 파괴적 마이그레이션 테스트가 `_test` 아닌 DB 를 향하면 `RuntimeError`
- [x] 가드 실증 — 개발 DB DSN 으로 실행 시 파괴 대신 예외
- [x] `test_trading_schema_round_trip` 신규 테이블 반영 (9 → 11 → **10**, §S6 축소 후)

## 게이트

- [x] BE ruff / mypy / pytest 3-env — **2710 passed / 46 skipped / 0 failed** (baseline 2653, +57) → **축소 후 2706** (§S6)
- [x] FE tsc / test / lint — **1094 passed** (baseline 1088, +6), tsc·lint clean
- [x] alembic 왕복 + head `20260725_0002` (마이그레이션 **1**, 신규 테이블 **1개** — §S6 축소 후)
- [ ] canon 32 불변 · authed (`/orders` 라우트 직접 확인)
- [ ] §9.5 — 같은 worker child 에서 스윕 N회 연속 성공 + beat 자체 발화

## FE 증빙 (authed 브라우저 실촬영)

> 데이터 출처와 한계는 `screenshots/README.md` 참조 — 개발 DB 전소로 **촬영용 임시 데모 픽스처**를 쓰고 촬영 직후 전량 삭제했다.

- [x] Clerk `storageState` 주입 실브라우저(1920×1080, DPR 2)로 `/orders` 촬영
- [x] **거부(−1007.7)·취소(−1.00) 행의 실현 손익이 빈 칸** — 이번 정직성 수정의 핵심 증빙
- [x] 체결 행만 값 + **거래소 확정 / 추정** 배지, 부분체결 **부분** 칩
- [x] CSV 실내보내기 — **손익 출처 열 신설 · 시각의 날짜 복원 · 부분체결 마커**, 거부·취소 행은 손익·출처 모두 빈 칸, 헤더 12열 == 각 행 12열
- [x] **콘솔 error 0** · body 가로 스크롤 **false**

## dogfood

> ★로컬 개발 DB 전소(context-notes #6)로 거래소 계정·주문 이력이 소실됐다. 사용자 재등록 후 진행한다.

- [ ] 사용자: 앱에서 Bybit demo API 키로 거래소 계정 재등록
- [ ] 1 원장 적재 — 스윕 1회 후 행 수·손익 합이 오라클 raw 와 일치
- [ ] 2 분류 — 미귀속 행이 `external_manual` 로 분류(`createType=CreateByUser`·`orderLinkId` 없음)
- [ ] 3 멱등 — 2회차 `inserted:0`, 원장 행 수 불변
- [ ] 4 창 고정 — 매 주기 `[now−7d, now]` 한 창만 조회(§S6 축소로 과거 전진 없음)
- [ ] 5 알림 1회성 — 신규 미귀속 행에 1회 발화, 다음 주기 무발화
- [ ] 6 §9.5 라이브 worker — 같은 child 에서 연속 성공 + beat 발화
- [ ] 7 authed 브라우저(3100) — `/orders` 손익 셀·CSV·콘솔 error 0
- [ ] 8 상태 복구 — 활성 세션 0 · 포지션 미개설 · docker 5436/6380 보존
- [ ] **정직 각주** — 주문 이력이 없어 모든 closed-pnl 행이 미귀속으로 분류되므로 **백필(33.8%) 종단 검증은 이번 스프린트에서 불가**

## 최종 codex 누적 diff — DO-NOT-SHIP 2 + MAJOR 1 + MINOR 1 (전건 수정)

- [x] **DO-NOT-SHIP** 체결 직후 refresh 가 원장을 우회해 부분합을 CAS 고정 → `resync_exchange_realized_pnl` + 스윕 대조 경로
- [x] **DO-NOT-SHIP** `max_pages` 소진을 성공 취급 → `ClosedPnlWindow(rows, truncated)` + 잘린 창은 읽은 최고령 행까지만 경계 전진 _(§S6 축소로 dataclass 제거 → 발생 지점 로그 + 계정 식별자로 대체. 워터마크가 없어져 호출자가 대응할 수단이 사라졌기 때문)_
- [x] **MAJOR** 시각 결측 행이 로그만 남기고 소실 → `malformed_row` 계상
- [x] **MINOR** downgrade 인덱스 drop 무조건 실행 → `DROP INDEX IF EXISTS`
- [x] 4건 전부 회귀 테스트 부착

## S6 범위 축소 — 과거 전진 기계장치 제거 (2026-07-25, 머지 전)

> 사용자 판정. 원장은 **최근 7일만** 담는다. 배경·실측은 `context-notes.md` §9.

- [x] 마이그레이션 `20260725_0002` 에서 `exchange_exit_sync_state` `create_table` 제거 (**2 → 1 테이블**)
- [x] **downgrade 의 `DROP TABLE IF EXISTS` 는 의도적으로 남김** + 이유 주석 — 초판 적용 DB 에서 `downgrade base` 가 April 마이그레이션의 평문 `drop_table('exchange_accounts')` 에서 의존 FK 로 거부되는 것을 차단. `quantbridge_test` 자기치유 실측
- [x] `ExchangeExitSyncState` 모델 · `get/set_backfilled_from` · `created_at_bounds`(자기 고아, 기각된 설계를 문서화) 제거
- [x] `_EXIT_LEDGER_HORIZON_DAYS` · `_closed_pnl_windows` · 창 루프 · `window_index` · `truncated` 경계 복구 · `summary["windows"]` 제거
- [x] `ClosedPnlWindow` dataclass 제거 → `list[ClosedPnlSnapshot]` + **발생 지점 `logger.warning("closed_pnl_window_truncated")`** (최종 `truncated` 값 = 3경로 모두 · `log_context` 로 계정/심볼 식별)
- [x] **커서 경계 포함**(`until = oldest_ms`) — 최종 codex diff **P1**: 같은 createdTime tie 행이 페이지 경계에서 조용히 누락돼 부분합이 `realized_pnl` 로 고정되는 결함. 회귀 테스트 + 구 커서로 red 실증
- [x] 테스트 수술 — 워터마크 6건 삭제 · provider 잘림 2건을 **logger mock** 으로 전환(caplog 은 전체 스위트에서 격리 깨짐 실측) · 분할행 집계 테스트는 **원장 선적재**로 재작성(한 창에 합치면 무의미해짐) · 신규 2건
- [x] **페이크 세션을 트랜잭션화** — 커밋 시에만 원장에 보이게. 원장 커밋을 지우면 3건 red(이전엔 0건) 실증
- [x] 개발 DB 는 `DROP TABLE` 한 줄(alembic_version 유지), 검증은 가드 걸린 `quantbridge_test` 왕복 — 수동 alembic 이 개발 DB 를 향하는 구조(BL-451 ④) 회피
- [x] 게이트 재실행 — BE **2706** / ruff · mypy clean / alembic base→head + 10 테이블 센티널 / FE 미변경

## 마감

- [x] 최종 codex 누적 diff 리뷰 1회 (생략 금지) — **축소 후 재실행에서 P1 1건 추가 발견·수정**
- [x] docs/exit-attribution/{checklist,operating-contract,context-notes}.md
- [x] TODO / dev-log / BL — BL-438 부분 Resolved(관측 원장 최근 7일) · BL-442 Resolved · 신규 BL-443~**452**
- [x] push (QB_PRE_PUSH_BYPASS=1) → PR #476 본문 갱신 (squash 는 사용자)
