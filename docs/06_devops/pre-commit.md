# QuantBridge — Pre-commit (husky + lint-staged)

> **목적:** 커밋 전 자동 린트/포맷 훅 가이드.
> **SSOT:** [`../../package.json`](../../package.json) `lint-staged` + [`../../.husky/pre-commit`](../../.husky/pre-commit). 본 문서는 의도/우회 정책.

---

## 1. 개요

루트 `package.json`은 husky/lint-staged 훅 전용. frontend/backend 도구는 각자 독립.

```bash
# 최초 클론 후
pnpm install   # 루트에서 husky install 자동 실행
```

---

## 2. 트리거되는 검사

`package.json` `lint-staged` 설정:

| 패턴 | 검사 |
|------|------|
| `frontend/**/*.{ts,tsx,js,jsx}` | `pnpm lint --fix --file <path>` |
| `backend/**/*.py` | `ruff check --fix <path>` + `ruff format <path>` |
| `*.{json,md,yml,yaml}` | `prettier --write` |

> `--fix` / `--write` 옵션이 활성 — 자동 수정된 변경은 staging에 반영됨.

---

## 3. 흐름

```bash
git add <file>
git commit -m "..."
# → husky pre-commit hook 발동
# → lint-staged: 변경된 파일에만 검사 실행
# → 자동 수정 적용 후 commit 진행
# → 린트 실패 시 commit 차단
```

---

## 4. 우회 정책

> sprint-kickoff-template §방법론 규칙 인용:
> **`--no-verify` 절대 금지. 사용자 명시 승인 시만 허용.**

이유:
- 로컬 우회는 CI에서 동일 검사로 다시 막힘 → 무의미한 시간 낭비
- 우회 커밋이 main에 들어가면 추적 불가
- 정책 위반 시 lessons.md에 사례 기록

### 예외 (사용자 승인 필요)

- WIP 커밋 (push 안 함) + 다음 commit에 즉시 lint 통과
- 외부 의존성 변경으로 일시적 lint 충돌 (예: 신규 라이브러리 type stub 누락) — 최대 1 PR 내 해소

---

## 5. 자주 발생하는 문제

### 5.1 `ruff check --fix` 후에도 commit 차단
- ruff가 fix 못하는 위반 (type, naming) — 수동 수정 필요
- 메시지 확인 후 IDE에서 수정 → 재 `git add` → 재 commit

### 5.2 `pnpm lint --fix`가 ESLint 캐시로 stale
- `cd frontend && pnpm lint --cache=false` 강제 재실행
- `.eslintcache` 삭제 후 재시도

### 5.3 prettier가 markdown 줄바꿈 변경
- 본 프로젝트는 prettier 기본 설정 — 줄 길이 80자 권장
- `<!-- prettier-ignore -->` 주석으로 특정 블록 보호 가능 (남용 금지)

### 5.4 `.husky/pre-commit` 권한 에러
```bash
chmod +x .husky/pre-commit
```

### 5.5 husky가 동작 안 함
- `pnpm install` 재실행 (루트에서) — `prepare: husky` 스크립트로 셋업
- `.git/hooks/pre-commit` 심링크 존재 확인

---

## 6. 로컬 cache stale 이슈 (Sprint 4 D1)

- 로컬 ruff 통과해도 CI 실패 가능
- 원인: `.ruff_cache` 또는 `.eslintcache` stale
- 해소: `rm -rf backend/.ruff_cache frontend/.eslintcache` 후 재실행

---

## 7. 참고

- husky: https://typicode.github.io/husky/
- lint-staged: https://github.com/okonet/lint-staged
- ruff: https://docs.astral.sh/ruff/
- ESLint config: `frontend/eslint.config.*`
- Sprint kickoff 방법론 규칙: [`../guides/sprint-kickoff-template.md`](../guides/sprint-kickoff-template.md)

---

## 변경 이력

- **2026-04-16** — 초안 작성 (Sprint 5 Stage A)
