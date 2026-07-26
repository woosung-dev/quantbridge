<!-- position-cockpit 스프린트 체크리스트. 상속 체인 = tier-c → opspack-ws2 → perf-surface → position-cockpit -->

# position-cockpit 체크리스트

## 구현 (B1~B4)

- [x] **B1** WS position 채널 — PositionFanoutHandler + PrivateTopicRouter, `_stream_main` topics=("order","position") + message_handler(handler 제거), position_update 3-site 등재, list_active_by_account, DEL-before-debounce, 비활성계정 no-op, 클럭 주입 debounce
- [x] **B2** 발행 + 캐시 DEL — 비영속, qb_pos_snapshot DEL 후 publish_realtime
- [x] **B3** 계좌 잔고 REST — GET /exchange-accounts/{id}/balance(P2), BalanceSnapshot + fetch_usdt_balance_snapshot, AccountBalanceService(Redis 15s), fetch_balance 불변
- [x] **B4** 열린 포지션 표 — 세션별 대조(세션열) + short 부호 + 빈상태 + 503 재시도 + verdict + 각주, 활성세션 계정 잔고 카드, §02/§03 삽입 + §04~08 renumber(rise d8/d9 CSS), 진단 포지션 카드 제거(2카드)

## 검증

- [x] codex G0 = 12건 전부 CONFIRMED → 전건 반영(§2.5 하드닝 SSOT)
- [x] codex 생성 3워커(W1/W2/W3 worktree, workspace-write) — 생성/평가 완전 분리
- [x] Claude 적대 평가 3/3 — W2 PASS, W3 PASS, W1 테스트버그 1건 codex resume 수정 후 PASS (제품/12하드닝 전부 코드 검증)
- [x] 통합 cherry-pick W1→W2→W3(충돌 0) + 통합 하드닝 fixup(잔고 정직성 + 테스트 격리)
- [x] 게이트: BE **2583**(baseline 2557 +26)·FE **1075**(baseline 1057 +18)·ruff/mypy/tsc/lint 0·canon **32 불변**·authed **PASS**(코크핏 §02/§03 + 2카드 spec 확장)·alembic 무변경(마이그레이션 0)
- [x] codex 최종 누적 diff = **NO BLOCKING FINDINGS**
- [x] dogfood 2계통 + WS 4점 전 PASS(잔고 190679 curl 일치·flat·주문→포지션→발행프레임 P1 정확→청산, 콘솔 0, 하드닝 6종 라이브)
- [x] dogfood 상태 복구(세션 비활성 + alert_rules 원복 + psql 재검증)

## 마감

- [x] docs/position-cockpit/{checklist,operating-contract,context-notes}.md
- [x] TODO.md position-cockpit 섹션 + Next Action 갱신
- [x] dev-log INDEX 한 줄 + perf-surface #471 머지 반영
- [x] BL 등재 — BL-431(포지션 표 TP/SL·청산 액션) / BL-432(잔고 selector 클로저) / BL-433(subscribe metric + BL-423 연계)
- [x] 프로덕션 build ✓ Compiled successfully
- [ ] stage/position-cockpit → main PR(로컬 게이트 증빙), squash = 사용자
