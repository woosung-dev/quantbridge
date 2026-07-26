# QuantBridge — CI / CD

> **목적:** GitHub Actions workflow 구조와 게이트 가이드.
> **SSOT:** [`../../.github/workflows/ci.yml`](../../.github/workflows/ci.yml). 본 문서는 의도/운영 가이드.

---

## 1. 잡 그래프

```mermaid
flowchart TB
    Trigger[push main / PR main]
    Changes[changes\nframework: dorny/paths-filter]
    FE[frontend\nlint + tsc + test]
    BE[backend\nruff + mypy + alembic + pytest]
    CI[ci summary\nfail if any failed]

    Trigger --> Changes
    Changes -->|frontend changed| FE
    Changes -->|backend changed| BE
    FE --> CI
    BE --> CI
```

### Changes-aware 분기

- `dorny/paths-filter@v3`로 PR diff에서 변경된 경로 감지
- `frontend/**` 변경 시만 frontend job 실행
- `backend/**` 변경 시만 backend job 실행
- 둘 다 변경 시 병렬 실행

> PR이 docs only 변경이면 두 job 모두 skip — `ci` summary가 통과 처리.

---

## 2. Frontend Job

| 단계 | 명령 | 목적 |
|------|------|------|
| Setup | pnpm v9 + Node 20 + cache | 의존성 캐시 |
| Install | `pnpm install --frozen-lockfile` | 재현성 확보 |
| Lint | `pnpm lint` | ESLint + Prettier |
| Type | `pnpm tsc --noEmit` | TypeScript Strict |
| Test | `pnpm test -- --run` | vitest |

> CI Node 버전은 20, 로컬 권장은 22+. 향후 일치시킬지 검토 (Sprint 5+).

---

## 3. Backend Job

| 단계 | 명령 | 목적 |
|------|------|------|
| Services | TimescaleDB + Redis containers | DB/Redis 의존 테스트 |
| Setup | `astral-sh/setup-uv@v3` (cache) + Python 3.12 | uv lock 캐시 |
| Install | `uv sync --all-extras --dev` | 의존성 |
| Lint | `uv run ruff check .` | 린트 |
| Type | `uv run mypy src/` | 타입 |
| Migration | `uv run alembic upgrade head` | round-trip 게이트 (DB는 `quantbridge_test`) |
| Test | `uv run pytest -v` | pytest 전체 |

### 환경 변수 (CI 전용)

- `DATABASE_URL=postgresql+asyncpg://quantbridge:password@localhost:5432/quantbridge_test`
- `REDIS_URL=redis://localhost:6379/0`

> CI services는 `localhost`로 노출됨 (Compose 내부 호스트명 아님).

> CI Python 버전은 3.12, 로컬 권장은 3.11+. CLAUDE.md/regex `python>=3.11`에 부합.

---

## 4. CI Summary

`ci` job:
- `if: always()` — 다른 job 결과와 무관하게 실행
- frontend/backend 결과 파싱 → 둘 중 하나라도 failure이면 `exit 1`
- skip은 통과로 간주 → docs only PR 머지 가능

---

## 5. PR 정책 (sprint-kickoff-template §B 인용)

- **Draft 시작** — sprint 진행 중 WIP
- **Milestone push 직후** `gh pr checks` 확인 — 실패 즉시 fix
- **`gh pr ready <N>`** — sprint 완료 시 ready 전환 + WIP 타이틀 제거
- **머지** — 사용자 명시 승인 후 (CLAUDE.md Git Safety Protocol)

### CI 실패 → 즉시 fix 원칙

- 로컬 ruff 통과해도 CI 엄격 (Sprint 4 D1)
- `.ruff_cache` stale 가능성 — `rm -rf backend/.ruff_cache` 후 재실행
- `--no-verify` 절대 금지 (사용자 명시 승인 시만)

---

## 6. 캐시 전략

| 캐시 | 위치 | 무효화 |
|------|------|--------|
| pnpm store | `~/.local/share/pnpm/store` | `pnpm-lock.yaml` 변경 시 |
| uv cache | uv 자체 cache 디렉토리 | `uv.lock` 변경 시 |

> 캐시 hit 시 install 시간 단축. 의존성 추가 후 첫 PR은 cache miss로 느릴 수 있음.

---

## 7. CD (배포)

> 현재 미설정. Sprint 7+ 배포 결정 후 별도 workflow 추가.

계획:
- staging deploy on push to `main` (선택)
- production deploy on tag `v*.*.*`
- 자동 alembic migration (Docker entrypoint)

상세는 [`../07_infra/deployment-plan.md`](../07_infra/deployment-plan.md).

---

## 8. 권한 / 보안

- `permissions: contents: read, pull-requests: read` — 최소 권한
- Secret은 GitHub Secrets에 저장 (`CLERK_SECRET_KEY` 등 — Sprint 7+ 배포 시점)
- `.env.local`은 절대 커밋 금지

---

## 9. 자주 발생하는 문제

### 9.1 frontend / backend job이 실행 안 됨
- `dorny/paths-filter` 패턴 확인 — 디렉토리 변경 없으면 skip 정상

### 9.2 backend job: alembic 실패
- migration 파일 `down_revision` 충돌 — `alembic heads`로 multi-head 확인
- `quantbridge_test` DB 권한 — services container env 점검

### 9.3 backend job: pytest 실패 (CI만)
- `.ruff_cache` stale 아님 — CI는 fresh
- timezone 차이 (CI=UTC, 로컬=KST) — naive datetime 비교 주의 (Sprint 5 S3-05 후 해소 예정)
- DB savepoint 격리 누락 — fixture 검토

### 9.4 frontend job: tsc 에러
- 로컬 IDE TypeScript 버전과 CI 버전 차이 — `frontend/tsconfig.json` strict 옵션 일치 확인

---

## 10. 참고

- CI workflow: [`../../.github/workflows/ci.yml`](../../.github/workflows/ci.yml)
- Pre-commit: [`./pre-commit.md`](./pre-commit.md)
- Local setup: [`../05_env/local-setup.md`](../05_env/local-setup.md)
- Sprint kickoff: [`../guides/sprint-kickoff-template.md`](../guides/sprint-kickoff-template.md) §B

---

## 변경 이력

- **2026-04-16** — 초안 작성 (Sprint 5 Stage A)
