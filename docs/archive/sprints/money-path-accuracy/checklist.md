<!-- money-path-accuracy 실행 체크리스트 — 계약은 operating-contract.md, 결정 기록은 context-notes.md -->

# money-path-accuracy 체크리스트

## §0 전제 게이트

- [x] PR #474 main 머지 확인 (`3a91713`) + 트리 클린 → `stage/money-path-accuracy` 생성 (main 베이스)
- [x] 스택 기동 확인 — db 5436 · redis 6380 오버레이 정상 · worker/beat/ws-stream up
- [x] baseline 재현 — BE **2611 passed / 46 skipped**, FE **1084 passed**, ruff/mypy clean, alembic head `20260724_0002`

## 계획 · 검증

- [x] codex G0 (핸드오프 read-only) — **REJECT**, 전건 코드 대조(§7.3) 후 절반 수용 / 절반 실측 반박
- [x] Explore 3-리더 grounding (BL-014 머니패스 / provider·ccxt 표면 / BL-362 알림)
- [x] Plan 압박검증 — 설계 결함 R1(마커 컬럼 부재) 발견
- [x] 사용자 인터뷰 **11건 확정** (D1~D11)
- [x] ccxt 실계약 검증 — `fetch_positions_history` 가 오라클 raw 와 바이트 일치하는 `info.closedPnl` 반환

## B1 — closedPnl backfill (BL-014 부분)

- [x] P1 `ClosedPnlSnapshot` + `fetch_closed_pnl` / `fetch_closed_pnl_page` (BybitFuturesProvider 전용)
- [x] P2 마이그레이션 `20260725_0001` (`realized_pnl_synced_at`) + `Order` 필드
- [x] P2 `backfill_exchange_realized_pnl` (non-optional Decimal · 3-guard CAS) + `list_unsynced_reduce_only_since`
- [x] P3 `trading.refresh_closed_pnl` + `_enqueue_closed_pnl_refresh` 4 winner 배선
- [x] P4 `trading.sweep_closed_pnl` + beat 5분 엔트리 + §7.2 sentinel + orphan 카운터
- [x] metrics `qb_closed_pnl_backfill_total{outcome}`

## B1 — filled_quantity 소생 + API

- [x] P5 `OrderReceipt.filled_quantity` + 4 create_order 구현 · 4 체결 winner write
- [x] P5 `qb_partial_fill_total{source}` (호출자 winner 블록)
- [x] P6 `OrderResponse` 3필드 + FE zod 미러 + 주문 원장 10→12열 + 확정/추정 배지

## B2 — BL-362

- [x] P7 `send_rule_alert(channel=both)` 라우팅 + 외곽 try/except 유지
- [x] P7 `run_live_error` raw 예외 문자열 제거(호출부) + 주석 갱신
- [x] P7 `backend/.env.example` · `.env.prod.example` 에 TELEGRAM\_\* 추가

## 게이트

- [x] BE ruff / mypy / pytest 3-env — **2653 passed / 46 skipped / 0 failed** (baseline 2611, +42)
- [x] FE tsc / test / lint — **1088 passed** (baseline 1084, +4), tsc·lint clean
- [x] alembic 왕복 + base 부터 전체 체인 + 드리프트 0 (마이그레이션 **1** = `20260725_0001`)
- [x] **canon 32 불변** · authed 63 passed(+1 데이터 시딩 의존 flake, diff 무관 — 실행마다 다른 라우트에서 발생) · `/orders` 전용 5건 전부 통과
- [x] §9.5 — 같은 child(`ForkPoolWorker-2`)에서 sweep task 4건 연속 성공 + beat 자체 발화 + §7.2 sentinel(`@worker_ready` 등록 검증) 통과

## dogfood (7단계)

- [x] 1 백필 종단 — 3건 전부 오라클 closedPnl 과 **완전 일치** + `synced_at` 기록
- [x] 2 수동 청산 — NULL → 거래소값, Kill Switch SUM `42.4607`→**`42.41703`** 이동 실증
- [x] 3 수수료 실증 — `closedPnl = gross − (openFee+closeFee)` 정확 성립. `e9026276` 은 **부호가 뒤집힘**(시뮬 +0.0253 → 실제 −0.04524449)
- [x] 4 스윕 — run1 `{scanned:3,applied:3,groups:1}` → run2 `{0,0}` **멱등**, 라이브 worker 로도 회수 재현
- [x] 5 BL-362 — `channel=both`, 클래스명 있고 raw 없음, 실발송 `{'slack': False, 'telegram': True}`. ★`SLACK_WEBHOOK_URL` 미설정 = **이전엔 발산 알림이 아무에게도 도달하지 않았음**
- [x] 6 authed 브라우저 — 12열 정확 · 확정/추정 배지 · body 가로스크롤 false · **콘솔 error 0**
- [x] 7 부분체결 — Bybit demo BTCUSDT 시장가로는 자극이 비현실적이라 결정론적 픽스쳐로 커버(각주 명시)
- [x] 상태 — 활성 세션 0 유지, 포지션 미개설(신규 거래 0), 되돌린 행 원복 확인, docker 5436/6380 보존

## 마감

- [x] 최종 codex 누적 diff — **DO-NOT-SHIP 2 BLOCKING** 전건 코드 대조 후 수정(분할 행 합산 / 스윕 페이징)
- [x] docs/money-path-accuracy/{checklist,operating-contract,context-notes}.md
- [x] TODO / BL — **BL-014 부분 Resolved** · **BL-362 Resolved** · 신규 **BL-438~442**
- [ ] push (QB_PRE_PUSH_BYPASS=1) → main PR 1개 (squash 는 사용자)
