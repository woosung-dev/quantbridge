# 다음 세션 시작 프롬프트 — H2 Sprint 1 구현

> **사용법:** 새 세션에서 아래 코드블록 전체를 복사·붙여넣기.
> 2026-04-24 계획·문서 작성 세션 직후 기준.

---

```
H2 Sprint 1 계획 + SDD 문서 작성 완료. 이번 세션은 실제 구현.

## 이전 세션에서 한 것
- Phase A/B/C SDD 문서 작성 + 심층 리뷰 (실측 코드 기반 갭 6개 발견·수정)
- CLAUDE.md 현재 작업 섹션 업데이트
- docs/dev-log/dogfood-week1-path-beta.md 생성

SDD 문서 위치:
- docs/superpowers/plans/2026-04-24-h2-sprint1-phase-a.md
- docs/superpowers/plans/2026-04-24-h2-sprint1-phase-b.md
- docs/superpowers/plans/2026-04-24-h2-sprint1-phase-c.md

## 현재 코드 상태
- main 기준: backend 985 pass / 17 skip / 0 fail, FE 167 tests
- 최근 머지: PR #68 (testnet→demo docs 정합)
- 구현 시작 브랜치 없음 — 이번 세션에서 생성

## 브랜치 전략 (Option C)
main
 └─ stage/h2-sprint1  ← 사용자가 최종 main PR 수동 생성
     ├─ feat/h2s1-dogfood-baseline   (Phase A)
     ├─ feat/h2s1-pine-v2-h2         (Phase B)
     └─ feat/h2s1-trading-ui         (Phase C)

## 실행 순서
Phase A → (Gate-A 통과) → Phase B 병행 with Phase C → Gate-B/C → stage 머지

Phase B와 C는 독립적이므로 autonomous-parallel-sprints 적용 가능.
Phase A는 환경 검증 위주 (코딩 거의 없음) — 직렬로 먼저 진행.

---

## Phase A (30~60분) — 환경 검증

Phase A SDD 전문: docs/superpowers/plans/2026-04-24-h2-sprint1-phase-a.md

핵심 작업:
1. backend/.env.example에 EXCHANGE_PROVIDER + Kill Switch 변수 추가
2. .gitignore에 .env.demo 포함 확인
3. Docker up + alembic upgrade head + trading schema 4개 테이블 확인
4. pytest tests/trading/ -v -x (green)
5. Smoke test 실행 (실패 시 TODO.md Blocked 기록, Phase B/C 진행)
6. docs/dev-log/dogfood-week1-path-beta.md 실제 값 기입

Gate-A 통과 기준: .env.example 수정 + DB 테이블 4개 + trading tests green

---

## Phase B — pine_v2 H2 심화 (구현 핵심)

Phase B SDD 전문: docs/superpowers/plans/2026-04-24-h2-sprint1-phase-b.md

### ⚠️ 실측 기반 주의사항 (이전 세션에서 확인)

**B-1 `_var_series` ring buffer:**
- 현재: `dict[str, list[Any]]` — list.append 무제한 성장 (interpreter.py 라인 198)
- RunResult.var_series 타입이 `dict[str, list[Any]]` → deque 전환 시 반드시 list() 변환 후 RunResult 생성
- `_eval_subscript`은 `series[-offset]` → deque에서 동일 동작, 변경 불필요
- 음수 offset (`x[-1]`) → `float("nan")` 가드 추가

**B-2 `valuewhen` cap:**
- 현재: `hist.insert(0, ...)` O(n) (stdlib.py 라인 251-271)
- deque(maxlen=500) + appendleft O(1) 로 전환
- `occurrence < 0` → nan, float occurrence → int() guard 필요

**B-3 User function 상태 격리:**
- StdlibDispatcher는 @dataclass → `_prefix_stack: list[str]`은 반드시 `__post_init__` 에 추가
- StdlibDispatcher.call()의 node_id는 int 타입 → prefix 적용 후에도 int 유지 (hash packing)
- finally 순서: scope_stack.pop() 먼저, 그 다음 stdlib.pop_call_prefix()

**B-4 request.security coverage:**
- CoverageReport 실제 필드명: `unsupported_functions` (not `unsupported_builtins`)
- Phase A T5 curl 명령에서 `.coverage.unsupported_functions` 로 확인

Gate-B: pytest tests/ -q 985+ green + mypy src/strategy/pine_v2/ 0 에러

---

## Phase C — FE Trading UI 개선

Phase C SDD 전문: docs/superpowers/plans/2026-04-24-h2-sprint1-phase-c.md

### ⚠️ 실측 기반 주의사항 (이전 세션에서 확인)

**C-3 주문 폴링:**
- FE Order 필드명은 `state` (not `status`) — OrderState: "pending"|"submitted"|"filled"|"rejected"|"cancelled"
- useEffect dep: `[query.data]` — ESLint react-hooks/exhaustive-deps disable 절대 금지
- prevStateRef stale entry 정리: fetch마다 currentIds로 없어진 order ID 제거 (메모리 누수 방지)

**C-1 Kill Switch 배너:**
- KS API 에러 시 황색 경고 배너 필수 (안전 우선 — 조용히 실패 금지)
- trigger_type 한국어 매핑: daily_loss, cumulative_loss, api_error

**C-2 Demo/Live 배지:**
- `a.mode` null/undefined guard + 알 수 없는 mode 값 fallback Badge 필요

**C-4 E2E:**
- mock 객체 `...` 금지 — 완전한 객체 정의 (schemas.ts 참조)
- 현재 E2E 인증 fixture 없음 — Clerk mock 또는 공용 route mock 처리 필요
- 5개 시나리오: Demo배지, KS active배너, KS 버튼disabled, KS API에러배너, KS resolve후 배너소멸

Gate-C: pnpm test 167+ green + pnpm tsc --noEmit 0 + pnpm lint 0 (hooks disable 없음)

---

## 커밋 단위

c1 feat(dogfood): .env.example Kill Switch vars + EXCHANGE_PROVIDER + week1 baseline
c2 feat(pine-v2): _var_series deque ring buffer (max_bars_back=500) + RunResult list compat
c3 feat(pine-v2): valuewhen deque appendleft O(1) + cap 500 + edge case guards
c4 feat(pine-v2): user function call-site ta.* state isolation via prefix stack
c5 feat(pine-v2): request.security explicit unsupported_functions coverage
c6 feat(trading-ui): kill switch active/error banner + KS_TRIGGER_LABELS + order button disabled
c7 feat(trading-ui): ModeBadge null guard + order state conditional polling + toast
c8 test(e2e): trading UI kill switch (4 scenarios) + demo badge e2e

---

시작 시 Phase A SDD 먼저 읽고 T1부터 진행.
Gate-A 통과 후 Phase B/C 병렬 워커로 킥오프.
```
