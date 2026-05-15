# CLAUDE.md align audit + docs/process cleanup (2026-05-15)

> **Date:** 2026-05-15
> **Branch:** `chore/docs-claudemd-audit-cleanup`
> **Trigger:** 사용자 의문 — global `~/.claude/CLAUDE.md` (Behavioral guidelines §1~§10) 정합 + over-engineering 누적 검증 + 제거 후보 식별
> **Plan:** `~/.claude/plans/behavioral-guidelines-to-concurrent-church.md`
> **Skill:** `deepen-modules` (Iron Law: 1회 = 1 도메인) — docs/process 트랙 채택, code-side 별도 트랙 deferred

---

## 0. Audit 동기

사용자 prompt = "프로젝트가 클로드.md 가이드라인 align 되어있나? 오버엔지니어링 / 제거 후보 있나?". `deepen-modules` skill 의 Iron Law (1 도메인 1 audit) 와 사용자 "전체" scope 충돌 → AskUserQuestion 으로 4 옵션 제시 + 사용자 docs/process 압축 (★★★★★ 즉시 효과 + risk 🟢) 선택.

본 audit = (a) §1~§10 align 종합 평가 + (b) docs/process surgical cleanup 5 commit + (c) code-side 후속 트랙 BL 등재 권고.

---

## 1. Phase 1 — Recon 결과 (2 Explore agent 병렬)

### 1.1 Top-level inventory

