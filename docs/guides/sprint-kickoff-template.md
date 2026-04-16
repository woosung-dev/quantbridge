# Sprint Kickoff 템플릿

> **목적:** 새 Claude 세션에서 sprint를 시작할 때 사용하는 프롬프트 템플릿.
> Sprint 4 완료 경험에서 정제됨. 이후 모든 sprint에 재사용.

## 사용법

새 세션에서 다음 프롬프트를 복사-붙여넣기 하고, `{SPRINT_N}`, `{PREV_PR_NUMBER}` 같은 placeholder만 수정.

---

## 프롬프트 템플릿

```
Sprint {N-1}가 완료됐어 (PR #{PREV_PR_NUMBER}).
Sprint {N}을 시작하려고 해.

## 작업 1 — 상태 점검 + 환경 확인

1. git status / log --oneline -5 확인
2. 이전 PR 머지 여부 확인 (gh pr view {PREV_PR_NUMBER} --json state,mergedAt)
   - 머지됐으면 main HEAD 확인 후 feat/sprint{N}-<scope> 브랜치 생성 전 단계
   - 미머지면 "머지 먼저 할까요?" 사용자 확인 받기
3. Docker 서비스 상태 (quantbridge-db, quantbridge-redis)
4. backend 테스트 현황: uv run pytest -q 로 현재 pass 수 유지 확인
5. ruff + mypy clean 확인

## 작업 2 — Sprint {N} 범위 옵션 매트릭스

다음 문서를 참조해서 Sprint {N} 범위 옵션 매트릭스 제시:

- docs/TODO.md §Sprint {N}+ 이관 (이전 sprint에서 이관된 미완 항목)
- docs/superpowers/specs/ 최신 spec §10.5 (세부 사유/긴급도 맥락)
- docs/03_api/endpoints.md (다음 도메인 후보)
- CLAUDE.md §현재 컨텍스트 (도메인 진행 순서)

### 옵션 매트릭스 축 (sprint별 조정)

각 옵션당:
- 범위
- 산출 가치
- 의존성 / 리스크
- 예상 task 수
- 추천도 (⭐ 1-5)

결정은 사용자가 한다. 구현은 사용자 결정 후.

## 작업 3 — 결정 후 방법론

Sprint 1~4 패턴 답습:
1. superpowers:brainstorming — spec 작성
2. superpowers:writing-plans — plan 작성
3. superpowers:subagent-driven-development — full 2-stage review per task

## 방법론 규칙 (반드시 준수 — Sprint 4 교훈)

### A. Full 2-stage review 정책
- 모든 task에 spec reviewer + code quality reviewer 별도 디스패치
- Combined review로 압축 금지 (Sprint 4에서 compressed로 놓친 Critical 2건 있음)
- Simple task도 규정대로 — 생각보다 자주 Important issue 발견됨

### B. Milestone 단위 push + CI
- Milestone 완료 후 즉시 `git push` + `gh pr checks`
- CI 실패는 즉시 fix (로컬 ruff 통과해도 CI는 엄격)
- `.ruff_cache` 로컬 stale 가능성 고려

### C. Retroactive review
- 초기 compressed/skipped된 task는 Sprint 내 retroactive D로 검증
- Sprint 4에서 Critical bugs 2건 catch (reclaim_stale NULL, prefork engine)

### D. 외부 검토
- 대규모 spec은 Codex consult 또는 독립 에이전트 검토 1회 이상
- Sprint 4에서 Codex + Sonnet + Opus 3단계로 Critical 3건 사전 catch

## Sprint 4 프로젝트 특화 교훈

### D1. Pyright noise
- Pyright는 uv venv 미연결로 대부분 false positive
- 실제 검증: `uv run ruff check` + `uv run mypy` + `uv run pytest`만 신뢰
- 예외: `"X is not accessed"` 경고는 가끔 실제 (변수/import 추적 가능한 경우)

### D2. SQLAlchemy 2.0 mypy 제약
- 컬럼 비교 연산자: `# type: ignore[arg-type]`
- `.desc()`, `.asc()`, `.in_()`: `# type: ignore[attr-defined]`
- `Result.rowcount`: `# type: ignore[attr-defined]`
- `datetime|None < cutoff`: `# type: ignore[arg-type,operator]`
- 패턴은 `backend/src/strategy/repository.py` (Sprint 3) 참조

