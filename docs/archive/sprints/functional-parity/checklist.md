<!-- 기능 격차 마감 스프린트(functional-parity)의 작업 항목·게이트 추적 체크리스트 (SSOT) -->

# functional-parity 체크리스트

> 스프린트 정본: `~/.claude/plans/magical-puzzling-yeti.md` · 운영 계약: [`operating-contract.md`](operating-contract.md) · 결정 기록: [`context-notes.md`](context-notes.md)
> 기준 커밋: main @ `88faccd` → `stage/functional-parity`

## 0. 범위 (사용자 확정 2026-07-23)

- Tier A(FE 배선·결함) + Tier B(소형 BE 동반). Tier C(WS/포지션동기화/알림/펀딩) 전부 제외.
- 전략 상세 화면 신설 금지 — 대시보드 링크는 edit 재조준.
- **기구현 5건 재구현 금지** (main 88faccd 실측): screen-06 필터+CSV / screen-07 진단 섹션 / screen-10 안정성 섹션(grid) / sprint55 e2e 재배선 / BL-402(네이티브 select 전환으로 구조 소멸) → 회귀 검증 + 문서 상태 갱신만.

## 1. 작업 항목

### W-trading (`fp/trading`)

- [x] **A2 주문 취소 배선 (M)** — BE `POST /api/v1/orders/{id}/cancel` 기존재(CF4). 액션 열 재도입(screen-11 `:1278` 10번째 열, `.btn.btn-xs.btn-danger`, 확인 다이얼로그 없음·title 경고가 캐논). 202=「거래소에 취소를 요청했습니다」(취소됨 표기 금지), 409=안내 toast+invalidate. `orders-blotter.tsx:4-5` 잘못된 전제 주석 교정. `orders-blotter.test.tsx:134` 9열 단언 반전.
- [x] **B2 nav-count 미체결 소스 (S+S)** — 캐논 `_KIT.md` §4.6 복원. BE `list_orders` state 반복 Query + `OrderRepository` states 필터. FE `useOpenOrdersCount()`(limit=1, states=[pending,submitted]) + 사이드바 교체 + countTitle 갱신 + `ORDER_FILTER_HINT.navCount` 문구 반전.

### W-strategy (`fp/strategies`)

- [x] **B1 `strategy.backtest_count` (M)** — 저장 컬럼·migration 없이 read-time GROUP BY 집계. 정의=COMPLETED 기준(FE `STRATEGY_BACKTEST_COUNT_HINT` 선제 등재와 정합). BE repository+service+`StrategyListItem` / FE 스키마 optional+`strategy-list.tsx` 열 재도입(스켈레톤 5→6열, CSV 열 추가).
- [x] **A1 대시보드 링크 404 (S)** — `dashboard-cockpit.tsx:424` `/strategies/{id}` → `/strategies/{id}/edit` + href 테스트 단언.

### W-optimizer (`fp/optimizer`)

- [x] **BL-401 zod field 에러 렌더 (M)** — 3폼 `formState.errors` 전달 + `.field-error` 프리미티브(waitlist FieldError 패턴, role=alert). `form-schemas.ts` 메시지 한국어화(payload 무변경 — characterization 테스트 유지). 신규 필드 에러 테스트 3폼.
- [x] **BL-411 stale 422 메시지 (XS, BE)** — `optimizer/exceptions.py` 지원 목록을 `OptimizationKind` enum 파생으로. `test_exceptions.py:21,30` 동반 갱신.

### W-backtest (`fp/backtest`)

- [x] **A7-lite 최신 스트레스 결과 복원 (S)** — `GET /stress-tests?backtest_id=&limit=1` 배선, `stressTestKeys.byBacktest` 소비, `activeStressTestId ?? latest?.id` render-time 파생(effect 금지).
- [x] **C1 정리 (S)** — `backtest-history-card.tsx` 삭제 / `viewBacktestShare()` 삭제 / `StrategyWithPine` 로컬 stub 제거(`StrategyResponseSchema.pine_declared_qty` 직접 사용).

### W-final (오케스트레이터 직접)

- [x] 기구현 5건 회귀 검증 — 통합 vitest 980 그린 + authed 62 (sprint55 재실행 포함)
- [x] e2e: `authed-functional-parity.spec.ts` 신설(5 case — A1 클릭스루 포함으로 tier1 확장 대체) + testMatch 등재 + sprint55 BL-401 확장 1 case
- [x] BL 등재: defer BL-413·BL-414 + 평가 파생 BL-415·BL-416 / Resolved: BL-401·BL-402·BL-411
- [x] `docs/status.md` 갱신 · `terminology-ssot.md` §6-3 해소 기록 · `HANDOFF.md` 6판 §3 소거 표기

## 2. Defer 확정 (프로토타입 근거 부재 — 캐논 준수)

- 주문 상세 조회(`GET /orders/{id}`) — screen-11 에 행 확장/드로어 affordance 0건.
- 스트레스 테스트 이력 리스트 화면 — 17벌 어디에도 없음 (A7-lite 로 기능 격차의 본질만 해소).

## 3. 게이트 추적

| 게이트                                            | baseline              | 목표                                      | 실측                                                                                   |
| ------------------------------------------------- | --------------------- | ----------------------------------------- | -------------------------------------------------------------------------------------- |
| FE vitest                                         | 965 passed (169 파일) | 순증 그린                                 | ✅ **980 passed (171 파일)**                                                           |
| FE tsc / lint                                     | 그린                  | 그린                                      | ✅ 0 / 0                                                                               |
| BE pytest                                         | 2412+2env실패         | 그린                                      | ✅ **2416 passed·46 skipped·0 failed** (+waitlist 18 = `TEST_REDIS_LOCK_URL` env 해소) |
| BE ruff / mypy                                    | 그린                  | 그린                                      | ✅ 0 / 0                                                                               |
| e2e:design-canon                                  | 32                    | **32 불변**                               | ✅ **32/32** (3100 재조준 후 warm)                                                     |
| e2e:authed                                        | 56 / skipped 0        | 56→N 증가, `--list` 증빙                  | ✅ **62/62** (`--list` 62 등재 확인)                                                   |
| DB 오라클 3건 (취소·backtest_count 3점·nav-count) | —                     | Fable 직접 실측                           | 진행 중 (시딩 완료: 미체결 2·카운트 [0,2,0,1,0,0])                                     |
| Opus MCP dogfood                                  | —                     | 신규 배선 화면 전수 + 기지 예외 외 콘솔 0 |                                                                                        |
