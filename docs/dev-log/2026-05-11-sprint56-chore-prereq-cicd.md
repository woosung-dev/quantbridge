# Sprint 56 chore PR — CI/CD prereq (BL-238/239/240 Resolved)

> **Sprint:** Sprint 56 (chore follow-up) / **Date:** 2026-05-11
> **Branch:** `chore/bl-238-239-240-cicd-prereq` (PR pending)
> **Base:** `main @ 420edbc` (Sprint 55 PR #260 post-merge follow-up 직후 — PR #261 Sprint 56 Genetic 과 독립 머지 가능)
> **Sibling PR:** #261 (Sprint 56 Genetic 본격 — 영향 파일 disjoint, 머지 순서 무관)

---

## 1. 트리거

Sprint 55 close-out 시 등재된 **"Sprint 56 prereq 의무"** 3건 (BL-238/239/240) 처리. Sprint 56 Genetic 본격 (PR #261) 종료 후 같은 세션 안 동시 처리 = Sprint 57 zero-friction prereq lock.

3건 모두 CI/CD 시스템 영역 = backend/frontend 코드 영향 X = Sprint 56 PR #261 과 파일 disjoint = 별도 PR 분리 (semantic commits §9 정합).

---

## 2. 변경 사항

### BL-238 — lint-staged `ruff check --fix` exit 0 silent skip 차단

**문제**: Sprint 52 ruff `I001` 1차 + Sprint 55 `RUF002` 2차 발생 패턴 = lint-staged 의 `ruff check --fix` 가 unfixable 항목을 stderr warning + exit 0 처리 → commit 차단 X → CI 만이 첫 검출. Sprint 55 hotfix `6142ecd` (ruff RUF002 × → \*) 가 동일 패턴.

**fix**: `package.json` lint-staged `backend/**/*.py` command 를 3-step 으로 확장:

```diff
 "backend/**/*.py": [
-  "bash -c 'cd backend && .venv/bin/ruff check --fix ${0#backend/}'",
+  "bash -c 'cd backend && .venv/bin/ruff check --fix --exit-non-zero-on-fix ${0#backend/}'",
+  "bash -c 'cd backend && .venv/bin/ruff check ${0#backend/}'",
   "bash -c 'cd backend && .venv/bin/ruff format ${0#backend/}'"
 ],
```

- (1) `--fix --exit-non-zero-on-fix`: fixable 항목 자동 수정 후 commit 차단 (사용자 재커밋 의무).
- (2) `ruff check` (no-fix): unfixable 항목 (RUF002 곱셈 기호 등) commit 차단.
- (3) `ruff format`: 포맷팅 (변경 없음).

**LESSON-068 후보 = 3/3 정식 승격 path** — Sprint 57+ 재발 시 정식 lesson 등재.

### BL-239 — pre-push hook 에 `uv run mypy src/` 추가

**문제**: Sprint 55 hotfix `39ecc01` = mypy 5 errors (skopt import-untyped + Any return) 가 CI 만이 첫 검출. pre-push hook (`backend ruff check + pytest`) 안 mypy 미포함 → push 통과 후 CI fail 동일 패턴 반복 위험. **CI parity gap**.

**fix**: `.husky/pre-push` backend 분기에 `uv run mypy src/` 추가 (ruff + pytest 사이):

```diff
 if git diff --name-only @{u}.. 2>/dev/null | grep -q '^backend/'; then
-  echo "→ pre-push: backend ruff + pytest"
+  echo "→ pre-push: backend ruff + mypy + pytest"
   cd backend
   uv run ruff check .
+  uv run mypy src/
   uv run pytest -q
   cd -
```

### BL-240 — pre-push hook 안 `TEST_*` 변수 auto-source

**문제**: LESSON-061 (Sprint 51~56, 11+ 발생 count 누적 영구 quirk). pre-push hook 시점 BE pytest 실행 시 env vars (`TEST_DATABASE_URL` / `TEST_REDIS_LOCK_URL`) 누락 → `test_migrations.py` 4건 fail (asyncpg connection error). 매 push 마다 사용자 manual `export` 의무 반복.

**fix**: `.husky/pre-push` backend 분기 시작 시 mktemp + grep 패턴으로 **TEST\_\* 변수만** 자동 source. 운영 secret (DATABASE_URL / SECRET_KEY 등 non-TEST prefix) 차단 보장.

```sh
QB_ENV_FILE="$QB_REPO_ROOT/backend/.env.local"
if [ -f "$QB_ENV_FILE" ]; then
  QB_TMP_ENV=$(mktemp)
  grep -E "^TEST_[A-Z_]+=" "$QB_ENV_FILE" > "$QB_TMP_ENV" 2>/dev/null || true
  if [ -s "$QB_TMP_ENV" ]; then
    set -a
    . "$QB_TMP_ENV"
    set +a
    echo "  → BL-240 auto-source: backend/.env.local 의 TEST_* 변수 export 완료"
  fi
  rm -f "$QB_TMP_ENV"
fi
```

**구현 결정** (sh 호환):

- husky pre-push 는 sh (bash X) → process substitution `<()` 사용 불가 → 임시 파일 (`mktemp`) 경유.
- `grep -E "^TEST_[A-Z_]+="` 패턴으로 TEST\_ prefix 라인만 추출 (운영 secret 차단).
- `set -a + . source + set +a` 패턴 (POSIX shell 호환).
- hook 종료 시 shell context 소멸 = scope 격리.

**전제**: 사용자가 `backend/.env.local` 안에 `TEST_DATABASE_URL=...` / `TEST_REDIS_LOCK_URL=...` 를 본인 추가해야 효과 발현. 미설정 시 grep 결과 empty → no-op (no harm). Sprint 57+ runbook 갱신 권장.

---

## 3. 검증

### 정적 검증

- `sh -n .husky/pre-push` → syntax OK.
- `sh .husky/pre-push` smoke run → backend 변경 없을 때 정상 스킵 (변경 분기 진입 X).

### 영향 범위

- **backend/frontend 코드 변경 0** → BE pytest / FE vitest 회귀 검증 불필요 (PR #261 에서 통과한 baseline 그대로 유지).
- **package.json** + **.husky/pre-push** 2 파일만 변경.

### Sprint 56 PR #261 과의 conflict 검증

- 영향 파일 disjoint:
  - PR #261 → `backend/src/optimizer/*` / `frontend/src/*` / `docs/dev-log/2026-05-11-sprint56-close.md` / `docs/dev-log/2026-05-12-sprint54-bayesian-genetic-grammar-adr.md` / `docs/REFACTORING-BACKLOG.md` (BL-233 row) / `docs/dev-log/INDEX.md` (Sprint 56 row) / `AGENTS.md`.
  - 본 PR → `package.json` / `.husky/pre-push` / `docs/REFACTORING-BACKLOG.md` (BL-238/239/240 row) / `docs/dev-log/2026-05-11-sprint56-chore-prereq-cicd.md` (신규).
- `docs/REFACTORING-BACKLOG.md` 양쪽 변경 = 서로 다른 BL row → conflict 없음 (git 3-way merge 자동 해결).

---

## 4. BL flow (3건 Resolved + 0 신규)

| BL     | 우선순위         | 결과                                                                                                                            |
| ------ | ---------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| BL-238 | Sprint 56 prereq | ✅ lint-staged 3-step (`--fix --exit-non-zero-on-fix` + `ruff check` + `ruff format`) — Sprint 52/55 silent skip 패턴 재발 차단 |
| BL-239 | Sprint 56 prereq | ✅ pre-push hook mypy 추가 — Sprint 55 hotfix #2 (`39ecc01`) 패턴 재발 차단                                                     |
| BL-240 | Sprint 56 prereq | ✅ pre-push hook 안 TEST\_\* auto-source — LESSON-061 영구 fix (11+ 발생 count 종료)                                            |

**합계 변동 (PR #261 머지 후 적용)**: 94 (Sprint 56 close-out) → BL-238/239/240 Resolved -3 = **91 active BL**.

---

## 5. 후속 의무

- (사용자) `backend/.env.local` 에 `TEST_DATABASE_URL=...` / `TEST_REDIS_LOCK_URL=...` 추가 (BL-240 효과 발현 prereq).
- Sprint 57+ runbook (`docs/06_devops/runbook.md` 또는 신규) 에 BL-240 환경 변수 예시 명시 권장.

---

## End of chore PR doc
