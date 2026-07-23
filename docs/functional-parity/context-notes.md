<!-- functional-parity 스프린트 중 내려진 결정과 근거의 누적 기록 (append-only) -->

# functional-parity 컨텍스트 노트

## 2026-07-23 W0 — 스프린트 성립 결정

1. **범위 확정 (사용자)**: Tier A+B. Tier C(WS/포지션동기화/알림/펀딩) 전부 제외. 전략 상세 화면 신설 금지(프로토타입 부재) — 대시보드 링크 edit 재조준.
2. **실측 반전 — 기구현 5건**: 계획 후보였던 screen-06 필터+CSV / screen-07 진단 / screen-10 안정성(grid) / sprint55 e2e / BL-402 는 main @ 88faccd 에 이미 구현 완료(#464 부채 마감 슬라이스). `docs/c-language-port/checklist.md` §FIX 는 그 픽스 이전 기록이었음. → **문서만 보고 재구현 착수하면 안 되고, 계획 시 main 실측이 선행이어야 한다** (§7.1 baseline preflight 의 재확인).
3. **A2 전제 반전**: 이식 당시 "주문 취소 API unbacked" 미렌더 결정(`orders-blotter.tsx:4-5` 주석)은 **잘못된 전제** — BE `POST /orders/{id}/cancel` 은 CF4 로 완전 구현돼 있었음. 미렌더 결정의 근거 주석이 코드 현실과 어긋난 채 캐논처럼 작동한 사례.
4. **B1 집계 방식**: 저장 컬럼+migration 대신 read-time GROUP BY. 근거 = denorm drift 회피 / 목록 ≤20건 / BacktestRepository 가 이미 strategy service 에 cross-inject. 정의 = COMPLETED 기준 (FE `STRATEGY_BACKTEST_COUNT_HINT` 가 "완료된 백테스트 수"로 선제 등재돼 있어 문구-데이터 정합).
5. **B2 캐논 복원**: S9 의 "전체+툴팁" 은 state 필터 부재로 인한 잠정치로 재해석 — 소스 신설로 `_KIT.md` §4.6(미체결 수) 복원. `ORDER_FILTER_HINT.navCount` 문구 반전 필수(정직성 연쇄).
6. **A7 축소**: 이력 리스트 화면은 프로토타입 부재로 defer. 기능 격차의 본질 = 리로드 시 스트레스 결과 소실(`useState` 만) → `?backtest_id=&limit=1` 최신 복원(A7-lite)로 해소.
7. **워크트리 정리**: stale 13개 제거 + merged 브랜치 대량 정리. **wf_b2f8516a-320-1/2/3 은 미커밋 변경(pine_v2 na-safe 실험, BL-374/PR #373 계열 잔재) 있어 보류** — 사용자 판단 대기.
8. **평가자 = Claude**: 생성자가 codex 이므로 리뷰어를 Claude 로 교차 (c-port 는 반대 방향). codex read-only 는 최종 누적 diff 1회만.

## 2026-07-23 W-trading — A2·B2 구현 결정

1. **취소 202 계약**: 실제 응답은 `{order_id, state: "submitted", detail: "exchange cancel requested"}` 이며, 200 `OrderResponse` 와 Zod union 으로 구분한다. `apiFetch`가 `Response.ok`를 사용하므로 202 별도 성공 처리는 불필요하다.
2. **취소 toast**: pending 200은 목록 invalidate 뒤 기존 `notifyTransitions`의 cancelled 전이 toast만 사용한다. submitted 202만 「거래소에 취소를 요청했습니다」 정보 toast를 내며, 409은 안내 toast와 주문 prefix invalidate를 함께 수행한다.
3. **nav-count 소스**: `/orders?state=pending&state=submitted&limit=1`의 filtered total을 사용한다. Repository의 목록과 count가 같은 states 조건을 공유해 배지와 원장 집계가 어긋나지 않는다.

## 2026-07-23 통합·게이트 — 환경 함정 3건 (전부 실측)

1. **5433 = ffwpu 재현**: Docker 데몬 기동 시 ffwpu-postgres 가 5433 을 선점해 `make up-isolated` 의 quantbridge-db 바인딩이 실패했다. 세션 한정 오버레이 compose 로 **db 를 5436** 으로 우회(과거 dogfood 레시피와 동일 포트). host 프로세스(uvicorn/alembic/pytest/psql)는 전부 env 오버라이드로 5436 을 본다. `backend/.env.local` 의 5433 은 여전히 남의 DB 를 가리키는 지뢰 — **DB 정체성 프로브(openapi title + psql↔API 동일 row) 없이 오라클 선언 금지**.
2. **3000 = 타 프로젝트 next 서버**: nexus-core FE 가 3000 을 점유 중이라 quantbridge dev 는 밀려나고, e2e/design-canon 이 **엉뚱한 앱을 감사**해 5건 위양성 실패가 났다(27/32). BE 만 정체성 프로브하고 FE 를 생략한 것이 원인. **FE 도 `<title>` 프로브 의무**. 해법 = FE 3100 + BE `FRONTEND_URL=3100` CORS + `PLAYWRIGHT_BASE_URL=http://localhost:3100`. 재조준 후 32/32.
3. **BE pytest 에러 16건 = `TEST_REDIS_LOCK_URL` 미설정**: conftest 기본값이 6379 라 격리 redis(6380)에 닿지 못했다. `TEST_REDIS_LOCK_URL=redis://localhost:6380/3` 로 waitlist 18 전부 그린. full-run 인캔테이션에 포함할 것.

## 2026-07-23 수용 루프 실적 — 적대 평가가 잡은 실버그 3건

- **fp-backtest F-1**: `page.items[0]` 이 스트레스 0건(최빈 케이스)에서 undefined resolve → RQ v5 가 "data is undefined" throw → 상세 진입마다 영구 error + 콘솔 에러, 표면은 멀쩡한 silent failure(§7.3 패턴). `?? null` + 타입 `| null` + 빈 배열 테스트로 수정.
- **fp-optimizer F1**: 워커가 grid 에 `min >= max` 거부를 신설 — BE 계약(min==max 단일점 스윕 허용, schemas.py "min must be <= max")을 깨는 회귀. `min > max` 만 거부 + "작거나 같아야 합니다" 로 정합 + min==max 허용 계약 테스트 잠금.
- **fp-optimizer F2**: exceptions.py:86 "Sprint 54 MVP" 사용자 노출 문구 잔존 → 중립화.
- 교차 구조(codex 생성 ↔ Claude 평가)의 가치 실증 — 3건 전부 워커 자기 게이트는 그린이었다.

## 2026-07-23 e2e 추가 — SSR 프리페치 함정

- `/strategies` 는 HydrationBoundary 서버 프리페치라 **Playwright 라우트 목이 Node-side fetch 를 못 가로챈다**. B1 e2e 는 목 대신 라이브 구조 불변식(열 존재 + 전 행 정수 + 0행이면 실패)으로 전환 — SSR 실경로 검증이라 오히려 정직. 목 기반 스펙을 쓸 땐 대상 페이지가 클라이언트 페치인지 먼저 확인할 것.
- 전략 목록 봉투는 `{items,total,page,limit,total_pages}` 5필드 — 2필드 목은 zod 파싱 실패로 빈 화면이 된다(스펙 1차 실패 원인).
