# API 경계

> **정본:** 각 도메인의 `apps/api/src/<domain>/router.py`와 FastAPI OpenAPI다. 개발 환경에서는 `/openapi.json`·`/docs`·`/redoc`에서 전체 schema를 확인한다. production은 공개를 막을 수 있으므로, 이 문서는 사람이 빠르게 경계를 찾는 지도만 유지한다.

## 진입점

| 경계                          | Router                                             | 기준 경로                                   |
| ----------------------------- | -------------------------------------------------- | ------------------------------------------- |
| 상태 확인·metrics             | `health/router.py`, `main.py`                      | `/health`, `/healthz`, `/livez`, `/metrics` |
| 인증                          | `auth/router.py`                                   | `/api/v1/auth`                              |
| 전략·변환                     | `strategy/router.py`, `strategy/convert/router.py` | `/api/v1/strategies`                        |
| 백테스트                      | `backtest/router.py`                               | `/api/v1/backtests`                         |
| 스트레스 테스트               | `stress_test/router.py`                            | `/api/v1/stress-tests`                      |
| 최적화                        | `optimizer/router.py`                              | `/api/v1/optimizer`                         |
| 거래소 계정·주문·세션·Webhook | `trading/router.py`                                | `/api/v1` 아래 trading route                |
| Waitlist                      | `waitlist/router.py`                               | `/api/v1` 아래 waitlist route               |
| 실시간 브라우저 연결          | `realtime/router.py`                               | `/api/v1/realtime/ws`                       |

## 공통 계약

- 보호된 HTTP 경로는 Better Auth 가 발급한 JWT를 JWKS로 검증하고([ADR-034](../../decisions/034-auth-self-host-better-auth.md)), 소유권 확인은 service 계층이 맡는다. 검증기는 `realtime/auth.py`다.
- 관리자 전용 경로는 별도 router가 아니라 도메인 router 안에 있다 — 현재 `/api/v1/admin/waitlist` 뿐이고 인가는 `waitlist/dependencies.py`의 이메일 화이트리스트다.
- Backtest·Stress Test·Optimizer는 요청에서 직접 실행하지 않고 Celery 작업으로 넘긴다. 정확한 상태 코드·payload는 OpenAPI/schema가 정본이다.
- 애플리케이션 예외는 JSON `detail`에 안정된 `code`를 제공한다. 예상하지 못한 오류도 HTML이나 stack trace 대신 표준 5xx JSON으로 반환한다.
- WebSocket의 인증·메시지 형식은 REST와 별도 계약이다. `realtime/router.py`와 frontend 소비 코드를 함께 바꾼다.

## 계약 파일 — `contracts/openapi/openapi.json`

OpenAPI 산출물이 레포에 **결정적으로 고정**돼 있다(`apps/api/scripts/export_openapi.py`, 키 정렬 + `APP_ENV=development` 강제 — 두 번 돌리면 byte-identical). 소비 경로는 **두 단이다** — `tools/scripts/openapi-poc-filter.py` 가 이 전량 export 에서 PoC 부분집합 `contracts/openapi/poc/openapi.poc.json` 을 뽑고, `apps/web/orval.poc.config.ts` 가 **그 부분집합**을 읽는다([ADR-031](../../decisions/031-api-contract-axis-poc.md)). orval 은 전량 파일을 직접 읽지 않는다.

★**API 를 바꾸면 이 파일을 재생성해야 한다** — `mise run openapi-check` 가 drift 를 막고, CI `backend_static` 잡이 같은 검사를 한다(로컬 게이트 러너는 ADR-037 제로베이스로 철거 — green = 표준 러너 + CI 단일 게이트).

## 갱신 규칙

새 API를 만들거나 route prefix를 바꾸면 router·schema·OpenAPI 테스트를 먼저 바꾼다. 이 문서는 새로운 **도메인 경계 또는 기준 경로**가 생길 때만 갱신한다. 개별 endpoint 목록을 다시 복제하지 않는다.
