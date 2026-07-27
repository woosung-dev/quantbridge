# live-conditional-hardening — 체크리스트

> 브랜치 `feat/live-conditional-hardening` · 베이스 `main` @`30031efe`.
> 이 문서는 **커밋하지 않는다**. 종결 시 흡수 대조 후 삭제한다.
> 플랜 = `~/.claude/plans/claude-plans-quantbridge-live-condition-fluffy-cherny.md`

## G0 — preflight (완료)

- [x] 조건부 진입 주문 전수 — `cancelled 16` / `rejected 10` / `filled 5`, `pending`·`submitted` **0건**
- [x] 취소 16건 전부 `exchange_order_id` 보유 → **BL-499 경로는 프로덕션 미주행**
- [x] 48h 워커 로그 — `cancel_failed` 0 · `concurrent_transition_submitted` 0
- [x] BL-500 stuck 형태 후보 **0건** → 가설, 재현 픽스처 필요
- [x] 라이브 세션 활성 **0** / 총 4 → BL-498 상황 재현돼 있음
- [x] ccxt `bybit.fetch_positions(None)` = `settleCoin=USDT` + `category=linear` 계정 1콜
- [x] `close_position` 이 `is_active` 미요구 → 비활성 세션 id 로도 청산 가능

## G0.5 — codex 플랜 검증

- [x] codex read-only 1회 — 지적 8건
- [x] 8건 전건 재현 판정 — 6 반영 / 1 기반영 / 1 부분기각 (context-notes D5)

## Step 0 — 정리

- [x] stale worktree 10개 정리 완료

## Step 1 — BL-498 (본체)

- [x] 1a `providers.py` — `_position_snapshot_from_ccxt` 추출 + `fetch_all_open_positions` 신설 + 심볼 역정규화
- [x] 1a 왕복 테스트 (canonical → bybit → canonical 항등)
- [x] 1b `live_signal_session_repository.list_by_account` (+`user_id` 방어)
- [x] 1c `schemas.py` — `AccountPositionRow` / `AccountPositionsResponse`
- [x] 1d `position_service.get_account_positions` (+hedge 가드) (IDOR 선차단 · 캐시 네임스페이스 분리)
- [x] 1e `router.py` — `GET /exchange-accounts/{account_id}/positions`
- [x] 1f FE — api/schemas/query-keys/hooks + `account-positions-table.tsx` + 코크핏 §03 배치
- [x] BE 테스트(서비스 9 · provider 6 · repo 1 · api 2) · FE 테스트 8

## Step 2 — BL-499

- [x] `live_signal.py` 취소 루프 — `get_state_fresh` 재조회 → `cancel_raced` 분기 + **`to_place` 는 건너뜀**
- [x] 테스트 4건 — 분류·게이지 무영향·음성 대조·다음 tick 자가 치유

## Step 3 — BL-500

- [x] `fetch_order_status_task` 계약 확인 → **위임 자체를 기각**(D4/D5 #6)
- [x] 거래소 부재 로컬 행 제거 + 발산 로그 + `stage=exchange_missing` metric
- [x] 유령 행 종결은 우리 책임 아님 — 나이 게이트(3분)로 전파 지연과 분리
- [x] 테스트 4건 — 늙은 유령 재등재 / 최근 행 유지 / in-flight 유지 / 조회 실패 무제거

## 검증

- [x] 표적 변이 7종(M1·M2·M2b·M3·M5·M6·M7·M8) 전부 의도한 테스트만 red, 음성 green 유지
- [x] BE 게이트 — ruff·mypy 0 · alembic fresh 통과 · **마이그레이션 0** · pytest+cov 재실행 중
- [x] FE 게이트 — lint·tsc 0 · vitest **1174** · build ok · hooks grep clean
- [x] e2e design-canon **32** · authed **64/1** — ★그 1건은 **dev 서버 stale CSS 로 인한 거짓 red**(프로덕션 빌드에서 통과 확인). dev 서버 재기동 후 재측정 필요
- [x] G3 적대 검증 3렌즈 — DO-NOT-SHIP 9건 전건 재현 판정(수정 7 / 기각 1 / BL 1)
- [x] G5 dogfood 2회 — 1차 3중 대조 종단 · **2차는 1차가 못 밟은 15초 캐시 창**을 기전 수준으로 재현
- [ ] G6 최종 codex 누적 diff 리뷰 (실행 중)

## 종결

- [x] 문서 표류 5건 수정 (status ①⑤ · INDEX ②③ · roadmap ④)
- [x] `gates-and-traps.md` 함정 3군 추가 (거짓 red · 변이 검증 · 캐시/주기)
- [x] dev-log 신규 + INDEX + status + roadmap + backlog(BL-498/499/500 갱신 + BL-501/502/503 등재)
- [x] "내가 틀린 것" **9건**
- [ ] 작업 문서 흡수 대조 후 삭제 (`docs/` 최상위 10 유지)
- [ ] PR 생성 (squash 는 사용자)
