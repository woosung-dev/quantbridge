<!-- tier-c 스프린트(Tier C 4종 + WS Tier 1)의 작업 항목·게이트 추적 체크리스트 (SSOT) -->

# tier-c 체크리스트

> 스프린트 정본: `~/.claude/plans/tier-c-squishy-pebble.md` · 운영 계약: [`operating-contract.md`](operating-contract.md) · 결정 기록: [`context-notes.md`](context-notes.md)
> 기준 커밋: main @ `16c8f20` → `stage/tier-c`

## 0. 범위 (사용자 확정 2026-07-24)

- A안: 펀딩 노출완성+prior 해제 / 포지션 대조 / 알림 규칙 / WS Tier 1 (주문·킬스위치·세션 push, 폴링=SSOT).
- WS Tier 2 후속. 알림 실수신 검증 이연(채널 미세팅 — mock 까지).

## 1. 작업 항목

### W1 — 병렬 4기

- [x] **tc/funding-be (축3 A+B, M)** — 엔진 funding 1회 계산 호이스팅(`funding_costs` kwarg 병존, oracle 9건 byte-identical) + `total_funding` 4-site(①BacktestMetrics ②BacktestMetricsOut+serializer ③serializers 왕복 — FE zod ④는 tc/funding-fe) + oracle T1~T7 + `types.py:48` 주석 교정 + backfill 태스크(`trading.backfill_funding_rates`, 페이지네이션+`_store_rows` 추출+멱등) + beat SOL + B1~B5 테스트.
- [x] **tc/optimizer-fe (축3 D, S)** — normal prior option 해제 + legend + `BayesianRowSchema` E1(normal+log_scale 거부) + F5~F6 + BE `bayesian.py` stale docstring 2곳.
- [x] **tc/position-be (축2 S1, M)** — `PositionSnapshot`+`fetch_open_positions`(hedge 2건 반환) + `PositionService`(supported=false 정직 분기 + Redis 15s 캐시 + snapshot diff verdict 6종) + `GET /live-sessions/{id}/positions` + 스키마 + 테스트(verdict 6종·ownership 404·503·캐시).
- [x] **tc/realtime-be (축1 S0+S1, M)** — `src/realtime/`(router `/api/v1/realtime/ws`·manager·schemas·auth) + `authenticate_clerk_token` 추출 + main.py lifespan + Origin 4403/auth 4401/상한 테스트 (starlette TestClient).

### W2 — 직렬~부분 병렬

- [x] **tc/alerts-be (축2 S2, L)** — `trading.alert_rules` 테이블(String+StrEnum, partial unique) + alembic 1건 + CRUD 3본 + `alerting.py` send_rule_alert(Telegram 최초 배선) + beat `alert_rules.evaluate_loss` 300s + giveup 훅 2곳 + dedupe + 테스트(commit-spy·409·채널 라우팅·throttle·giveup 회귀).
- [x] **tc/publish-be (축1 S2, M)** — `realtime_publisher.py`(no-raise) + 발행 5지점(state_handler user_id 주입 / tasks/trading 3곳 / kill_switch / live_signal) + commit-후-1회-발행 spy 테스트.
- [x] **tc/funding-fe (축3 C, S+)** — 체크박스 register+활성화+문구(캐논 이탈 주석) + FE zod `total_funding` + assumptions-card "총 펀딩" 행+tooltip 동적 + report-shell + F1~F4.
- [x] **tc/realtime-fe (축1 S3, M)** — `lib/ws-client.ts` + `features/realtime/`(store scalar·handlers·schemas·RealtimeBridge) + dashboard-shell mount + vitest(백오프·auth·invalidate 매핑).

### W3 — 통합 FE

- [x] **tc/cockpit-fe (축2 S3 + 축1 S4, M)** — `SessionDiagnostics({session})` 배선(포지션 30s 폴링 훅·알림 규칙·실시간 스트림 status) + `DiagnosticCard` action prop + `features/alert-rules/` 모듈 + `SessionDiagnostics.test.tsx` 재작성 + authed spec 갱신(+testMatch 등재).

### W4 — 오케스트레이터

- [x] 통합 게이트 직렬 재현 (아래 §게이트 표)
- [x] codex read-only 최종 누적 diff 리뷰 1회 — 프레임 0 / MAJOR 2(해소) / MINOR 2(1 해소+1 BL)
- [x] backfill 실행(BTC/ETH/SOL × 2024-01-01~) + psql 커버리지 검증 — 3심볼×2804행·8h 갭 0
- [x] Opus MCP dogfood — V1~V5 전 항목 기능 PASS + 펀딩 3점 오라클 psql 일치(71.8206952…) + cancel 실거래소 왕복 2건 cancelled + WS 101 실측. 발견 = BL-421/422 + beat /data 권한 함정
- [ ] 문서 3종 갱신 + TODO.md + BL 등재 → push + stage→main PR

## 2. 게이트 추적

| 게이트                                        | baseline (재측정 실측)                                    | 목표                          | 실측                                               |
| --------------------------------------------- | --------------------------------------------------------- | ----------------------------- | -------------------------------------------------- |
| FE vitest                                     | **983 passed (171 파일)** ✅ 2026-07-24 재측정            | 순증 그린 (+50~70 예상)       | ✅ **1019 passed (177 파일)** (+36)                |
| FE tsc / lint                                 | **0 / 0** ✅ 재측정                                       | 0 / 0                         | ✅ 0 / 0 (+prettier check exit 0)                  |
| BE pytest                                     | **2433 passed · 46 skipped** ✅ 재측정 (3-env 인캔테이션) | 순증 그린 (+60~90 예상)       | ✅ **2490 passed · 46 skipped** (+57)              |
| BE ruff / mypy                                | **0 / 0** ✅ 재측정                                       | 0 / 0                         | ✅ 0 / 0 (197 파일)                                |
| e2e:design-canon                              | 32 (문서 기준)                                            | **32 불변**                   | ✅ **32/32** (최종 스택 재실행)                    |
| e2e:authed                                    | 62 (문서 기준)                                            | +3~5, `--list` 증빙           | ✅ **63/63** (`--list` 63 = 62+tier-c 1)           |
| alembic upgrade/downgrade 왕복                | —                                                         | 그린 (alert_rules 1건)        | ✅ dev DB 실왕복 + psql `\d` DDL 검증 (평가자)     |
| DB 오라클 (펀딩 3점·포지션 2계통·cancel 왕복) | —                                                         | Fable 직접 실측               | ✅ 펀딩 3점 일치·alert row·cancelled 2건 psql 확정 |
| Opus MCP dogfood                              | —                                                         | 전 항목 + 기지 예외 외 콘솔 0 | ✅ V1~V5 PASS·psql 재대조 완료 (발견은 BL-421/422) |

## 3. 환경 (재발 방지 실측치)

- DB 5436 오버레이(`scratchpad/docker-compose.port5436.yml`) + redis 6380. 프로브 완료: orders=12/strategies=6/funding_rates=4/quantbridge_test 존재.
- BE pytest env: `TEST_DATABASE_URL=postgresql+asyncpg://quantbridge:password@localhost:5436/quantbridge_test` + `TEST_REDIS_LOCK_URL=redis://localhost:6380/3`.
- FE 3100 + BE `FRONTEND_URL=3100` + `PLAYWRIGHT_BASE_URL=http://localhost:3100`. 정체성 프로브(openapi title/<title>) 없이 오라클 선언 금지.
- psql 은 host 부재 — `docker exec quantbridge-db psql -U quantbridge -d quantbridge`.
