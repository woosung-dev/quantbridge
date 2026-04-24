# 다음 세션 시작 프롬프트 — H2 Sprint 11 (Beta 오픈 준비 + Sprint 10 Critical Follow-ups)

> **사용법:** 아래 `✂ COPY START` 와 `✂ COPY END` 사이를 복사해 새 세션에 붙여넣기.
> 2026-04-25 Sprint 10 머지 직후 기준.

---

<!-- ✂ COPY START ─────────────────────────────────────── -->

````
H2 Sprint 11 + Sprint 10 Critical Follow-ups 통합 — Beta 오픈 준비 + 인프라 완성

## 전제

H2 Sprint 10 (Redis lock + Rate limit + CCXT error metric + Real broker skeleton) 는
`stage/h2-sprint10` (7cabcdf) 에 5 Phase squash + AGENTS.md 완료. 사용자 main PR 생성 대기
또는 이미 main 머지 상태. BE 1102 passed / 17 skip / 0 fail / ruff 0 / mypy 0.

H1 dogfood (Bybit Demo 3~4주) 는 병행 진행 중 가정 (AGENTS.md §H1 게이트 참조).

이번 세션은 **H2 Sprint 11 (Beta 오픈 준비)** + **Sprint 10 의 production-impact critical follow-ups 3건** 통합.

Narrowest wedge persona pain:
- "지인/Twitter 팔로어 5~10명에게 Beta 계정 나눠주고 싶은데, geo-block / disclaimer / waitlist 가 없음"
- "Sprint 10 의 Redis wrapping 이 실제 mutex 가 아니라 contention signal 만 — 멀티 서버 환경에서 실제 race 는 여전히 PG 단독 의존"
- "slowapi 0.1.9 bug workaround 가 prod 에 들어가 있음 — upgrade 안전한가?"

---

## 이번 세션 범위 (12~16h 예상)

### Phase A: Sprint 11-1 — US·EU Geo-block 3 계층 (2~3h) [critical]
- Cloudflare WAF Geo-block rule (한국 + 베트남 + 몇몇 동남아 제외 나머지 deny)
- Clerk signup restriction (country_code 기반 pre-signup validation)
- Landing page 상단 "Not available in US/EU" 명시
- `docs/07_infra/geo-block-setup.md` runbook

### Phase B: Sprint 11-2 — Disclaimer + ToS 임시 템플릿 (1~2h) [Beta prerequisite]
- 오픈소스 template (e.g. termly 무료) 기반 + AI 검토
- 한국어 + 영어 버전 2개
- `/disclaimer`, `/terms` Next.js 라우트 추가
- "법무 임시" 배너 상단 고지
- `docs/07_infra/legal-temporary.md` — H2 말 정식 변호사 교체 TODO

### Phase C: Sprint 11-3 — Waitlist 페이지 + Beta 초대 자동화 (3~4h)
- `/waitlist` 페이지 — narrowest wedge 필터링 양식 5 field
  (TV 구독 레벨 · Bybit/OKX 자본 규모 · Pine 경험 · 기존 도구 · pain 3줄)
- DB 테이블 `waitlist_applications` (Alembic migration)
- Admin 페이지 `/admin/waitlist` — approve/reject + Beta 초대 이메일 발송
- Resend.com 또는 Sendgrid 이메일 API 통합 (선택: 사용자 결정)
- invite token + Clerk signup link 자동 생성

### Phase D: Sprint 11-4 — Onboarding flow (2~3h)
- 계정 등록 → 첫 전략 upload → 첫 백테스트 실행 → 결과 확인 — **5분 target**
- `/onboarding` wizard UI (4 step: welcome → strategy → backtest → result)
- Bybit Demo 계정 연결 가이드 (API 키 발급 스크린샷 + 붙여넣기)
- 샘플 Pine 전략 1개 제공 (사용자 데이터 없어도 first-run 가능)

### Phase E: Sprint 10 Follow-up — Service-level Redis lock hold 확장 (3~4h) [Opus 권장 critical]
- Phase A2 wrapping 은 contention-signal only. 실질 mutex 로 확장.
- `backend/src/backtest/service.py::submit` 와 `backend/src/trading/service.py::execute` 에서
  `async with RedisLock(f"idem:{domain}:{key}", ttl_ms=30_000): await existing_flow()` 패턴
