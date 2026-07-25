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

- [ ] BE ruff / mypy / pytest 3-env (baseline 2611 초과, 실패 0)
- [ ] FE tsc / test / lint (baseline 1084 초과, 실패 0) — **1088 확인**
- [ ] alembic 왕복 (upgrade → downgrade -1 → upgrade) + 드리프트 0
- [ ] canon 32 불변 · authed 66
- [ ] §9.5 신규 task 라이브 검증 (같은 child N번째 성공)

## dogfood (7단계)

- [ ] 1 자동 청산 종단 — realized_pnl 이 closedPnl 로 교체 + synced_at 기록, 오라클 대조
- [ ] 2 수동 청산 종단 — NULL → 거래소값, Kill Switch SUM 반영 (psql)
- [ ] 3 수수료 차이 실증 — net vs gross
- [ ] 4 스윕 회수 + 재실행 멱등(rowcount 0)
- [ ] 5 BL-362 텔레그램 실수신 + raw 문자열 부재 확인
- [ ] 6 MCP playwright authed — /orders 12열 · 배지 · 콘솔 error 0
- [ ] 7 부분체결은 픽스쳐 커버 + 각주 정직 명시
- [ ] 상태 전량 복구 + psql 재검증

## 마감

- [ ] 최종 codex 누적 diff 1회
- [ ] docs/money-path-accuracy/{checklist,operating-contract,context-notes}.md
- [ ] TODO / dev-log / BL — BL-014 부분 Resolved · BL-362 Resolved · 후속 BL 4~5건
- [ ] push (QB_PRE_PUSH_BYPASS=1) → main PR 1개 (squash 는 사용자)
