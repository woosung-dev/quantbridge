<!-- trading-surface-pack 실행 체크리스트 -->

# trading-surface-pack checklist

## §0 preflight

- [x] #472 stage→main 머지 확인(main @ed0d1c5), 트리 클린, 새 브랜치 stage/trading-surface
- [x] baseline 재현: BE 2583 / FE 1075 / alembic head(마이그레이션 0)
- [x] codex G0 read-only 14 finding → 코드 대조 후 반영(§7.3)

## §2 generator (codex 2워커 병렬, worktree)

- [x] W1 be: P-TPSL 읽기(0→null) + P-CLOSE close_service+router+dependencies + order_service flatten 분기 + P-METRIC + 테스트
- [x] W2 fe: §03 TP/SL 2열+청산 액션(colSpan 14, 확인 모달, useClosePosition) + BL-416 + BL-425 + BL-432 + 테스트

## §3 evaluator (Claude 서브에이전트 per-worker, 게이트 직접 실행)

- [x] W2 적대평가 PASS (tsc/lint/vitest 1083, 4축)
- [x] W1 적대평가 FAIL(RUF059 1건) → codex resume → PASS (ruff/mypy/pytest 2601, 4축)

## §4 cherry-pick + 병합 게이트

- [x] W1(cc84391) + W2(13b0ba4) cherry-pick → stage/trading-surface
- [x] 병합 트리 게이트: BE ruff+mypy+pytest 2601 / FE tsc+lint+vitest 1083
- [x] authed 코크핏 e2e 확장(112234e, TP/SL·청산 열 구조)

## §6 dogfood (2계통 오라클)

- [x] 독립 curl HMAC 오라클 검증(balance/positions)
- [x] §03 TP/SL 읽기 대조(값 일치 + 빈값→— 정직 + 콘솔 0)
- [x] 청산 종단(모달 정직 고지 + reduce-only Order filled + 오라클 flat + Order row)
- [x] kill-switch 활성 청산 성공(가드 bypass 실증, KS 미소비)
- [x] 상태 전량 복구 + psql 재검증

## §7 마무리

- [x] FE build ✓ (22/22 static)
- [x] 최종 codex 누적 diff 1회 → MAJOR 1(청산 leverage cap-bypass) → 포지션값 fix + 재검증(BE 2601)
- [x] 재게이트: BE 2601 / FE 1083 / ruff·mypy·tsc·lint 0 / authed 66·canon 32(flaky /backtests 재시도 pass) / build ✓ / alembic 무변경
- [x] push(QB_PRE_PUSH_BYPASS=1) + PR **#473**(stage/trading-surface → main, squash=사용자 대기)

## §8 마감

- [x] docs/archive/sprints/trading-surface-pack/{operating-contract,context-notes,checklist}.md
- [x] TODO.md 섹션 + BL-431/416/425/432/433 Resolved + 신규 BL-434~436 + dev-log INDEX
- [x] 메모리 갱신 (project_trading_surface_pack_sprint_20260724 + MEMORY.md)
