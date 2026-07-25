# exit-money-path 체크리스트

> BL-444 (P1) + BL-445 (P2) — 세션 스코프 머니-패스 정정. 마이그레이션 **0**.
> 플랜 SSOT = `~/.claude/plans/exit-money-path-frolicking-cray.md`. 계약 = [`operating-contract.md`](operating-contract.md). 결정 이력 = [`context-notes.md`](context-notes.md).

---

## §0 전제 게이트

- [x] main `0a8e229` · 트리 클린 · 브랜치 `stage/exit-money-path` (main 베이스)
- [x] 스택 확인 — db **5433** · redis **6380** · worker/beat/ws-stream up · backend 8100 · FE 3100
- [x] 워커 최신 검증 — `sweep_closed_pnl_task()` → `{accounts, inserted, backfilled, resynced, alerted}` (`windows` 키 없음 ✅)
- [x] baseline 재현 — ★2회 실패 후 원인 규명 2건 (아래 §0-fix)

### §0-fix 인프라 사고 2건 (코드 무관)

- [x] **3-env 미export** — 셸에 env 가 없어 conftest 가 `localhost:5432` 로 폴백 → 400+ 에러. `set -a; source backend/.env.local; set +a` 로 해결
- [x] **Docker VM 디스크 100% 포화** — Postgres 가 `PANIC: could not write ... No space left on device` 로 무한 크래시-복구 루프. 빌드 캐시만 정리(`docker builder prune -f`, 10GB 회수 → 8.9G 여유). **볼륨·이미지 미변경**, 데이터 무손실 확인(원장 4행 유지)

## §0.5 재측정 스파이크

- [x] 착수 전 실측 재확인 — orders 0 · sessions 0 · events 0 · strategies 0 · accounts 1 · exits 4
- [x] 원장 구성 — `ours/none` 3행(−0.04367079) · `external_manual/none` 1행(−0.08025458) · **bracket/trailing/liquidation 0행**
- [x] 자동 계상 상한 — `matched_order_id` NOT NULL **0** · `attributed_strategy_id` NOT NULL **0**
- [x] 소비처 5곳 현재값 — **전부 0행 위에서 0**
- [x] 스윕 shape + 워커 최신성
- [x] **결론 — BL-438 ② 조건 미충족 확정 → 스코프 제외**

## §7.3 전건 코드 대조

- [x] Plan 압박검증 발견 4건 검증 — (A) beat 재발행 ✅ (B) unique 에 symbol ✅ (E) close_service `realized_pnl` 부재 ✅ (①은 **과장**으로 정정)
- [x] codex G0 = REVISE, [P1] 2건 — **둘 다 코드로 확인 후 수용**
- [x] fixture 기대값 10건 독립 산술 검증

## 구현

- [x] **Slice 0** — `tests/trading/test_session_scope_money_path.py` 대조군. ★**프로덕션 stash 후 before 값 5 passed 로 판별력 증명**
- [x] **Slice 1** — `SessionScope` + `from_live_session` + `_session_scope_where` + 개명 2건(구 메서드 삭제)
- [x] **Slice 2a** — `router.py` Site 4 배선 + 종단 테스트(인접 세션 2개 커브 분리)
- [x] **Slice 2b** — `alert_rules.py` Site 3 배선 + **알림 문구 2곳 정직화** + 신규 실 DB 태스크 테스트
- [x] **Slice 3** — BL-453 부분: `tasks/trading.py:1698` `.value` → `str()` + StrEnum 6필드 주석 통일
- [x] 기존 테스트 3파일 갱신 — `test_repository_orders.py` · `test_alert_rule_repository.py`(전면 재작성) · `test_alert_rules_task.py`(3곳)
- [x] 개명 잔존 참조 전수 grep — 코드 0건 (문서만, Slice 5 에서 갱신)

## 게이트

- [x] `ruff check .` — All checks passed
- [x] `mypy src/` — Success, no issues found in 203 source files
- [ ] BE pytest 전량 (baseline 2707 → 증가)
- [ ] FE pnpm test (baseline 1094)
- [ ] canon 32
- [ ] `alembic` 무변경 (마이그레이션 0)

## dogfood (D7 — 브라우저 회귀 확인만)

- [ ] MCP Playwright — 대시보드 · 코크핏 · 블로터 실주행
- [ ] `browser_console_messages` error **0**
- [ ] 빈 상태가 `"—"` 로 정직하게 렌더
- [ ] `/live-sessions/{id}/state` 응답 shape 불변

> 개발 DB 가 0행이라 **값 판별력은 fixture 담당**. dogfood 는 회귀 안전망이다 — 정직하게 그렇게 보고한다.

## 마감

- [ ] 신규 BL 5건 등재
- [ ] BL-444/445 Resolved · BL-453 부분 · BL-438 ② 갱신
- [ ] 문서 드리프트 5건 정리
- [ ] 최종 codex 누적 diff 리뷰 1회 (`main...HEAD`) — **생략 금지**
- [ ] PR 1개 (`stage/exit-money-path` → main), squash 는 사용자