- PG advisory lock 은 tx 내부 그대로 유지 (2-layer)
- TDD 3건 — (a) 두 동시 요청 중 Redis mutex 로 1건 serialize, (b) Redis 장애 → PG 단독 수렴,
  (c) lock hold 동안 TTL 갱신 (heartbeat `extend` 호출 검증)
- 기존 idempotency 테스트 19 green 유지 회귀 확인

### Phase F: Sprint 10 Follow-up — slowapi upgrade 검증 (1~2h) [trust hardening]
- `slowapi>=0.1.9` → 최신 (0.2.x or master) upgrade 시도
- `_RateLimitStateInitMiddleware` workaround 제거 가능 여부 검증
- 기존 7 rate-limit TDD 모두 green 유지
- 성공 시 middleware 제거 커밋, 실패 시 TODO 업데이트 + upstream issue 링크

### Phase G: Sprint 10 Follow-up — `error_class` allowlist (1~2h) [cardinality leak 방지]
- `qb_ccxt_request_errors_total` 의 `error_class` 가 동적 예외 클래스 시 Prometheus leak
- `ccxt.BaseError` 및 asyncio/OS built-in (TimeoutError/ConnectionError/OSError) 외에는 "Other" bucket
- `backend/src/common/metrics.py::ccxt_timer` 내부 분기 추가
- TDD 2건 — (a) 알려진 예외 → 원 이름, (b) 무관한 예외 → "Other"

**Out of scope (Sprint 12 이관):**
- 11-5 Beta 사용자 인터뷰 스케줄 — 본인 수동 (AI 불필요)
- 정식 변호사 ToS (H2 말 D-5 A안)
- Sentinel / Cluster (Sprint 13+)
- Real broker E2E 실제 구현 (nightly 첫 실행 시 credentials + seed 하에)
- WebSocket rate limit

---

## 개발 방법론 — Sprint 10 동일 적용 (실제 Skill 호출)

| 단계 | Skill 호출 | 목적 |
|------|-----------|------|
| 세션 시작 직후 | `superpowers:using-superpowers` (자동) | entry |
| 마스터 플랜 작성 전 | `Skill(superpowers:writing-plans)` | Stage 3 Sprint 계획 |
| Plan-stage 검증 | `codex exec --sandbox read-only` | Generator-Evaluator (Sprint 10 에서 검증된 패턴) |
| Phase SDD 작성 전 | `Skill(superpowers:writing-plans)` 재호출 | Phase 단위 계약 SDD |
| Worktree 생성 | `Skill(superpowers:using-git-worktrees)` + 3 symlink (.venv + 2 node_modules) | LESSON-010 |
| 각 Phase 구현 Agent | `Skill(superpowers:subagent-driven-development)` + `Skill(superpowers:test-driven-development)` | TDD RED→GREEN→COMMIT |
| 독립 Phase 병렬 | `Skill(superpowers:dispatching-parallel-agents)` | A+B+C FE UI 병렬 가능 (독립 파일) |
| 3-way blind review | codex foreground + Opus background + Sonnet background | 각 Phase 완료 직후 |
| 완료 주장 전 | `Skill(superpowers:verification-before-completion)` | evidence before assertion |
| merge | `Skill(superpowers:finishing-a-development-branch)` | stage→main PR |

### Generator-Evaluator (3-way blind review) — Sprint 10 확립 패턴

Sprint 10 5 Phase 모두 iter-1 로 production-impact 이슈 차단:
- A1: 4 fix (root .env · ValueError test · asyncio.wait_for · Celery hook docstring)
- B: 5 fix (SlowAPIMiddleware 등록 · storage timeout · webhook exempt · X-RateLimit · route.path cardinality)
- D: 4 fix (CancelledError TDD · cardinality 주석 · histogram assert · runbook retry+drilldown)
- A2: 3 fix (lazy pool · probe_key uuid · wrapping 정직화 docstring)
- C: 4 fix (pytest-timeout · pipefail shell · ensureLabel helper · dead env)

**PASS 기준 (유지):** avg confidence ≥ 8/10 ∧ blocker 0 ∧ major ≤ 2
**GWF 정책 (유지):** 2 vote 이상 major 만 fix + 단독 major 중 실질 bug 선별 + 3 iter FAIL 시 해당 항목 분리 후속 PR

---

## 브랜치 전략 (Option C — Sprint 10 동일)

