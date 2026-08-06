# QuantBridge — CI / CD

> **목적:** GitHub Actions workflow 구조와 게이트 가이드.
> **SSOT:** [`.github/workflows/ci.yml`](../../../.github/workflows/ci.yml). 본 문서는 의도/운영 가이드.

---

## 1. 잡 그래프

```mermaid
flowchart TB
    Trigger[PR → main / stage/**]
    Changes[changes\ndorny/paths-filter]
    Doc[documentation\nmake docs-audit]
    FE[frontend\nlint + tsc + test + build]
    BES[backend_static\nruff + mypy • DB 불요]
    BE[backend ×3 샤드\nalembic + pytest --cov]
    BEC[backend_coverage\ncoverage combine + fail-under=90]
    E2E[e2e\nplaywright]
    CI[ci summary\nsuccess/skipped 아니면 실패]

    Trigger --> Changes
    Changes -->|frontend| FE
    Changes -->|frontend| E2E
    Changes -->|backend| BES
    Changes -->|backend| BE
    BE --> BEC
    FE --> CI
    BES --> CI
    BEC --> CI
    E2E --> CI
    Doc --> CI
```

### 트리거 — PR 만 (2026-08-06)

`push: [main]` 을 뺐다. 같은 내용이 PR 과 머지 직후 **두 번** 돌고 있었고(backend 23분 × 2),
`pull_request` 이벤트는 PR head 가 아니라 **머지 프리뷰**(`refs/pull/N/merge`)를 체크아웃하므로
머지 결과는 이미 PR 에서 검사된다. 남는 위험은 마지막 PR run 이후 **base 가 움직인 경우**뿐이고,
순차 머지 + 로컬 `scripts/final-gates.sh` 가 그 구간을 덮는다. main 을 손으로 확인해야 하면
`workflow_dispatch` 로 돌린다.

### Changes-aware 분기

- `dorny/paths-filter@v3`로 PR diff에서 변경된 경로 감지
- `frontend/**` 변경 시만 frontend / e2e job 실행
- `backend/**` 변경 시만 backend_static / backend / backend_coverage job 실행
- 둘 다 변경 시 병렬 실행

> PR이 docs only 변경이면 code job 이 전부 skip — `ci` summary가 통과 처리.
> 단 `documentation` 잡은 **항상** 돌고 `ci` 가 그 결과를 본다(아래 §4).

---

## 2. Frontend Job

| 단계    | 명령                             | 목적              |
| ------- | -------------------------------- | ----------------- |
| Setup   | pnpm v9 + Node 20 + cache        | 의존성 캐시       |
| Install | `pnpm install --frozen-lockfile` | 재현성 확보       |
| Lint    | `pnpm lint`                      | ESLint + Prettier |
| Type    | `pnpm tsc --noEmit`              | TypeScript Strict |
| Test    | `pnpm test -- --run`             | vitest            |

> CI Node 버전은 20, 로컬 권장은 22+. 향후 일치시킬지 검토 (Sprint 5+).
>
> ★**로컬에서는 `pnpm test` 를 쓴다.** 위 `pnpm test -- --run` 은 `--` 구분자가 있어 CI 에서만 정상 동작한다. 로컬에서 `pnpm test --run` 으로 잘못 쓰면 인자 중복으로 죽으면서 **exit 0** 을 낸다. 게이트 전종과 함정은 [`gates-and-traps.md`](./gates-and-traps.md) 참조.

---

## 3. Backend Job

**2026-08-06 — 잡 3벌로 쪼갰다.** pytest 한 스텝이 backend 잡 23분의 **94%(1313s)** 였다.

`backend_static` (DB 불요)

| 단계    | 명령                                          | 목적                          |
| ------- | --------------------------------------------- | ----------------------------- |
| Setup   | `astral-sh/setup-uv@v3` (cache) + Python 3.12 | uv lock 캐시                  |
| Install | `uv sync --all-extras --dev`                  | 의존성                        |
| Lint    | `uv run ruff check .`                         | 린트                          |
| Cache   | `actions/cache` → `backend/.mypy_cache`       | mypy cold 실측 32s → 캐시 hit |
| Type    | `uv run mypy src/`                            | 타입                          |