| 차원       | 수치                                                                                                           |
| ---------- | -------------------------------------------------------------------------------------------------------------- |
| Backend    | 90,482 LOC / 13 도메인 (strategy 7,539 + trading 5,316 + backtest 4,140 + tasks 3,336 + optimizer 2,900 + ...) |
| Frontend   | 182,181 LOC / features 4종 합 9.5k + app/\_components 2.9k                                                     |
| **docs/**  | **16M / 269 .md** (dev-log 92 file 2.9M + qa 7.6M = 66% 비중)                                                  |
| .ai/ rules | 5 file 719 LOC (가이드 100% 준수)                                                                              |
| Top file   | `pine_v2/interpreter.py` 1,303L (Deep module SSOT — audit 제외)                                                |

### 1.2 docs/ 폴더별 cross-ref + size

| 폴더          | size | 파일            | cross-ref                       | 결정                                       |
| ------------- | ---- | --------------- | ------------------------------- | ------------------------------------------ |
| `dev-log/`    | 2.9M | 92              | ∞ (활성)                        | 3 file 통합/압축                           |
| `qa/`         | 7.6M | 57 (50 PNG)     | 2 (BL-244~246 evidence)         | 보존 (PNG→WebP tradeoff = A2 보류)         |
| `_archive/`   | 524K | 14              | 0                               | git rm + .gitignore                        |
| `reports/`    | 264K | 9 (7 종료 HTML) | 2 (template + auto-dogfood/ 만) | 7 종료 HTML git rm + .gitignore drift 차단 |
| `prototypes/` | 792K | 13              | 50                              | 보존 (구현 스펙)                           |
| `dogfood/`    | 580K | 4               | 28                              | 보존 (sprint50 PNG WebP A2-2 보류)         |
| `guides/`     | 56K  | 7               | 32                              | 보존 (template)                            |

---

## 2. CLAUDE.md §1~§10 align 평가

| 규칙                                | 상태         | 근거                                                                                             |
| ----------------------------------- | ------------ | ------------------------------------------------------------------------------------------------ |
| §1 Think Before Coding              | ✅           | codex G.0/G.4 evaluator + plan-eng-review 적용 (memory `feedback_codex_g0_pattern.md`)           |
| §2 Simplicity First                 | ⚠️           | docs/process meta-violation 3건 + code-side 거대 service 3건 (별도 트랙)                         |
| §3 Surgical Changes                 | ✅           | Sprint 59 PR-D 158 BL → 13 active 트리아주                                                       |
| §4 Goal-Driven Execution            | ✅           | Sprint 60 17 BL Resolved + 4-AND Beta gate 명세                                                  |
| §5 No Closing Colons (Korean)       | ⚠️ 위반 누적 | Track C1 검출 = **181 line** (dev-log 161 + dogfood 12 + guides 8). BL-306 등재 + LESSON-068 1/3 |
| §6 Korean Header Comments           | ⚠️ 위반 누적 | Track C2 검출 = **70 file 누락** (BE 14 + FE 56). BL-307 등재 + LESSON-068 1/3                   |
| §7 Plan + Checklist + Context Notes | ✅           | Sprint 단위 plan + checklist + close-out + dev-log                                               |
| §8 Run Tests                        | ✅           | Sprint 60 BE 148 + FE 707 PASS, ruff/mypy/tsc clean                                              |
| §9 Semantic Commits                 | ✅           | Sprint 60 12 commit (1 commit 1 logical change)                                                  |
| §10 Read Errors                     | ✅           | investigate skill + codex consult                                                                |

**전반:** 8/10 ✅ + 2/10 ⚠️ (검증 skip). align 양호. 주된 over-engineering 신호 = docs/process 비대 + code-side 거대 service.

---

## 3. Track A — docs/process surgical cleanup (실행)

5 commit branch `chore/docs-claudemd-audit-cleanup`.

| commit | scope               | 변경                                                                                                                                                                                                      | 절감                      |
| ------ | ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------- |
| 1      | A1-1 + A1-2         | `_archive/2026-Q2-h1/` (524K, 14 file) + `reports/2026-04-*.html` (7 file 248K) git rm + .gitignore drift 차단                                                                                            | -7,491L / -772K           |
| 2      | A1-3                | `2026-05-04-sprint29-heikinashi-adr.md` (46L) → `sprint29-coverage-hardening.md` §3 inline 통합 + cross-link 갱신                                                                                         | -54L / -1 file            |
| 3      | A1-4                | `010-product-roadmap.md` (DEPRECATED 1차 초안 161L) git rm + `010b-product-roadmap.md` cross-link 갱신 (010a CPU Budget 별개 보존). 정정 — plan 가정 (3 file → 1 통합) ≠ 실제 (010+010b 중복 + 010a 별개) | -163L / -1 file           |
| 4      | A1-5                | `dogfood-week1-path-beta.md` (165L skeleton + Day 1 미기입) → 78L 압축 (baseline anchor + dayN cross-ref + 운영 절차 SSOT 위임 + dogfood-checklist L171 정합 유지 weekly summary section)                 | -91L                      |
| 5      | INDEX + audit entry | `dev-log/INDEX.md` 3 cross-ref edit (heikinashi row 제거 + 010 deprecated mark + audit entry 신규 추가) + 본 file 신규 작성                                                                               | net +160L (audit dev-log) |

**Track A net:** ~7,800L / ~770K 감소. **code 0 touch**. CLAUDE.md §3 Surgical 준수.

---

## 4. Track A2 (PNG → WebP) tradeoff 보류

| 후보                                               | 절감        | tradeoff                                                                            | 결정                 |
| -------------------------------------------------- | ----------- | ----------------------------------------------------------------------------------- | -------------------- |
| `qa/2026-05-13/traces/` PNG 50개 → WebP            | 7M → 2.1M   | BL-244~246 critical evidence file hash 변경 → git diff 노이즈, evidence 무결성 우려 | **보류**             |
| `dogfood/sprint50-stress-test-screens/` PNG → WebP | 544K → 162K | sprint 50 종료 = git diff 노이즈 영향 적음                                          | **사용자 결정 보류** |
| `qa/2026-05-14-sprint60-smoke/` PNG → WebP         | -408K       | 진행 중 sprint, 변환 보류 권고                                                      | **보류**             |

본 audit 권고 = A2 전체 보류 (evidence 무결성 우선). 향후 Beta 진입 후 별도 PR 로 재검토 가능.

---

## 5. Track B — Code-side over-engineering 후보 (BL 등재 권고)

본 audit scope 외 (Iron Law). 별도 `/deepen-modules` 호출 권고. 후보 3 도메인.

| 후보                     | LOC                                                                           | 권고                                          | trigger                                                              |
| ------------------------ | ----------------------------------------------------------------------------- | --------------------------------------------- | -------------------------------------------------------------------- |
| `backend/src/trading/`   | 5,316L / 32 file (providers.py 772L + tasks/trading.py 721L + models.py 528L) | `/deepen-modules trading`                     | live 거래 risk 도메인. providers multi-exchange dispatcher 분기 의심 |
| `backend/src/backtest/`  | 4,140L / 17 file (service.py 889L + v2_adapter.py 782L)                       | `/deepen-modules backtest` (interpreter 제외) | service-level 비대. v2_adapter pine_v2 adapter 책임 검증             |
| `backend/src/optimizer/` | 2,900L / 14 file (genetic.py 582L + bayesian.py 470L)                         | `/deepen-modules optimizer`                   | Sprint 54-56 신설 직후 = §7.5 신규 도메인 deepening trigger 매치     |

**호출 시점 권고:** Sprint 60 Beta gate 4-AND 통과 직후 (Day 7 인터뷰 2026-05-16 NPS 결과 후). dogfood 직전 = risk 회피 우선 (skill STOP condition).

**제외 대상 (Deep module SSOT — audit 금지):**

- `backend/src/strategy/pine_v2/interpreter.py` (1,303L) — pine_v2 SSOT, ADR-011
- `backend/src/strategy/pine_v2/stdlib.py` (793L) — pine_v2 stdlib SSOT
- `backend/src/strategy/pine_v2/coverage.py` (750L) — coverage matrix SSOT

---

## 6. Track C — meta align 미검증 항목 (수동 권고)

### C1. CLAUDE.md §5 No Closing Colons (Korean) 검증 → ✅ 실행 완료 (2026-05-15)

```bash
grep -rnE '[가-힣][가-힣 ]*:\s*$' docs/dev-log docs/guides docs/dogfood
```

**결과:** **181 line 위반** (false positive 0 — 모두 한국어 sentence ender). 폴더별 = dev-log 161 + dogfood 12 + guides 8. file 별 top 5 = `2026-05-01-sprint15-watchdog.md` 10 / `dogfood/sprint42-feedback.md` 7 / `2026-05-12-sprint54-bayesian-genetic-grammar-adr.md` 7 / `dogfood/sprint42-cohort-outreach.md` 5 / `2026-05-04-sprint28-kickoff.md` 5.

**처리:** **BL-306 신규 P3 등재** + **LESSON-068 1/3 등재** (한국어 docs lint mechanism 부재 누적 패턴, 3차 시 영구 승격 path).

### C2. CLAUDE.md §6 Korean Header Comment 검증 → ✅ 실행 완료 (2026-05-15)

```bash
find backend/src frontend/src -type f \( -name "*.py" -o -name "*.ts" -o -name "*.tsx" \) \
  ! -name "*.test.*" ! -name "*.spec.*" ! -name "*.d.ts" ! -name "index.ts" \
  ! -name "*.config.ts" ! -name "__init__.py" ! -name "conftest.py" \
  -exec sh -c 'head -3 "{}" | grep -q "[가-힣]" || echo "{}"' _ {} \;
```

**결과:** **70 file 누락** (BE 14/157 = **8.9%** + FE 56/243 = **23%**). 핵심 file 포함 = `backend/src/main.py` / `backend/src/core/config.py` / `backend/src/trading/registry.py` / `backend/src/optimizer/engine/bayesian.py` / `frontend/src/app/layout.tsx` / `frontend/src/app/(dashboard)/layout.tsx` / `frontend/src/lib/utils.ts` 등.

**처리:** **BL-307 신규 P3 등재** (ESLint custom rule + ruff custom rule + 70 file backfill, BL-306 묶음 sprint 가능). LESSON-068 안 §6 누락 패턴 함께 명시.

---

## 7. 결과 검증

```bash
du -sh docs/  # 16M → 약 15.2M (Track A1-1/A1-2 효과)
find docs/dev-log -type f -name "*.md" | wc -l  # 92 → 90 (heikinashi + 010 삭제)
git log --oneline chore/docs-claudemd-audit-cleanup ^main | wc -l  # 5 commits 예정
```

INDEX cross-ref 정합 검증:

```bash
grep -oE 'docs/dev-log/[a-zA-Z0-9_-]+\.md|\[.*\]\([^)]*\.md\)' docs/dev-log/INDEX.md \
  | grep -oE '[a-zA-Z0-9_-]+\.md' | sort -u \
  | xargs -I{} sh -c 'test -f "docs/dev-log/{}" || echo "MISSING: {}"'
```

MEMORY.md / project_sprint\*\_complete.md 안 dev-log file path 정합 — 삭제 file 발견 시 별도 audit 단계 (사용자 manual).

---

## 8. 다음 audit 권고

- **2026-05-16 Day 7 인터뷰 후:** NPS / bug 결과 합산 후 Sprint 61 분기 결정 시점에 Track B `/deepen-modules trading` 호출 권고
- **Sprint 61 분기 결정 시:** ✅ Track C1/C2 수동 검증 완료 (2026-05-15) → BL-306/307 등재 + LESSON-068 1/3. BL-306+307 묶음 sprint 권고 (Beta 진입 후, est ~12-17h)
- **본 audit branch:** `chore/docs-claudemd-audit-cleanup` PR 사용자 squash merge 의무 (main 직접 push 영구 차단)

---

## 9. Self-assessment

**8/10** (3-line 근거):

1. **Iron Law 준수 + scope split** — 사용자 "전체" 요청 vs deepen-modules 1 도메인 충돌을 surface tradeoff 후 docs/process 트랙 단독 채택. code-side 후속 트랙 BL 등재만.
2. **Plan A1-4 가정 정정 발견** — plan = 010/010a/010b 3 file 통합 가정. 실제 = 010+010b 중복 (1 rm) + 010a 별개 보존 (CPU Budget). audit 도중 fact 정정 후 commit message 안 명시.
3. **dogfood-checklist L171 정합 유지** — A1-5 압축 시 외부 cross-ref 의 weekly storage 역할 발견 → 압축본 안에 weekly summary section 신설로 외부 정합 차단.

**감점 2점:** Track A2 (PNG → WebP) tradeoff 결정을 사용자에게 명시 위임만 — 자동 변환 도구 (cwebp 등) 검증 X. 향후 evidence 보존 정책 정정 시 별도 audit.

---

## 10. LESSON-068 inline (사용자 main `.ai/` repo manual 갱신 의무)

> `.ai/` 는 본 프로젝트 gitignored — 사용자의 main `.ai/` repo 안에서 별도 commit 의무. 본 audit dev-log = first-class record. 아래 내용을 사용자 main `.ai/project/lessons.md` 안 `### LESSON-068` 으로 추가 권고.

### LESSON-068 — Korean docs lint mechanism 부재 → §5/§6 위반 누적 자연 발생 (1/3)

- **상황:** 2026-05-15 CLAUDE.md align audit Track C 검증 결과 — `~/.claude/CLAUDE.md` §5 (한국어 콜론 종결 금지) **181 line 위반** (docs/dev-log 161 + dogfood 12 + guides 8) + §6 (신규 source file 1줄 한국어 주석 의무) **70 file 누락** (BE 14/157 = 8.9% + FE 56/243 = 23%). main.py / core/config.py / trading/registry.py / app/layout.tsx 등 핵심 file 도 누락.
- **원인:** lint mechanism 0 — markdownlint custom rule (한국어 sentence + `:` end-of-line) 부재 + ESLint custom rule (한국어 주석 첫 3줄 의무) 부재 + ruff custom rule 부재. LLM 매 generation 자연 위반 + reviewer 0 → 누적.
- **해결 path:** (a) ruff custom plugin 또는 markdownlint custom rule 으로 §5 자동 검출 + auto-fix script (`:` → `.` 한국어 sentence ender 한정) (b) ESLint custom rule + ruff custom rule 으로 §6 누락 file 검출 + pre-commit hook (c) 누락 70 file 일괄 한국어 헤더 추가 sprint = BL-307. 1차 누적 (Sprint 60 Track C) — 3차 시 `.ai/common/global.md` §5/§6 mechanism 의무 영구 승격 path.
