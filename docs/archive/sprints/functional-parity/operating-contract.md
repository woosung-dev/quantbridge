<!-- functional-parity 스프린트의 멀티에이전트 운영 계약 — c-language-port 계약 대비 델타만 기록 -->

# functional-parity 운영 계약 (델타)

> 기본 계약은 [`../c-language-port/operating-contract.md`](../c-language-port/operating-contract.md) 전부 상속 (오케스트레이터 직접 수정 금지 예외 3종 · 워커 자기보고 불신 · 게이트 직렬 · 래칫 3분류 · 3회 실패 규칙 등). 아래는 이번 스프린트에서 달라진 것만.

## 1. 역할 구조 (모델 교차)

| 역할                       | 담당                                                   | 비고                                                                               |
| -------------------------- | ------------------------------------------------------ | ---------------------------------------------------------------------------------- |
| 오케스트레이터 + 최종 검증 | Claude(Fable) 세션                                     | 게이트 재현·커밋·cherry-pick·DB 오라클 전담                                        |
| Generator                  | `codex exec` 4기 병렬 (workspace-write, 워크트리 격리) | c-port 의 opus 워커 자리를 codex 가 대체                                           |
| Evaluator                  | Claude 서브에이전트 (read-only 적대 리뷰)              | codex 생성 ↔ Claude 평가 = 공유 맹점 회피 교차                                     |
| codex read-only 지점       | 최종 누적 diff 리뷰 **1회만**                          | "codex 2지점(플랜+최종)" 기확정 유지 — 플랜 지점은 Plan 에이전트 3기 교차로 대체됨 |
| 브라우저 dogfood           | Opus 서브에이전트 + MCP Playwright                     | storageState 쿠키 주입 (PR #466 레시피)                                            |

## 2. codex generator 델타 규약

- 호출: `gtimeout <sec> codex exec "<prompt>" -C <worktree> -s workspace-write -c 'model_reasoning_effort="high"' --json < /dev/null`. exit 124 = hang → resume 1회 → Opus 워커 대체.
- **codex 는 git 조작 전면 금지 (파일 수정만).** linked worktree 의 git 메타가 `-C` 밖이라 sandbox 가 물리 차단 — 커밋은 평가 합격 후 오케스트레이터가 워커당 1커밋으로 수행 (cherry-pick/bisect/revert 단위 = 1).
- 재생성 루프: 평가 FAIL → `codex exec resume <session-id>` + 발견 원문, 최대 2회 (총 3시도).
- 워커 브랜치: `fp/trading` `fp/strategies` `fp/optimizer` `fp/backtest` — 전부 `stage/functional-parity` 베이스 (main 베이스 함정 차단).

## 3. 수용 파이프라인 (워커별)

1. Fable 기계 검사 — 권역 밖 파일(=즉시 FAIL), KITPORT 센티넬 무변경, CSS 주석 `*`+`/` 스캔.
2. Fable 게이트 재현 — tsc / lint / 스코프 vitest (BE: ruff / mypy / 스코프 pytest). 자기보고는 판정에 불사용.
3. Claude 적대 평가 4축 — (a) 명세 충족 (b) 캐논·§4.9 준수 (c) 신규 배선 테스트 실존 (d) 과잉 변경 무.
4. PASS → Fable 커밋 → stage cherry-pick 대기열 (순서: optimizer → backtest → strategies → trading).

## 4. 검증 오라클 (§7.3 — circular oracle 금지)

- 주문 취소: 클릭 후 psql 로 `state='cancelled'` 실측. submitted 는 202 후에도 DB submitted 유지 확인.
- backtest_count: DB `COUNT(*) GROUP BY strategy_id` ↔ API ↔ 화면 **3점 일치**.
- nav-count: psql `COUNT WHERE state IN ('pending','submitted')` ↔ 배지 + 취소 직후 감소.
- DB 접근 전 **정체성 프로브 의무**: openapi title=QuantBridge + psql 5433 row ↔ API 응답 동일 row 대조.
- 주문 시딩은 orphan_scanner 30분 창 내 검증+정리.