```
main (Sprint 10 머지 후)
 └─ stage/h2-sprint11  ← 사용자가 최종 main PR 수동 생성
     ├─ feat/h2s11-geo-block              (Phase A)
     ├─ feat/h2s11-legal-temporary        (Phase B)
     ├─ feat/h2s11-waitlist               (Phase C, 큰 변경 — BE + FE)
     ├─ feat/h2s11-onboarding             (Phase D, FE 중심)
     ├─ feat/h2s11-service-level-lock     (Phase E, Sprint 10 A2 follow-up)
     ├─ feat/h2s11-slowapi-upgrade        (Phase F, Sprint 10 B follow-up)
     └─ feat/h2s11-error-class-allowlist  (Phase G, Sprint 10 D follow-up)
```

**시퀀스:**
- **A → B 순차** (Beta 오픈 기반 필수)
- **B 머지 후 C + D 병렬** (dispatching-parallel-agents 단일 메시지 2 Agent)
- **C + D 머지 후 E + F + G 병렬** (3 follow-ups 독립)
- 최종 stage → main PR 사용자 수동

**총 예상:** 12~16h. 병렬 시 9~11h 가능.

---

## Phase 분해 초안 (SDD 세션에서 확정)

### Phase A — US·EU Geo-block 3 계층

**위치:**
- `docs/07_infra/geo-block-setup.md` (runbook 신규)
- Cloudflare WAF rule (manual, 본 PR 은 runbook 만)
- `frontend/src/middleware.ts` — geo header 기반 redirect
- `backend/src/auth/dependencies.py` — Clerk signup webhook validation

**TDD 3건:** 한국 allow · US deny landing · VPN 우회 시 Clerk 단계 deny

### Phase B — Disclaimer + ToS 임시 템플릿

**위치:**
- `frontend/src/app/disclaimer/page.tsx` + `frontend/src/app/terms/page.tsx`
- `frontend/src/components/legal-banner.tsx` — 전 페이지 상단 고정
- `docs/07_infra/legal-temporary.md`

**주의:** 법적 효력 낮음. H2 말 정식 변호사 교체 TODO 고지 필수.

### Phase C — Waitlist 페이지 + Beta 초대 자동화

**위치:**
- `backend/src/waitlist/{router,service,repository,schemas,models}.py` (신규 도메인)
- Alembic migration (waitlist_applications 테이블)
- `frontend/src/app/waitlist/page.tsx` — 5 field form
- `frontend/src/app/admin/waitlist/page.tsx` — approve/reject UI
- `backend/src/common/email.py` — Resend.com API wrapper (사용자 결정)
- `backend/.env.example` — `RESEND_API_KEY`

**TDD:** BE 8건 (form validation · DB save · admin approve 전환 · invite token 생성 · 중복 email 거부 · RLS user_id · email retry · rate limit 5/min `/waitlist`)

### Phase D — Onboarding flow

**위치:**
- `frontend/src/app/onboarding/page.tsx` — 4 step wizard
- `frontend/src/features/onboarding/*` (welcome · strategy · backtest · result 컴포넌트)
- Sample Pine 전략 1개 — `frontend/public/samples/ema-crossover.pine`
- Bybit Demo API 키 발급 가이드 (스크린샷)

**FE TDD:** 4건 — wizard 전진/후진, 샘플 전략 load, 백테스트 submit 후 완료 대기, 5분 TTL local state

### Phase E — Service-level Redis lock hold 확장

**위치:**
- `backend/src/backtest/service.py::submit` — `async with RedisLock(...)` 으로 기존 flow 감쌈
- `backend/src/trading/service.py::execute` — 동일
- Repository 의 wrapping 제거 (Phase A2 에서 추가한 것 — service-level 로 이동)

**TDD 3건:** 동시 요청 serialize · Redis 장애 시 PG 단독 수렴 · lock TTL 연장 (heartbeat)

### Phase F — slowapi upgrade 검증

**위치:**
- `backend/pyproject.toml` — slowapi 최신
- `backend/src/common/rate_limit.py` — `_RateLimitStateInitMiddleware` 제거 시도
- 기존 7 TDD 모두 green 유지

**성공 시 커밋:** "refactor(common): remove slowapi 0.1.9 workaround middleware"
**실패 시 커밋:** "chore(deps): slowapi upgrade blocked — TODO #N" + upstream issue link

### Phase G — `error_class` allowlist

