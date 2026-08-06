# Archived Refactoring Backlog

> Sprint 59 PR-D 트리아주 결과 — 명백한 Resolved BL + Sprint 16~30 stale follow-up. 1-line table row 만 보존, 상세는 해당 sprint dev-log 참조.
>
> **재활 정책:** archived = 의도적 폐기 또는 stale. 부활 trigger 발생 시 `grep BL-XXX` 후 main BACKLOG 로 row 이동. trigger 미도래지만 의도적 부활 가능성 보존은 [`_deferred.md`](_deferred.md).
>
> **Sprint 59 archive 일자:** 2026-05-13.

## Resolved BL (✅ Status)

| ID      | 제목                                                                  | Sprint Resolved                                                                                            | Dev-log                                                                              |
| ------- | --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| BL-001  | submitted 영구 고착 watchdog                                          | Sprint 15 (2026-05-01)                                                                                     | [sprint15-watchdog](../../dev-log/2026-05-01-sprint15-watchdog.md)                      |
| BL-002  | Day 2 stuck pending order cleanup                                     | Sprint 15 (2026-05-01)                                                                                     | [sprint15-watchdog](../../dev-log/2026-05-01-sprint15-watchdog.md)                      |
| BL-004  | KillSwitch capital_base 동적 바인딩                                   | Sprint 28 Slice 4 PR #108 (2026-05-04)                                                                     | [006-sprint6-design-review-summary](../../decisions/006-sprint6-design-review-summary.md) |
| BL-010  | commit-spy 도메인 확장 (4 도메인 11 spy)                              | Sprint 16 (2026-05-01)                                                                                     | [sprint16-phase0](../../dev-log/2026-05-01-sprint16-phase0-live-and-backfill.md)        |
| BL-011  | Redis lease + heartbeat                                               | Sprint 24a                                                                                                 | —                                                                                    |
| BL-012  | prefork 복귀                                                          | Sprint 24a                                                                                                 | —                                                                                    |
| BL-013  | Auth circuit breaker (1h TTL)                                         | Sprint 24a                                                                                                 | —                                                                                    |
| BL-016  | `__aenter__` first_connect race                                       | Sprint 24a                                                                                                 | —                                                                                    |
| BL-027  | WS state_handler dec winner-only commit-then-dec                      | Sprint 16 (2026-05-01)                                                                                     | [sprint16-phase0](../../dev-log/2026-05-01-sprint16-phase0-live-and-backfill.md)        |
| BL-080  | scan/reconcile/trading prefork-safe (Option C persistent worker loop) | Sprint 18 (2026-05-02)                                                                                     | [sprint18-bl080](../../dev-log/2026-05-02-sprint18-bl080-architectural.md)              |
| BL-081  | `qb_pending_alerts` gauge + `track_pending_alert()`                   | Sprint 19 (2026-05-02)                                                                                     | —                                                                                    |
| BL-083  | `tests/test_migrations.py` 격리 stack 호환                            | Sprint 19 (2026-05-02)                                                                                     | —                                                                                    |
| BL-084  | AST audit module-level asyncio primitive 차단 gate                    | Sprint 19 (2026-05-02)                                                                                     | —                                                                                    |
| BL-085  | `tests/tasks/test_prefork_smoke_integration.py`                       | Sprint 19 (2026-05-02)                                                                                     | —                                                                                    |
| BL-091  | ExchangeAccount.mode dynamic dispatch 3-tuple                         | Sprint 22 (2026-05-03)                                                                                     | —                                                                                    |
| BL-092  | `qb_active_orders` filled/cancelled dec invariant                     | Sprint 21                                                                                                  | —                                                                                    |
| BL-093  | TestOrderDialog success toast + BrokerBadge                           | Sprint 21                                                                                                  | —                                                                                    |
| BL-095  | Backtest 422 inline detail (FE friendly hints)                        | Sprint 21                                                                                                  | —                                                                                    |
| BL-096  | coverage.py supported list 확장 (Partial)                             | Sprint 21 (UtBot×2/DrFX 잔존 → Sprint 58 BL-241에서 처리)                                                  | —                                                                                    |
| BL-097  | interpreter alias ordering correctness                                | Sprint 21                                                                                                  | —                                                                                    |
| BL-098  | strategy.exit coverage/interpreter parity                             | Sprint 23                                                                                                  | —                                                                                    |
| BL-099  | vline coverage/interpreter parity                                     | Sprint 23                                                                                                  | —                                                                                    |
| BL-101  | Makefile up-isolated-build 옵션                                       | Sprint 23                                                                                                  | —                                                                                    |
| BL-102  | Order dispatch snapshot 저장                                          | Sprint 23                                                                                                  | —                                                                                    |
| BL-103  | EXCHANGE_PROVIDER lifespan deprecation warning                        | Sprint 23                                                                                                  | —                                                                                    |
| BL-110a | In-process lease integration test                                     | Sprint 25                                                                                                  | [sprint25-hybrid](../../dev-log/2026-05-03-sprint25-hybrid.md)                          |
| BL-112  | scenario2 실 backtest 실행                                            | Sprint 25                                                                                                  | [sprint25-hybrid](../../dev-log/2026-05-03-sprint25-hybrid.md)                          |
| BL-113  | scenario3 OrderService.execute 정확 args                              | Sprint 25                                                                                                  | [sprint25-hybrid](../../dev-log/2026-05-03-sprint25-hybrid.md)                          |
| BL-114  | pytest-json-report 도입                                               | Sprint 25                                                                                                  | [sprint25-hybrid](../../dev-log/2026-05-03-sprint25-hybrid.md)                          |
| BL-115  | HTML escape full coverage                                             | Sprint 25                                                                                                  | [sprint25-hybrid](../../dev-log/2026-05-03-sprint25-hybrid.md)                          |
| BL-140  | LiveSignalDetail equity curve chart UI                                | Sprint 27 PR #104                                                                                          | —                                                                                    |
| BL-140b | LiveSignalDetail equity curve real value                              | Sprint 28 Slice 3 PR #111                                                                                  | —                                                                                    |
| BL-141  | Backtest UI 활성화 + ts.ohlcv backfill                                | Sprint 28 Slice 2 PR #110                                                                                  | —                                                                                    |
| BL-144  | input step="any" silent submit block fix                              | Sprint 27 PR #105                                                                                          | —                                                                                    |
| BL-150  | Equity chart full migration + MC sign-flip fix                        | Sprint 36 PR #157 (2026-05-06)                                                                             | —                                                                                    |
| BL-152  | `total_trades` PRD parity alias                                       | Sprint 30-γ-BE `04f754d`                                                                                   | —                                                                                    |
| BL-156  | Sprint 31 BL — Surface Trust Recovery 관련                            | Sprint 32 (PR #136)                                                                                        | —                                                                                    |
| BL-163  | Sprint 31 BL                                                          | Sprint 32 (PR #135)                                                                                        | —                                                                                    |
| BL-164  | live-session-form SelectWithDisplayName helper                        | Sprint 33 PR #143                                                                                          | —                                                                                    |
| BL-168  | Sprint 32 Worker A                                                    | Sprint 32 (PR #134)                                                                                        | —                                                                                    |
| BL-169  | Sprint 32 Worker B                                                    | Sprint 32 (PR #133)                                                                                        | —                                                                                    |
| BL-170  | Sprint 32 Worker B-2                                                  | Sprint 32 (PR #133)                                                                                        | —                                                                                    |
| BL-171  | MarkerLayer                                                           | Sprint 32 (PR #138)                                                                                        | —                                                                                    |
| BL-172  | Sprint 32 Worker D                                                    | Sprint 32 (PR #138)                                                                                        | —                                                                                    |
| BL-175  | Buy & Hold 정확 계산 (backend buy_and_hold_curve)                     | Sprint 34 PR #150                                                                                          | —                                                                                    |
| BL-176  | SelectWithDisplayName onClear prop                                    | Sprint 36 PR #157 (2026-05-06)                                                                             | —                                                                                    |
| BL-177  | dense text shorten (visible-range/tooltip/cluster Sprint 35+ 분리)    | Sprint 34 PR #149 (partial)                                                                                | —                                                                                    |
| BL-178  | production OHLCV invalid close root cause                             | Sprint 35 Slice 1a (Docker worker stale, `make up-isolated-build` 워크어라운드)                            | [sprint35-bl178](../../dev-log/2026-05-05-bl178-rootcause-spike.md)                     |
| BL-180  | backtest engine golden oracle (hand-computed)                         | Sprint 35 PR #155                                                                                          | —                                                                                    |
| BL-181  | Docker worker auto-rebuild on PR merge                                | Sprint 38 PR #170                                                                                          | —                                                                                    |
| BL-183  | MC fan chart 4 통계 노출                                              | Sprint 37                                                                                                  | —                                                                                    |
| BL-184  | Equity/BH curve PnL 시작점 정렬                                       | Sprint 37 PR #161                                                                                          | —                                                                                    |
| BL-185  | Pine spot-equivalent sizing                                           | Sprint 37 PR #159                                                                                          | —                                                                                    |
| BL-187  | 백테스트 폼 simplify (leverage/funding 제거)                          | Sprint 37                                                                                                  | —                                                                                    |
| BL-187a | "Spot" 라벨 simplify                                                  | Sprint 37 PR #164                                                                                          | —                                                                                    |
| BL-188  | 백테스트 폼 ↔ Live Settings mirror                                    | Sprint 38 (stage 머지 후 main 반영)                                                                        | —                                                                                    |
| BL-188a | 백테스트 폼 default_qty + Pine override priority                      | Sprint 37 PR #164                                                                                          | —                                                                                    |
| BL-189  | CPU loop on stage @8a23f29 (measurement artifact)                     | Sprint 39                                                                                                  | —                                                                                    |
| BL-200  | pine_v2 STDLIB triple SSOT 단일화 (`_names.py`)                       | Sprint 47 PR #241 (2026-05-09)                                                                             | —                                                                                    |
| BL-201  | pine_v2 Track S/A/M Strategy pattern (`track_runner.py`)              | Sprint 48 PR #245 (2026-05-09)                                                                             | —                                                                                    |
| BL-202  | trading Provider Registry/Factory (`registry.py`)                     | Sprint 47 PR #240 (2026-05-09)                                                                             | —                                                                                    |
| BL-203  | trading service.py god file 분할                                      | Sprint 48 PR #246 (2026-05-09)                                                                             | —                                                                                    |
| BL-204  | trading repository.py god file 분할                                   | Sprint 48 PR #244 (2026-05-09)                                                                             | —                                                                                    |
| BL-205  | trading OrderStatus Literal triple SSOT (intentional doc only)        | Sprint 47 codex G.0 2차                                                                                    | —                                                                                    |
| BL-206  | frontend cross-page primitive cleanup (Skeleton/EmptyState variant)   | Sprint 47 PR #239 (2026-05-09)                                                                             | —                                                                                    |
| BL-219  | Cost Assumption Sensitivity 본격                                      | Sprint 50 (2026-05-10)                                                                                     | —                                                                                    |
| BL-220  | 진짜 Param Stability — pine_v2 input override                         | Sprint 51 PR `feat/sprint51-bl220-be-engine` (2026-05-11)                                                  | —                                                                                    |
| BL-221  | alembic SAEnum + StrEnum case mismatch                                | Sprint 50 hotfix `da7e52e` (2026-05-10)                                                                    | —                                                                                    |
| BL-222  | parent backtest config 손실 fix (config_mapper)                       | Sprint 52 Slice 1 `1923bb4` (2026-05-11)                                                                   | —                                                                                    |
| BL-223  | FE Param Stability form + wire-up                                     | Sprint 52 Slice 4+5 (2026-05-11)                                                                           | —                                                                                    |
| BL-224  | FE schemas.ts param_grid superRefine                                  | Sprint 52 Slice 3 `29363e7` (2026-05-11)                                                                   | —                                                                                    |
| BL-225  | `run_param_stability` InputDecl type validation                       | Sprint 52 Slice 2 `146fab9` (2026-05-11)                                                                   | —                                                                                    |
| BL-226  | FE `isFiniteDecimalString()` BE grammar parity                        | Sprint 53 PR #257 (2026-05-11)                                                                             | —                                                                                    |
| BL-227  | Cost Assumption Sensitivity `run_grid_sweep` 위임                     | Sprint 54 Slice 1 (2026-05-12)                                                                             | —                                                                                    |
| BL-228  | `run_grid_sweep` N-dim 확장                                           | Sprint 54 Slice 1 (2026-05-12)                                                                             | —                                                                                    |
| BL-229  | backtest/optimizer schemas StrictDecimalInput 통일                    | Sprint 54 Slice 2+4 (2026-05-12)                                                                           | —                                                                                    |
| BL-230  | Optimizer `error_message` public/internal 분리 + truncate             | Sprint 54 Slice 2+3 (2026-05-12)                                                                           | —                                                                                    |
| BL-231  | Bayesian/Genetic grammar ADR (코드 변경 0)                            | Sprint 54 Slice 5 (2026-05-12) — [ADR-013](../../dev-log/2026-05-12-sprint54-bayesian-genetic-grammar-adr.md) | —                                                                                    |
| BL-232  | Bayesian executor 본격 (scikit-optimize ask-tell)                     | Sprint 55 Slice 1-5 (2026-05-11)                                                                           | [sprint55-master](../../dev-log/2026-05-11-sprint55-master.md)                          |
| BL-233  | Genetic executor 본격 (self-impl GA)                                  | Sprint 56 Slice 1-6 (2026-05-11)                                                                           | —                                                                                    |
| BL-234  | Bayesian prior=normal + one_hot + Genetic roulette                    | Sprint 57 (2026-05-11)                                                                                     | [sprint57-close](../../dev-log/2026-05-11-sprint57-close.md)                            |
| BL-237  | Optimizer optimizer_heavy queue + cap 100                             | Sprint 57 (2026-05-11)                                                                                     | [sprint57-close](../../dev-log/2026-05-11-sprint57-close.md)                            |
| BL-241  | Pine TA 확장 (ta.wma/hma/bb/cross/mom/obv+fixnan)                     | Sprint 58 PR #264 (2026-05-11)                                                                             | [sprint58-close](../../dev-log/2026-05-11-sprint58-close.md)                            |
| BL-242  | strategy.equity + display NOP                                         | Sprint 58 PR #264 (2026-05-11)                                                                             | [sprint58-close](../../dev-log/2026-05-11-sprint58-close.md)                            |
| BL-243  | 거래 목록 UTC 라벨                                                    | Sprint 58 PR #264 (2026-05-11)                                                                             | [sprint58-close](../../dev-log/2026-05-11-sprint58-close.md)                            |

## Stale / Cancelled BL

| ID     | 제목                          | Reason                              | Sprint 결정                         |
| ------ | ----------------------------- | ----------------------------------- | ----------------------------------- |
| BL-166 | uvicorn `.env*` watch include | watchfiles glob noop 발견 후 Cancel | Sprint 34                           |
| BL-082 | 1h prefork soak gate          | 본인 dogfood 자연 측정으로 대체     | Sprint 19 (이연됐다가 자연 archive) |

## P2/P3 Stale (Sprint 16~30 follow-up, 발생 trigger 미도래 후 archive)

> 본 BL 들은 등재 후 trigger 도래 없이 1+ sprint 누적 = stale. trigger 발생 시 부활 가능.

| ID      | 제목                                                  | Priority      | 원래 trigger                                                                                              |
| ------- | ----------------------------------------------------- | ------------- | --------------------------------------------------------------------------------------------------------- |
| BL-017  | WebCrypto error 처리                                  | P1            | dogfood HTTP 환경 발견 시                                                                                 |
| BL-018  | Strategies/Accounts query loading/error UX            | P1            | dogfood Day 4+ 발견 시                                                                                    |
| BL-019  | NEXT_PUBLIC_API_URL trailing slash                    | P1            | Vercel 프로덕션 배포 직전                                                                                 |
| BL-020  | webhook 응답 size cap                                 | P1            | on-demand 대용량 trace 노출                                                                               |
| BL-021  | sessionStorage hardening                              | P1            | Beta 5명 onboarding 후                                                                                    |
| BL-030  | CI lupa C ext 빌드 검증                               | P2            | on-demand                                                                                                 |
| BL-031  | Redis Sentinel/Cluster 검토                           | P2            | Redis 한계 도달                                                                                           |
| BL-032  | cardinality allowlist 조정                            | P2            | 프로덕션 ccxt 예외 실측 후                                                                                |
| BL-033  | issue 중복 방지 auto-label                            | P2            | dogfood 1주 issue 중복 발견                                                                               |
| BL-034  | slowapi 0.2.x major upgrade                           | P2            | H2 말 (~2026-06-30)                                                                                       |
| BL-035  | Phase B Grafana Cloud dashboard                       | P2            | dogfood metric 식별 후                                                                                    |
| BL-036  | dogfood 통합 dashboard `/dashboard/today`             | P2            | "화면 부족" 자각 시                                                                                       |
| BL-037  | Coverage Analyzer AST 정밀화                          | P2            | Sprint Y2 또는 false-positive 보고 시                                                                     |
| BL-038  | P-3 중복 실행 통합                                    | P2            | Sprint 16 정리 sprint 시                                                                                  |
| BL-039  | `qb_redis_lock_pool_healthy` startup race             | P2            | dogfood false alert 1건 이상                                                                              |
| BL-040  | Path γ — PyneCore transformers 이식                   | P2            | H2~H3 path 평가 시                                                                                        |
| BL-041  | Path δ — Bulk stdlib top-N                            | P2            | dogfood 피드백 기반 우선순위                                                                              |
| BL-042  | Onboarding 성공률 metric                              | P2            | Beta 5명 onboarding 후                                                                                    |
| BL-043  | waitlist Resend 미설정 graceful fallback              | P2            | Beta 오픈 직전                                                                                            |
| BL-086  | AST audit factory function detection                  | P3            | Sprint 19 G.2 P2                                                                                          |
| BL-087  | AST audit target glob                                 | P3            | Sprint 19 G.2 P2                                                                                          |
| BL-088  | `drain_pending_alerts()` helper                       | P3            | Sprint 19 G.2 P2                                                                                          |
| BL-089  | `qb_pending_alerts` Grafana alert wire-up             | P2 partial    | Sprint 30 partial Resolved                                                                                |
| BL-090  | `tests/db_url.py` 분리                                | P3            | Sprint 19 G.2 P3                                                                                          |
| BL-094  | webhook secret sessionStorage TTL vs UX               | P3            | 정책 결정 후                                                                                              |
| BL-104  | strategy.exit full PendingExitOrder                   | P2            | Sprint 23 BL-098 후속                                                                                     |
| BL-105  | OrderService.execute account fetch transaction        | P2            | Sprint 23 G.2 P2                                                                                          |
| BL-106  | Alembic idempotency 강화                              | P3            | Sprint 23 G.2 P2                                                                                          |
| BL-107  | .husky/pre-push 가 default 5432 DB                    | P2            | Sprint 23 push 발견                                                                                       |
| BL-108  | `_ws_circuit_breaker.record_network_failure` 비원자성 | P3            | Sprint 24a G.2 P2                                                                                         |
| BL-109  | `test_first_connect_timeout` 실제 timeout path 미검증 | P3            | Sprint 24a G.2 P2                                                                                         |
| BL-110b | Real Celery prefork SIGTERM integration test          | P2            | Sprint 25 G.2 P2                                                                                          |
| BL-111  | WS circuit breaker `reset_circuit` admin path         | P3            | Sprint 24a G.2 P2                                                                                         |
| BL-116  | CI workflow_dispatch authed E2E                       | P2            | Sprint 25 G.2 P2                                                                                          |
| BL-117  | Clerk emailAddress 방식 마이그레이션                  | P2            | Sprint 25 G.2 P2                                                                                          |
| BL-118  | playwright.config baseURL 통합                        | P3            | Sprint 25 G.2 P2                                                                                          |
| BL-119  | API_ROUTES URL predicate                              | P3            | Sprint 25 G.2 P2                                                                                          |
| BL-120  | leak guard fail-on-leak                               | P2            | Sprint 25 G.2 P2                                                                                          |
| BL-121  | production guard host allowlist                       | P2            | Sprint 25 G.2 P2                                                                                          |
| BL-122  | pytest-json-report uv-aware detect                    | P3            | Sprint 25 G.2 P2                                                                                          |
| BL-123  | mkstemp fd leak fix                                   | P3            | Sprint 25 G.2 P2                                                                                          |
| BL-124  | run_auto_dogfood subprocess timeout                   | P2            | Sprint 25 G.2 P2                                                                                          |
| BL-125  | report 파일명 timestamp + symlink                     | P3            | Sprint 25 G.2 P2                                                                                          |
| BL-126  | FakeOrderDispatcher edge case                         | P2            | Sprint 25 G.2 P2                                                                                          |
| BL-127  | BL-110a xdist 격리                                    | P3            | Sprint 25 G.2 P2                                                                                          |
| BL-128  | trading-ui scenario 3 KS bypass disabled assert       | P2            | Sprint 25 G.2 P1 partial                                                                                  |
| BL-129  | ANSI/control seq HTML 처리                            | P3            | Sprint 25 G.2 P3                                                                                          |
| BL-137  | 신규 strategy trading settings UI                     | P2            | Sprint 27 hotfix / Beta prereq                                                                            |
| BL-138  | Live Sessions list two-line layout polish             | P3            | Sprint 27 polish                                                                                          |
| BL-139  | LiveSignalDetail aggregation scope                    | P3            | Day 3 정정 후 우선도 낮음                                                                                 |
| BL-142  | ts.ohlcv daily refresh task                           | P2            | Sprint 29+                                                                                                |
| BL-143  | LiveSignal equity_curve JSONB compaction              | P2            | Sprint 30+ (1000+ entry)                                                                                  |
| BL-146  | 메타-방법론 정책 4종 영구 규칙 승격                   | P2            | Sprint 29+ Stage 6 (LESSON-037~040 영구 승격 완료, BL closed)                                             |
| BL-147  | Bybit Demo integration test CI wire-up                | P2            | Sprint 29+                                                                                                |
| BL-151  | golden_backtest expected 재생성 (24 신규 필드)        | P3            | pine_v2 strategy.exit 지원 시 (BL-022 sibling)                                                            |
| BL-153  | Strategy DevOps 카테고리 메시징                       | P3 (실험 tag) | H3 가격 실험 단계                                                                                         |
| BL-182  | Worker container code version monitoring              | P2            | Sprint 37+ (BL-181 sibling, BL-181 Resolved 후 deferred)                                                  |
| BL-190  | PDF export                                            | P2            | 외부 사용자 요청 / 인쇄 use case 발견 시 (Active 유지 권고지만 trigger 미도래 = archive 1차 후 부활 권고) |
| BL-191  | share view endpoint rate-limit                        | P2            | Beta 본격 진입 시                                                                                         |
| BL-192  | backtest status server filter                         | P2            | Beta 본격 진입 시                                                                                         |
| BL-193  | `make be-test` env auto-inject                        | P2            | Sprint 42 발견 (Sprint 57 BL-240 으로 대체 — 압축 path)                                                   |
| BL-194  | favicon.ico 404 (dev only)                            | P2            | Sprint 42 발견 (polish 차원 사소)                                                                         |
| BL-238  | lint-staged backend `ruff --fix` exit 0 silent skip   | P3            | Sprint 56 prereq (Resolved Sprint 56)                                                                     |
| BL-239  | pre-push hook 에 `uv run mypy src/` 추가              | P3            | Sprint 56 prereq (Resolved Sprint 56)                                                                     |
| BL-240  | pre-push hook env vars 자동 source `.env.local`       | P3            | Sprint 56 prereq (Resolved Sprint 56)                                                                     |

## P3 전부 (nice-to-have, 컨벤션 정합)

| ID     | 제목                                             | 원래 trigger                                |
| ------ | ------------------------------------------------ | ------------------------------------------- |
| BL-050 | `PINE_ALERT_HEURISTIC_MODE` env ADR              | 신규 sprint 정리 시 on-demand               |
| BL-051 | zod@4 import 경로 정정                           | Sprint 16 cleanup                           |
| BL-052 | `.uuid()` → `z.uuid()` migration                 | BL-051 와 묶음                              |
| BL-053 | strategies/{id}/edit loading/error.tsx           | FE Polish bundle                            |
| BL-054 | strategy-list useSuspenseQuery 전환              | FE Polish bundle                            |
| BL-055 | "use client" 27개 presentational 서버 컴포넌트화 | RSC 성능 측정 후                            |
| BL-056 | Termly → 한국 변호사 검토                        | H2 말 (~2026-06-30) (외부 비용 $500~$1,500) |
| BL-057 | requirements.md §4.1 명시화                      | Sprint 16 docs sync                         |

## 2026-08-06 문서 대개편 대강등 (94 Resolved)

> docs 대개편(fix-doc 브랜치)에서 `docs/backlog.md` 의 RESOLVED 94건을 일괄 강등.
> **전문은 이 변경 커밋의 부모 리비전** `git show <parent>:docs/backlog.md` 에 있다(각 섹션 `### BL-NNN`).

| ID | P | 제목 | Resolved 근거 |
| --- | --- | --- | --- |
| BL-308 | P1 | trading websocket subsystem test coverage boost (4% → ≥70%) | W3, 2026-06-29 |
| BL-309 | P2 | trading 핵심 dispatch 모듈 test 추가 (registry / webhook / fees, 0% → ≥80%) | W3, 2026-06-29 |
| BL-361 | P1 | Pine Trust Layer 누출 — coverage SUPPORTED ↔ interpreter dispatch SSOT drift (28 symbols) | — |
| BL-362 | P2 | live 경로 coverage↔interpreter divergence silent swallow observability | 2026-07-25, `stage/money-path-accuracy` |
| BL-365 | P2 | `trigger_direction_for` / `map_exit_kind` dead-code + 서버 미배선 (standalone-trigger 방향 latent gap) | 2026-07-27, `feat/live-conditional-entry` |
| BL-374 | P2 | pine_v2 interpreter na-semantics — `x/0` · `math.sqrt(-1)` 등 raw Python 예외를 Pine `na` 로 정규화 | 2026-06-29, `fix/pine-374-na-semantics`, commit `2cd1313` |
| BL-376 | P3 | pine_v2 na/inf 소비 사이트 robustness — na→ta.\* length / na→strategy.entry qty / inf→math.floor·ceil·round | 2026-06-30, `fix/pine-376-na-inf` |
| BL-378 | P1 | ` 줄 · 헤더 스프린트 변경 기록(`docs/backlog.md:29`) · 인덱스 표 행 ✅. | 2026-06-30, `fix/pine-378-atr-wilder` |
| BL-388 | P2 | BacktestMetrics 24-field 가 4곳 평행 정의 (engine dataclass ↔ schema ↔ serializer ↔ `_to_detail`) — field-parity 무검… | — |
| BL-391 | P3 | backtest trades→equity→metrics 3단 reconciliation 불변식 암묵 + cross-stage oracle 부재 (test-first) | 2026-08-03, backtest-metric-oracle |
| BL-398 | P2 | Sharpe TV convention 정렬 (달력월 수익률 + RFR 2%/yr) — optimizer objective 영향 분석 동반 | — |
| BL-401 | P2 | ` 줄 · 헤더 스프린트 변경 기록(`docs/backlog.md:25`) · 인덱스 표 행 ✅. | 2026-07-23, `stage/functional-parity` |
| BL-402 | P2 | ` 줄 · 헤더 스프린트 변경 기록(`docs/backlog.md:25`) · 인덱스 표 행 ✅. | 2026-07-23, 구조 소멸 |
| BL-404 | P1 | watchdog `fetch_order` Bybit 전면 실패 — ccxt `acknowledged` 게이트 미대응 + futures 심볼 카테고리 미정규화 (라이브 주문 submitted 영구 … | 2026-07-05, `fix/trading-bl404-fetch-order-acknowledged` |
| BL-407 | P3 | ` 줄 + `**해소 (2026-07-13):**` 문단(실 리포트 스크린샷 육안 검증 PASS). | 2026-07-13, PR #433 `stage/fe-react-audit` |
| BL-411 | P3 | ` 줄 · 헤더 스프린트 변경 기록(`docs/backlog.md:25`, "지원 kind 목록 `OptimizationKind` enum 파생"). | 2026-07-23, `stage/functional-parity` |
| BL-416 | P3 | 주문취소 FE polish 팩 — 행별 disabled(현재 전역 `isPending` 으로 전 행 잠김) + 비-409 에러 무피드백 + 테스트 mock 의 ACTIVE_ORDER_STATES … | 2026-07-24 trading-surface-pack |
| BL-417 | P2 | ` 줄 · `docs/archive/dev-log/index-full-2026-08-02.md` (opspack-ws2 "BL-417 drop"). | 2026-07-24, `stage/opspack-ws2` |
| BL-418 | P3 | ` 줄 · `docs/archive/dev-log/index-full-2026-08-02.md` (opspack-ws2 "payload 계약"). | 2026-07-24, `stage/opspack-ws2` |
| BL-419 | P3 | ` 줄 · `docs/archive/dev-log/index-full-2026-08-02.md` (opspack-ws2 정비 팩 6종). | 2026-07-24, `stage/opspack-ws2` |
| BL-421 | P2 | ` 줄 · `docs/archive/dev-log/index-full-2026-08-02.md` (opspack-ws2 "pending 시맨틱"). | 2026-07-24, `stage/opspack-ws2` |
| BL-422 | P3 | ` 줄 · `docs/archive/dev-log/index-full-2026-08-02.md` (opspack-ws2 정비 팩 6종). | 2026-07-24, `stage/opspack-ws2` |
| BL-423 | P3 | 비활성(과거) 세션의 진단 정보를 UI 로 열 수 없음 — `/live-sessions` 가 active 전용 | 2026-07-30 conditional-entry-alignment |
| BL-425 | P3 | 예상된 alert-rules 409(중복 활성 규칙)가 브라우저 콘솔 error 로 노출 | 2026-07-24 trading-surface-pack |
| BL-431 | P2 | 코크핏 §03 열린 포지션 표 TP/SL·청산 액션 열 미렌더 — API 부재 | 2026-07-24 trading-surface-pack |
| BL-432 | P3 | 잔고/포지션 useQueries select 콜백이 렌더마다 새 클로저 | 2026-07-24 trading-surface-pack |
| BL-433 | P3 | WS subscribe negative-ack 관측이 warning 로그만 — metric counter 부재 + BL-423 연계 | 2026-07-24 trading-surface-pack, metric 부분 |
| BL-435 | P3 | 수동 청산 후 §03 flat 반영 지연 — WS 미연결 창에서 캐시 TTL+폴 지연(~15-30s) | 2026-07-25 close-completeness |
| BL-436 | P3 | 청산 create_order 가 settings.margin_mode 로 set_margin_mode — 포지션 실제 mode 불일치 시 실패 가능 | 2026-07-25 close-completeness |
| BL-442 | P3 | 주문 원장 CSV 내보내기에 손익 출처(거래소 확정/추정) 미표기 | 2026-07-25, `stage/exit-attribution` |
| BL-443 | P2 | 체결되지 않은 주문의 pine_v2 추정 손익이 원장·CSV 에 노출됨 | 2026-07-25, `stage/exit-attribution` |
| BL-444 | P1 | loss-limit 알림이 `live_signal_events` 조인이라 거래소 확정 손익을 보지 못함 | 2026-07-25, `stage/exit-money-path` |
| BL-445 | P2 | 세션 에쿼티 커브가 `(strategy, account)` 튜플 스코프라 비활성 세션끼리 커브를 공유 | 2026-07-25, `stage/exit-money-path` |
| BL-454 | P2 | 세션 등록·TV 웹훅 어느 쪽도 심볼을 정규화하지 않아 두 자유 문자열이 세션 스코프에서 어긋난다 | 2026-07-26, `stage/money-path-finish` |
| BL-457 | P2 | `classify_exit` 의 `ours` 는 실제 매칭이 아니라 orderLinkId 가 UUID 로 파싱되는지만 본다 | 2026-07-26, `stage/money-path-finish` |
| BL-461 | P3 | `_periodic_returns` daily fallback 이 sub-daily 봉을 "1 bar = 1 day" 로 센다 (resample 부재) | 2026-08-03, backtest-metric-oracle |
| BL-464 | P2 | `attribute_exit` 이 거래소 원문 심볼과 우리 canonical 심볼을 비교해 `inferred` 귀속이 구조적으로 죽어 있었다 | 2026-07-26, `stage/money-path-finish` |
| BL-465 | P1 | `_periodic_returns` 가 음수 자본을 걸러내지 않아 파산한 실행에 양수 위험조정수익이 붙었다 | 2026-07-26, `stage/dogfood-restore` |
| BL-467 | P1 | `backend-optimizer-heavy` 에 OHLCV 설정 3종이 없어 모든 optimizer 실행이 실패했다 | 2026-07-26, `stage/dogfood-restore` |
| BL-473 | P1 | Bybit private WS 인증 `expires` 창이 +1s 라 왕복 지연에 먹혀 라이브 체결 스트리밍이 죽어 있었다 | 2026-07-26, `stage/dogfood-restore` |
| BL-474 | P2 | 테스트 주문 다이얼로그가 라이브 경로와 **다른 시장**으로 나간다 (spot vs linear perp) | 2026-07-26, `feat/bl-474-webhook-ingress-parity` |
| BL-478 | P1 | stop-entry 전략은 라이브에서 **진입이 구조적으로 절대 나가지 않는다** — 청산만 나가서 매번 110017 | 2026-07-27, `feat/live-conditional-entry` |
| BL-479 | P1 | 라이브 경로에 사이징이 배선돼 있지 않다 — `compute_qty()` 가 항상 `1.0`, `position_size_pct` 는 읽히지 않는다 | 2026-07-26, `feat/live-entry-wiring` |
| BL-480 | P2 | `local_only` 발산이 빈 포지션 표에서 렌더되지 않아 사용자에게 숨겨진다 | 2026-07-26, `feat/bl-474-webhook-ingress-parity` |
| BL-481 | P2 | `sessions_allowed` 가 라이브에 미배선 — 거래 시간대를 제한해도 라이브는 24 시간 진입한다 | 2026-07-26, `feat/live-engine-parity` |
| BL-482 | P3 | `pyramiding` cap 이 라이브에 미배선 — 같은 전략이 백테스트는 cap, 라이브는 무제한 중첩 | 2026-07-26, `feat/live-engine-parity` |
| BL-483 | P1 | `leverage` 가 라이브 엔진에 미배선 — 증거금 게이트와 청산가 모델이 L=1 로 no-op | 2026-07-26, `feat/live-engine-parity` |
| BL-484 | P2 | 세션 자동 중단 **사유**가 화면에 남지 않는다 — 알림 채널로만 나가고 DB 에 없다 | 2026-07-30 conditional-entry-alignment · 마이그레이션 1 |
| BL-486 | P1 | 라이브 사이징 equity 가 **300바 롤링 창**에 따라 변한다 — 같은 신호가 볼 때마다 다른 수량 | 2026-07-26, `feat/live-engine-parity` |
| BL-487 | P3 | `test_get_pool_safe_across_event_loops` 가 `id()` 재사용에 취약 — 전체 스위트에서 random RED | 2026-07-26, `feat/live-engine-parity` |
| BL-488 | P1 | 평가 갭이 orphan close 를 만든다 | 2026-07-27, `feat/live-conditional-entry` |
| BL-495 | P3 | `/orders` 페이저가 좁은 폭에서 가로 오버플로 | 2026-07-27, `feat/live-conditional-entry` |
| BL-498 | P2 | 활성 세션이 없으면 거래소 포지션을 화면에서 보지도 닫지도 못한다 | 2026-07-27, `feat/live-conditional-hardening` |
| BL-500 | P2 | 거래소에서 사라진 `submitted` 조건부 주문을 DB 행만으로 resting 이라 오인한다 | 2026-07-27, `feat/live-conditional-hardening` |
| BL-501 | P3 | 같은 거래소 계정을 가리키는 API 키가 둘이면 포지션이 중복되고 read-only 키에도 청산 버튼이 붙는다 | 2026-07-28, `feat/live-ops-hygiene` |
| BL-502 | P3 | 세션 표와 계정 표의 청산 버튼에 공유 lock 이 없다 | 2026-07-28, `feat/live-ops-hygiene` |
| BL-503 | P2 | 제출 중단·유령 조건부 진입 행을 아무도 치우지 않는다 | 2026-07-28, `feat/live-ops-hygiene` |
| BL-506 | P2 | worker 프로세스의 Prometheus metric 이 스크레이프되지 않아 gauge 규율이 전부 관측 불가다 | — |
| BL-511 | P1 | ★조건부 진입의 **절반이 거래소에 거절된다** — stale 기준가로 인한 매 tick 재시도 루프, 백테스트↔라이브 조용한 발산 | 2026-07-28, `feat/live-entry-parity` |
| BL-512 | P2 | 계측이 "우리가 하려던 것" 만 세고 "거래소가 한 것" 은 안 센다 — 거절 미계상 · 낙관적 placed · **정상 체결이 error 카운터** | 2026-07-28, `feat/live-entry-parity` |
| BL-526 | P2 | ★**라이브 실적이 백테스트 기대치와 맞는지 화면에서 물을 수 없다** — 패리티가 진입까지만 증명됐다 | 2026-07-28, live-outcome-parity |
| BL-530 | P1 | ★엔진이 청산했다고 본 것의 71% 가 거래소에서 확정되지 않는다 | 2026-07-28, live-close-completeness |
| BL-535 | P1 | ★**백테스트는 스팟 봉으로 perp 전략을 검증한다** — 라이브만 계기를 맞춰 두 축이 갈렸다 | 2026-08-06 backtest-reality-gap |
| BL-536 | P1 | 진입 유실 채널 5종을 재측정하고, 그 크기로 설계 여부를 판단한다 | 2026-08-01, entry-completeness-rejudgement |
| BL-537 | P1 | 활성 세션이 없을 때 고아 포지션을 앱에서 청산할 수 없다 | 2026-07-29, live-orphan-close |
| BL-542 | P3 | 계정 포지션 표의 절단 경고가 실제 절단 없이 상시 발화한다 | 2026-08-01, silent-surface-honesty |
| BL-543 | P1 | 재생 구간 포지션이 세션 시작부터 `engine_only` 발산을 만든다 | 2026-07-30, engine-exchange-alignment |
| BL-544 | P1 | 거래소의 조건부 진입 체결을 엔진 재생이 놓쳐 공백 후 세션이 중단된다 | 2026-07-30, conditional-entry-alignment |
| BL-549 | P2 | ★`final-gates.sh` 를 커밋 전에 돌리면 게이트 대부분을 skip 하고도 그럴듯한 PASS 표를 낸다 | 2026-07-30 live-entry-completeness |
| BL-552 | P2 | ★`fleet-dispatch.sh` 가 프롬프트 미제출을 성공으로 보고한다 — 워커가 지시를 입력창에 담은 채 `idle` 로 멈춘다 | 2026-07-30 live-entry-completeness |
| BL-554 | P3 | (P3) pre-push 훅이 **푸시 대상 ref 가 아니라 현재 브랜치**를 봐서 원격 브랜치 삭제까지 막는다 | 2026-07-30 live-entry-completeness |
| BL-555 | P3 | (P3) `stage/*` 가 이 레포의 통합 브랜치 관례인데 pre-push 훅 화이트리스트에 없다 | 2026-07-30 live-entry-completeness |
| BL-560 | P1 | 거래소 terminal 체결을 확인하고도 원장에 write-back하지 않아 반전 청산이 어긋난다 | 2026-08-01, conditional-fill-visibility |
| BL-561 | P2 | 구조화 로그의 `extra` 필드가 렌더되지 않아 진단 증거가 소실된다 | 2026-08-01, conditional-fill-visibility |
| BL-562 | P2 | 조건부 진입의 반전 계측이 등재 시점 포지션만 본다 | 2026-07-31, instrument |
| BL-563 | P3 | bracket outcome이 게이트 뒤 요청을 기준으로 집계돼 공급 여부를 오분류한다 | 2026-07-31, instrument |
| BL-566 | P2 | (Title 줄 없음) | — |
| BL-569 | P3 | (Title 줄 없음) | — |
| BL-570 | P2 | 무편집 `설정 저장`이 요청·토스트·필드 오류 없이 막힌다 | 2026-08-01, silent-surface-honesty |
| BL-571 | P3 | enum 밖 세션 종료 사유가 원장·화면·콘솔을 오염한다 | 2026-08-01, silent-surface-honesty |
| BL-572 | P3 | 동일 세션의 표·카드 상태 라벨이 다르다 | 2026-08-01, silent-surface-honesty |
| BL-576 | P2 | (Title 줄 없음) | — |
| BL-577 | P2 | (Title 줄 없음) | — |
| BL-579 | P2 | (Title 줄 없음) | — |
| BL-583 | P2 | (Title 줄 없음) | — |
| BL-585 | P3 | (Title 줄 없음) | 2026-08-03 soak-divergence-root |
| BL-587 | P3 | (Title 줄 없음) | 2026-08-03 soak-divergence-root |
| BL-588 | P3 | (Title 줄 없음) | 2026-08-03 soak-divergence-root |
| BL-589 | P1 | (Title 줄 없음) | 2026-08-03 soak-divergence-root |
| BL-590 | P1 | (Title 줄 없음) | 2026-08-03 breach-rejection-recovery |
| BL-594 | P2 | (Title 줄 없음) | 2026-08-06 night-watch |
| BL-595 | P1 | (Title 줄 없음) | 2026-08-05 conditional-stop-ownership, `stage/conditional-stop-owners… |
| BL-596 | P2 | (Title 줄 없음) | 2026-08-05 gate596 |
| BL-597 | P2 | (Title 줄 없음) | 2026-08-06 fix/bl597-e2e-table-locator |