### D3. Celery prefork-safe
- `create_async_engine()` 모듈 import 시점 호출 금지 (master 프로세스 → fork 후 자식이 corrupt pool 상속)
- Lazy init 함수 패턴: 호출 시점에 engine 생성, 캐시
- Worker pool=prefork 고정 (gevent/eventlet 비호환)

### D4. 3-guard cancel pattern
- Transient CANCELLING 상태 + 3 guard (pickup / pre-engine / post-engine)
- `assert bt is not None` 금지 (python -O로 제거됨) → `if bt is None: logger.error + return`
- 조건부 UPDATE rows=0 → 반드시 `finalize_cancelled` fallback
- 완료 write와 trade insert는 단일 트랜잭션 (atomicity 주석 명시)

### D5. IntegrityError 번역
- asyncpg `ForeignKeyViolationError`: `isinstance(exc.orig, _AsyncpgFKViolation)` (substring 매칭 금지)
- SQLAlchemy 래핑 고려: `exc.orig` + `exc.orig.__cause__` 양쪽 체크
- 다른 IntegrityError는 propagate

### D6. Mock fixture cleanup
- `app.dependency_overrides[key] = override` 후 반드시 `app.dependency_overrides.pop(key, None)` teardown
- `app` fixture의 `clear()`에 의존 금지 (teardown 순서 의존성 fragile)

### D7. Naive UTC datetime ISO
- `datetime.isoformat()`은 naive에 `Z` 미부가
- `strftime("%Y-%m-%dT%H:%M:%SZ")` 또는 수동 `Z` append

### D8. Decimal-first 금융 연산
- `Decimal(str(entry)) + Decimal(str(exit))` (Decimal-first)
- `Decimal(str(entry + exit))` 금지 (float 공간 합산 후 conversion → precision 손실)

### D9. Stale reclaim NULL handling
- running + cancelling 양쪽 모두 reclaim 대상
- cancelling의 경우 `started_at NULL` (QUEUED→CANCELLING) → `created_at` fallback

### D10. Test fixture DB isolation
- savepoint + `expire_on_commit` 주의 (test vs production session)
- FK order: User → Strategy → Backtest 순 flush

## Git 규칙

- `main` 직접 커밋 금지
- feature branch: `feat/sprint{N}-<scope>`
- 커밋 message: `type(scope): summary` + body (한국어 OK)
- Co-Authored-By: Claude Opus 4.6 (1M context) footer
- push/PR merge는 사용자 명시 승인 후

## PR 관리

- Draft로 시작 → Sprint 완료 시 `gh pr ready <N>` + WIP 타이틀 제거
- Description: test plan 체크리스트 + milestone 테이블 + review trail
- Sprint 완료 표시: `docs/TODO.md` 업데이트

## 완료 기준 (DoD)

각 sprint 시작 시 spec §1.2에 **측정 가능한** 완료 기준 명시:
- ❌ "테스트 ≥N passed" (vanity metric)
- ✅ "필수 시나리오 리스트 M개 통과" (scenario-based)

## Sprint 진행률 추적

Milestone 단위 checkpoint:
- Task 완료 → TaskUpdate completed
- Milestone 완료 → push + CI 확인 + 요약 테이블 리포트
- 사용자에게 다음 milestone 진행 여부 확인

---

## 참고 파일

- `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md` — spec 포맷
- `docs/superpowers/plans/YYYY-MM-DD-<topic>.md` — plan 포맷
- `.ai/stacks/fastapi/backend.md` — Router/Service/Repository 3-Layer 규칙
- `.ai/common/global.md` — 전역 워크플로우 규칙
- `CLAUDE.md` — 프로젝트 고유 규칙 (Celery 비동기, Decimal, AES-256)

---

## 변경 이력

- **2026-04-16** (Sprint 4 완료 시점): 초판 작성. Sprint 4 교훈 D1~D10 응축.
```