**위치:**
- `backend/src/common/metrics.py::ccxt_timer` — except 분기에서 `_normalize_error_class(type(exc).__name__)` helper
- Allowlist: ccxt.BaseError 계열 이름 + TimeoutError + ConnectionError + OSError + RuntimeError + ValueError → 원 이름 유지. 그 외 → "Other"

**TDD 2건:** 알려진 예외 원 이름 · 동적 커스텀 클래스 "Other"

---

## 핵심 참조 문서 (세션 시작 시 필수 선독)

- `docs/superpowers/plans/2026-04-20-h2-kickoff.md` §4 Sprint 11 (148~183줄)
- `docs/superpowers/plans/2026-04-24-h2-sprint10-phase-{a1,b,d,a2,c}.md` — Sprint 10 전례
- `AGENTS.md` §현재 작업 Sprint 10 완료 라인 (Sprint 11 follow-up 항목 확인)
- `.ai/project/lessons.md` — LESSON-010~015 (worktree symlink · wrapping · slowapi bug · pipefail · pytest-timeout · Redis DB)
- `backend/src/common/{redlock,rate_limit,metrics,redis_client}.py` — Sprint 10 산출물 (Phase E/F/G 가 이들을 수정)
- `backend/src/{backtest,trading}/service.py` — Phase E wrapping 대상 service
- `backend/src/backtest/repository.py:182-187` + `trading/repository.py:206-211` — Phase E 에서 Repository wrapping 제거

---

## 주의사항 (Sprint 10 실측 learnings)

### 실패 가능성 높은 지점
- **Phase A Cloudflare WAF** — AI 가 직접 세팅 불가 (manual). runbook 만 작성. 사용자 수동 Cloudflare 대시보드 설정.
- **Phase B 법무 template** — 절대 AI 가 최종 법적 문구로 확정 금지. "법무 임시 — H2 말 변호사 교체" 배너 필수.
- **Phase C email provider** — Resend vs Sendgrid vs AWS SES 사용자 선택. API key 발급 수동.
- **Phase E wrapping scope 확장** — Repository → Service 이동 시 **기존 19 idempotency 테스트 회귀 위험**. 각 fix 후 `pytest tests/backtest/ tests/trading/ -k idempot` 강제.
- **Phase F slowapi upgrade** — breaking change 가능성. 기존 7 rate-limit TDD green 유지 우선. 실패 시 rollback + TODO.
- **Phase G allowlist** — allowlist 목록이 누락/과잉 시 cardinality 여전히 leak. production ccxt 예외 목록 실측 후 조정.

### 운영 함정 (Sprint 10 이월, 반복 확인)
- **worktree 3 symlink 필수** — LESSON-010 (3회 반복 시 승격 후보)
- **stage worktree 에서 Edit → commit → push** (main worktree 의 편집은 restore)
- **AGENTS.md 는 tracked, `.claude/CLAUDE.md` 는 symlink, `.ai/` 는 gitignored**
- **pre-push hook 은 신규 브랜치 시 `@{u}..` empty → skip** (commit body 에 local test 증거 명시)

### Evaluator 운영 (Sprint 10 20 iter-1 fix 실측)
- **codex CLI stdin hang** 반복 — foreground + 5 min timeout + 짧은 prompt + 2 회 실패 시 Opus+Sonnet 2-way fallback
- **Opus blind** 은 **설계 철학** 에 강함 (Wrapping 패턴 critique · module-level singleton)
- **Sonnet blind** 은 **edge case tree 탐색** 에 강함 (13~15 trip-wire 시나리오)
- **codex** 은 **실측 명령 실행** 에 강함 (`pytest-timeout` 미설치 재현 등)

---

## 병렬 worker 조합

- **A → B 순차** (Beta 오픈 기반)
- **C + D 병렬** (`Skill(superpowers:dispatching-parallel-agents)` 단일 메시지 2 Agent)
- **E + F + G 병렬** (독립 follow-up, 3 Agent)

총 worker 병렬 시 세션 내 3회 병렬 디스패치 발생.

---

## 커밋 단위 초안

