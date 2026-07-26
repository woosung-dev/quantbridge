<!-- close-completeness 작업 체크리스트 -->

# close-completeness 체크리스트

## §0 전제 게이트

- [x] #473 머지 확인(main @ c859174) + 트리 클린 + 브랜치 stage/close-completeness
- [x] baseline 재현 — BE 2601 / FE 1083 / canon 32 (3-env)
- [x] codex G0(플랜 read-only) = REJECT → 전건 코드 대조 검증(§7.3) → 플랜 개정 + 사용자 재인터뷰(스윕 이연·트레일링 각주)

## B1 (BL-435) 청산 즉시 flat — post-fill Celery DEL

- [x] SSOT 키 헬퍼 `position_snapshot_cache_key` (position_service/position_fanout/task 3곳 공유)
- [x] tasks/trading.py `_execute_with_session` reduce_only fill 승자 → list_active_by_account 세션 캐시 best-effort DEL
- [x] 테스트: reduce_only fill → DEL / entry → 미DEL / DEL 실패 swallow

## B2 (BL-436) 청산 margin_mode 503 회피 — reduce_only skip

- [x] create_order set_margin_mode/set_leverage 를 `if not order.reduce_only:` 로 감쌈
- [x] 테스트: reduce_only → set 미호출 / entry → 호출 유지 + 기존 테스트 정합

## B3 (BL-434) 완전 TP/SL 보고 (display; 스윕 이연)

- [x] provider `fetch_open_conditional_orders` (2콜 union + orderId dedupe + stopOrderType 엄격분류)
- [x] PositionSnapshot += position_idx/trailing_stop + fetch_open_positions 파싱
- [x] position_service 조인(병합 리스트 source-dedup·정렬·has_trailing_stop) + 캐시 확장(구 payload graceful)
- [x] ExchangePositionSchema plural + has_trailing_stop (BE + FE 미러)
- [x] FE 병합 표시(익절/손절 콤마-join, colSpan 14 불변) + 각주 갱신 + 조건부 트레일링 각주
- [x] close_service hedge positionIdx 409 가드
- [x] 테스트: 조회 dedupe/분류 / 조인 병합·dedup·정렬 / hedge 가드 / plural 스키마 / 캐시 back-compat / has_trailing_stop(조건부 trail)

## 검증

- [x] W2 fe 적대평가 PASS(tsc/vitest 1084/lint) / W1 be 적대평가(pytest 2610·correctness clean) → ruff B023+mypy → codex resume hoist → PASS
- [x] codex 최종 diff = [P1] 1(has_trailing_stop 조건부 trail) 해소 + 회귀테스트
- [x] 게이트: BE **2611** / FE **1084** / ruff/mypy/tsc/lint 0 / canon 32 불변 / alembic 무변경(마이그레이션 0)
- [x] dogfood 3계통: 독립 오라클 raw ↔ 앱 provider ↔ BE get_reconciliation(익절 66000/손절 62000) + authed 브라우저(§03 병합·청산 flat·콘솔 0) + B1 캐시 DEL 실측 + B2 no-503 + Bybit Partial 자동취소(스윕 이연 안전)
- [x] 상태 전량 복구(세션 비활성·flat·docker 5436/6380·psql 재검증)

## 마감

- [x] docs/archive/sprints/close-completeness/{checklist,operating-contract,context-notes}
- [x] TODO.md 섹션 + BL-435/436 Resolved + BL-434 부분 + dev-log INDEX + 신규 BL-437(스윕)
- [x] 커밋(c73bcf3) → push(QB_PRE_PUSH_BYPASS=1) → **PR #474**(stage/close-completeness → main, squash=사용자 대기)