`backend` (matrix `shard: [a, b, c]` — 각 샤드가 자기 DB/Redis 서비스를 갖는다)

| 단계      | 명령                                                          | 목적                                        |
| --------- | ------------------------------------------------------------- | ------------------------------------------- |
| Services  | TimescaleDB + Redis containers                                | DB/Redis 의존 테스트                        |
| Migration | `uv run alembic upgrade head`                                 | round-trip 게이트 (DB는 `quantbridge_test`) |
| Test      | `uv run pytest $(python -m tests.shard_paths <샤드>) --cov=…` | 샤드 몫 + **부분** 커버리지 데이터          |
| Upload    | `actions/upload-artifact` (`include-hidden-files: true`)      | `.coverage.<샤드>` 조각                     |

`backend_coverage` (DB 불요)

| 단계   | 명령                                          | 목적                             |
| ------ | --------------------------------------------- | -------------------------------- |
| Verify | 조각 개수 == `shards.json` 키 개수            | **누락 탐지기** (아래 ★)         |
| Gate   | `coverage combine` → `report --fail-under=90` | BL-308/309 래칫을 **한 번** 판정 |

**샤드 경계는 실측이다.** `tests/strategy/pine_v2` 혼자 로컬 **164.0s / 56.3%** 이고 CI 는 그
구간이 **5.0배**(스위트 평균 4.27배) 느리다. 그래서 샤드 `b` 는 파일 **두 개**뿐이다 — 그 둘이
스위트의 35% 라서다. 정의·근거 = [`backend/tests/shard_paths.py`](../../../backend/tests/shard_paths.py).

**등가성은 증명됐다.** 전체 1벌 실행과 샤드 3벌 합본의 `coverage report` 가 **파일별로 완전히
동일**(TOTAL `730 38 192 23 93%`)했고, 샤드 수집 합계 = 전체 수집(1039 + 78 + 3133 = **4250**)이다.

★**조각 개수 검사가 유일한 누락 탐지기다.** 샤드 a·b 의 데이터 파일은 내용이 동일해서
(둘 다 trading 모듈을 import 로만 스친다) `coverage combine` 이 `Skipping duplicate data` 를 찍는다.
즉 **a 나 b 의 아티팩트가 통째로 사라져도 최종 커버리지 수치는 안 움직인다** — 커버리지로는
누락을 볼 수 없다. `upload-artifact` 의 `include-hidden-files: true` 가 빠지면 dot 파일이
기본 제외되어 정확히 그 상황이 된다.

★**분할이 새면 `backend/tests/test_pytest_shard_partition.py` 가 막는다** — 모든 `test_*.py` 가
정확히 한 샤드에 속하는지, `ci.yml` matrix id 가 `shards.json` 키와 같은지. 변이 4종 전건 red 확인.

### 환경 변수 (CI 전용)

- `DATABASE_URL=postgresql+asyncpg://quantbridge:password@localhost:5432/quantbridge_test`
- `REDIS_URL=redis://localhost:6379/0`
- `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` / `REDIS_LOCK_URL` — celery 는 `REDIS_URL` 을
  **안 읽는다**(`core/config.py` 별도 필드). 2026-08-01 에 이 셋이 없어 5건이 실패했다.
- `TRADING_ENCRYPTION_KEYS`

> CI services는 `localhost`로 노출됨 (Compose 내부 호스트명 아님).
> ★이 목록을 손으로 관리하지 마라 — `backend/tests/test_ci_workflow_env_parity.py` 가
> `Settings` 에서 compose 호스트 기본값을 갖는 필드를 뽑아 **모든** pytest 스텝 env 와 대조한다.
> 로컬에서는 `.env.local` 이 전부 localhost 로 채워서 이 드리프트가 **구조적으로 안 보인다.**

> CI Python 버전은 3.12, 로컬 권장은 3.11+. CLAUDE.md/regex `python>=3.11`에 부합.

---

## 4. CI Summary

`ci` job:

- `if: always()` — 다른 job 결과와 무관하게 실행
- `needs` = `frontend` · `backend` · `backend_static` · `backend_coverage` · `e2e` · `documentation`
- 판정은 **`success` 또는 `skipped` 가 아니면 실패**
- skip은 통과로 간주 → docs only PR 머지 가능