```
c1  feat(infra): Cloudflare WAF geo-block runbook (Phase A)
c2  feat(frontend): middleware.ts geo header redirect (Phase A)
c3  feat(auth): Clerk signup country_code validation (Phase A)
c4  feat(legal): /disclaimer + /terms + legal-banner (Phase B)
c5  feat(waitlist): domain router+service+repo+schema+models+migration (Phase C)
c6  feat(waitlist): frontend form + admin approval UI (Phase C)
c7  feat(email): Resend.com integration + invite token (Phase C)
c8  feat(onboarding): 4-step wizard + sample strategy (Phase D)
c9  feat(backtest,trading): Service-level RedisLock wrapping (Phase E)
c10 chore(deps): slowapi upgrade + remove 0.1.9 workaround (Phase F, 성공 시) OR
    docs(todo): slowapi upgrade blocked — follow-up (Phase F, 실패 시)
c11 feat(observability): error_class allowlist — "Other" bucket (Phase G)
c12 docs(sprint11): AGENTS.md + lessons.md + main PR body 초안
```

---

## 시작 시퀀스

1. 본 프롬프트 + `AGENTS.md` + `docs/superpowers/plans/2026-04-20-h2-kickoff.md` §Sprint 11 읽기
2. Plan mode 진입 → **`Skill(superpowers:writing-plans)` 호출** → 마스터 플랜 `/Users/woosung/.claude/plans/h2-sprint-11-<code>.md` 작성
3. **codex plan-stage evaluator** 호출 (Sprint 10 패턴) — 본 Phase 분해에 대한 architectural risk / sequencing / 숨은 결합 탐색
4. `AskUserQuestion` 으로 핵심 scope 결정:
   - Q1: Email provider — Resend vs Sendgrid vs AWS SES
   - Q2: Onboarding sample strategy — EMA crossover vs RSI vs MACD
   - Q3: Phase F slowapi upgrade 시도 범위 — major upgrade 시도 vs minor 만 vs skip
5. ExitPlanMode
6. **Phase A → B 순차** (+ 각각 3-way iter-1)
7. **C + D 병렬** dispatch (`Skill(superpowers:dispatching-parallel-agents)`)
8. **E + F + G 병렬** dispatch (단일 메시지 3 Agent)
9. 모든 Phase 완료 → `Skill(superpowers:finishing-a-development-branch)` → AGENTS.md + lessons.md + main PR body 초안 → 사용자 수동 main PR

**첫 질문 금지** — 파일 읽고 Plan mode 진입부터 시작. 질문 필요 시 `AskUserQuestion` 툴.
````

<!-- ✂ COPY END ─────────────────────────────────────── -->

---

## 체크리스트 (세션 마감 시)

- [ ] Phase A/B/C/D/E/F/G 7 SDD 모두 `docs/superpowers/plans/` 에 생성
- [ ] 각 Phase 3-way Evaluator PASS (blocker 0, major ≤ 2, avg ≥ 8)
- [ ] Backend 전체 pytest green (1102 + Sprint 11 신규)
- [ ] Frontend 전체 pnpm test green (현재 173 + Sprint 11 신규)
- [ ] mypy 0 에러 / ruff clean / lint clean
- [ ] stage/h2-sprint11 → main PR 초안 제공
- [ ] AGENTS.md §현재 작업 Sprint 11 완료 라인
- [ ] lessons.md 신규 LESSON 2~4건 (email provider · geo-block 한계 · slowapi upgrade 결과)

## 성공 지표 (H2 Sprint 11 Acceptance)

- [ ] `/waitlist` 페이지 배포 + narrowest wedge filter 5 field 동작
- [ ] `/onboarding` 5분 target — 본인 TestClient 실측 5분 이내 완주
- [ ] Cloudflare WAF dashboard 에서 geo-block rule 확인 (사용자 수동 확인)
- [ ] 본인 외 **3명** 이 /waitlist 지원 + 그 중 **2명** narrowest wedge 일치 (Beta 초대 target)
- [ ] Phase E 완료 후 2 worker 동시 실행 테스트 — Redis 가동 시 중복 주문 0건 (실질 mutex 검증)

## Follow-ups (Sprint 12+ 이관 — 이 세션 scope 아님)

- 11-5 Beta 사용자 인터뷰 스케줄 + 실제 인터뷰 3회/사용자 (본인 수동)
- 정식 변호사 ToS (D-5 A안, $500~$1,500)
- Real broker E2E 실제 구현 (nightly 첫 실행 시)
- Redis Sentinel / Cluster (수평 확장 준비)
- TimescaleDB compression/retention policy (Sprint 10 out-of-scope)
- Freemium 티어 경계 확정 (Beta 유료 전환 의향 수집 후)
