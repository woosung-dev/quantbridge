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

- [x] `ruff check .` — All checks passed (pre-commit `ruff format` 후 재게이트 포함)
- [x] `mypy src/` — Success, no issues found in **203 source files**
- [x] BE pytest 전량 — **2717 passed / 0 failed** (baseline 2707 → **+10** = 신규 테스트 수와 일치)
- [x] FE `pnpm test` — **1094 passed = baseline 정확 일치** (FE 변경 0)
- [x] `alembic` 무변경 — `git diff main...HEAD -- backend/alembic` 공집합, head `20260725_0002` 유지
- [~] canon — **27 passed / 5 failed.** 5건 전부 차트 팔레트 CSS 안전망(`design-canon-runtime` 3 + `design-canon-tailwind-utilities` 2). ★**`frontend/` 이 main 과 바이트 동일**(`git diff main...HEAD -- frontend/` 공집합)이므로 이 브랜치가 만들 수 없다 = **main 의 기존 결함**. 아래 §환경 발견 2 참조

### ★한 번 red 였던 항목 — 정직 기록

- BE 첫 전량 실행에서 `tests/common/test_redis_client.py::test_get_pool_safe_across_event_loops` 1건 실패. 단독 실행·clean main·2회차 전량 모두 통과 → **순서 의존 flake** 로 판정. 내 변경 파일은 `tests/tasks`·`tests/trading` 이라 알파벳 순으로 `tests/common` **뒤에** 돌아 원인이 될 수 없다

## dogfood (D7 — 브라우저 회귀 확인만) — **🔴 환경 blocked**

- [x] MCP Playwright 로 `/dashboard` 실주행 — 렌더는 정상(사이드바·§01~§05 섹션·빈 상태 문구 전부 표시)
- [ ] `browser_console_messages` error 0 — **48건 관측, 전부 CORS/`ERR_FAILED`**
- [ ] 빈 상태 `"—"` 확인 — API 가 전부 실패해 판정 불가
- [ ] `/live-sessions/{id}/state` 응답 shape — 같은 이유로 판정 불가

### ★환경 발견 1 — 로컬 백엔드가 죽은 DB 포트를 향하고 있다 (이 브랜치와 무관)

8100 백엔드 프로세스는 **2026-07-24 08:22** 기동이고 인라인 env 가 `DATABASE_URL=...localhost:5436` 이다. **5436 은 닫혀 있다** — 2026-07-25 포트 정렬(5436 → 5433) **이전**에 뜬 stale 프로세스다. CORS 설정 자체는 정상이다(`OPTIONS` 프리플라이트가 `access-control-allow-origin: http://localhost:3100` 을 반환). DB 를 건드리는 실제 요청이 전송 단계에서 실패해 브라우저가 CORS 로 보고할 뿐이다.

**→ 백엔드를 5433 으로 재기동해야 브라우저 dogfood 가 의미를 갖는다.** 사용자가 띄운 프로세스라 임의로 죽이지 않았다.

### ★환경 발견 2 — main 에서 차트 토큰 9/10 이 런타임 미해석

canon 실패 5건의 실체 = `해석되지 않은 변수 — chart-tokens.ts 가 폴백으로 조용히 떨어진다`. `--bullish` `--bearish` `--chart-equity` `--chart-benchmark` `--chart-compare` `--text-muted` `--chart-dd-line` `--chart-dd-top` `--chart-dd-bottom` 9개가 `getComputedStyle(document.documentElement)` 에서 빈 문자열. `--border` 하나만 해석된다.

확인한 것 — 토큰은 `src/styles/globals.css` `:root`(라인 43·55 등)와 `.dark`(416~)에 **실재**하고, dev 서버가 내려주는 CSS 청크에도 **각 2회 존재**한다. 그런데 런타임에서 안 잡힌다. `--border`(라인 55)와 `--bullish`(라인 43)가 **같은 `:root` 블록**인데 하나만 해석되는 것이 핵심 단서다. FE 변경 0 인 이 PR 의 범위 밖이라 특성 파악까지만 하고 멈췄다.

> 개발 DB 가 0행이라 **값 판별력은 애초에 fixture 담당**이다. dogfood 는 회귀 안전망이었고, 그 안전망이 환경 때문에 못 돌았다 — 정직하게 그렇게 보고한다.

## 마감

- [x] 신규 BL **6건** 등재 (BL-454~459 — 459 는 최종 codex 발)
- [x] BL-444/445 Resolved · BL-453 부분 · BL-438 ② 재분류
- [x] 문서 드리프트 5건 정리 + active BL 카운트 산식 헤더 고정
- [x] **최종 codex 누적 diff 리뷰 1회** (`main...HEAD`) — **REVISE [P2] 1건**(세션 읽기↔주문 조회 TOCTOU). 전건 코드 대조 후 **회귀 아님**으로 판정(변경 전에는 창이 아예 없어 항상 전 기간 포함 · 읽기 전용 · 자가 교정) → 수정 대신 [BL-459](../REFACTORING-BACKLOG.md#bl-459) 등재 + 계약 §3.3 명시
- [x] **PR [#477](https://github.com/woosung-dev/quantbridge/pull/477)** (`stage/exit-money-path` → main) — squash 는 사용자