★**2026-08-06 에 구멍 2개를 막았다.**

1. `documentation` 이 `needs` 에 **없었다** — `make docs-audit` 이 빨개도 `ci` 는 초록이었다.
2. 판정이 `== "failure"` 였다 — `cancelled` 가 **통과로 읽혔다**. 이제 모르는 상태는 fail-closed.

3. `changes` 가 `needs` 에 **없었다**(이 구멍은 2026-08-06 이전부터 있었다) — 경로 감지 잡이
   실패하면 그 의존 잡이 전부 `skipped` 가 되고, 위 2번 규칙이 skipped 를 통과로 인정하므로
   `documentation` 하나만 성공해도 `ci` 가 초록이었다. **경로 감지가 죽으면 게이트 전체가 조용히
   사라지는** 경로다. codex 적대 리뷰가 잡았다.

> 잡 id 에 하이픈 대신 밑줄(`backend_static`)을 쓴 이유: `needs.backend-static.result` 는 표현식에서
> 뺄셈으로 파싱될 여지가 있어 대괄호 표기가 필요한데, 로컬에서 시험할 수 없는 문법이라 모호함이
> 없는 쪽을 택했다.

### 이 게이트가 **덮지 않는 것** (2026-08-06 codex 적대 리뷰 처분)

정직하게 적어 둔다 — 나중에 이 목록을 「없는 위험」으로 읽지 마라.

- ★**main 의 실제 커밋은 자동 검증되지 않는다.** `push: [main]` 을 뺐으므로 ⑴ 직접 push
  ⑵ PR 검사 후 base 가 움직인 뒤의 머지 는 검사 없이 main 에 들어간다. 이 레포는 GitHub
  branch protection 을 **쓸 수 없고**(private free — API 403), 직접 push 는 로컬 pre-push 훅과
  규율로만 막힌다. 실질 방어선은 **순차 머지 + 머지 직전 `gh pr checks` 재확인**이다.
- **merge queue 를 켜면 CI 가 아예 보고되지 않는다** — 트리거에 `merge_group` 이 없어서 큐의
  합성 커밋에 `ci` 체크가 생기지 않는다. 큐를 도입하는 날 트리거를 같이 추가해라.
- **env 감사는 키 존재만 본다** — 값이 `redis://redis:6379`(compose 호스트)나 빈 문자열로
  바뀌어도 통과한다. 그 고장은 CI 에서 연결 실패로 시끄럽게 죽으므로 감사의 표적이 아니다.
- **로컬 커버리지 방어선이 하나 줄었다** — `final-gates.sh` 의 커버리지 재현이 기본 skip 이므로
  래칫은 이제 **PR CI 한 곳에서만** 판정된다. 그 잡 자체가 고장 나는 경로는 샤드 조각 이름 검사와
  감사 테스트 2종이 막는다.

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

| 캐시       | 위치                        | 무효화                   |
| ---------- | --------------------------- | ------------------------ |
| pnpm store | `~/.local/share/pnpm/store` | `pnpm-lock.yaml` 변경 시 |
| uv cache   | uv 자체 cache 디렉토리      | `uv.lock` 변경 시        |

> 캐시 hit 시 install 시간 단축. 의존성 추가 후 첫 PR은 cache miss로 느릴 수 있음.

---

## 7. CD (배포)

> 현재 미설정. Sprint 7+ 배포 결정 후 별도 workflow 추가.

계획:

- staging deploy on push to `main` (선택)
- production deploy on tag `v*.*.*`
- 자동 alembic migration (Docker entrypoint)

프로덕션 배포의 선택과 시작 조건은 [`roadmap.md`](../../roadmap.md)의 Beta·Deferred 게이트가 정본이다.

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

- CI workflow: [`.github/workflows/ci.yml`](../../../.github/workflows/ci.yml)
- Pre-commit: [`./pre-commit.md`](./pre-commit.md)
- Local setup: [`local-setup.md`](./local-setup.md)
- Sprint kickoff: [`sprint-kickoff-template.md`](./workflows/sprint-kickoff-template.md) §B

---

## 변경 이력

- **2026-04-16** — 초안 작성 (Sprint 5 Stage A)
