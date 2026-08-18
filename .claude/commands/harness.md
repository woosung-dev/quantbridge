이 프로젝트의 하네스 러너(`tools/harness/execute.py`, v2)로 다단계 스프린트를 무인 실행한다.
아래 워크플로우를 따르라. (출처: jha0313/finsight — [ADR-030] 파일럿 결함을 고친 이식판.
★원본과 달리 **AC 는 러너가 실행해 exit code 로 판정한다** — step 세션의 자기신고를 믿지 않는다.)

> `phases/` 파일은 ADR-037 이후 **러너 회차의 공인 킥오프 메커니즘**이다 —
> generator-evaluator-pipeline §G8 의 「킥오프 파일 금지」는 러너 밖 회차에만 적용된다.

---

## 워크플로우

### A. 탐색

`docs/status.md` 의 「다음 행동」과 대상 BL 의 원장 섹션(`docs/backlog.md` grep), 관련 코드를
읽는다. 필요시 Explore 에이전트를 병렬로 쓴다. `CONTEXT.md` 를 반드시 읽는다(도메인 SSOT).

### B. 논의

구체화·기술 결정이 필요한 사항을 사용자에게 제시하고 논의한다(추천도를 붙여서).

### C. Step 설계

여러 step 으로 나뉜 초안을 작성해 사용자 피드백을 받는다. 설계 원칙:

1. **Scope 최소화** — 한 step = 한 레이어/모듈. 여러 모듈이면 쪼갠다.
2. **자기완결성** — 각 step 은 독립 codex 세션에서 실행된다. 「이전 대화에서 논의한」 같은
   외부 참조 금지. 필요한 정보는 전부 step 파일 안에 적는다.
3. **사전 준비 강제** — 읽어야 할 문서·이전 step 산출 파일 경로를 명시한다.
4. **시그니처 수준 지시** — 인터페이스만 제시하고 구현은 세션 재량. 단 벗어나면 안 되는
   핵심 규칙(멱등성·Decimal·Repository 경계·보안)은 명시한다.
5. **AC 는 실행 가능한 커맨드** — 러너가 `bash -c` 로 돌려 rc=0 만 통과다. 추상 서술 금지.
   ★**BE pytest AC 는 반드시 `cd apps/api && uv run --env-file .env.local pytest <대상> -q`
   모양으로 써라** — env 통째 소싱 없이는 `_db_guard` 가 rc=3 으로 죽는다(gates-and-traps §환경).
   FE 는 `cd apps/web && pnpm test -- --run <대상>` · `pnpm tsc --noEmit` 등 표준 러너만.
6. **주의사항은 구체적으로** — 「조심해라」 대신 「X 를 하지 마라. 이유: Y」.
7. **네이밍** — step name 은 kebab-case slug.

### D. 파일 생성 (사용자 승인 후)

#### D-1. `phases/index.json` (전체 현황 — 없으면 생성, 있으면 항목 추가)

```json
{ "phases": [{ "dir": "<task-dir>", "status": "pending" }] }
```

#### D-2. `phases/<task-dir>/index.json`

```json
{
  "project": "QuantBridge",
  "phase": "<task-name>",
  "steps": [
    {
      "step": 0,
      "name": "repro-test",
      "status": "pending",
      "ac": [
        "cd apps/api && uv run --env-file .env.local pytest tests/<대상> -q",
        "cd apps/api && uv run ruff check ."
      ]
    }
  ]
}
```

- ★**`ac` 배열은 step 마다 의무다** — 없으면 러너가 시작을 거부한다(rc≠0).
- `status` 초기값 전부 `"pending"`. 타임스탬프·`completed`·`error` 는 러너가 쓴다.
- step 세션이 쓸 수 있는 것: `summary`(산출 한 줄 — 다음 step 프롬프트에 누적 전달) ·
  `blocked`+`blocked_reason`(사람 개입 필요 시) **뿐이다.**

#### D-3. `phases/<task-dir>/step{N}.md`

```markdown
# Step {N}: {이름}

## 읽어야 할 파일

- {관련 정본 문서·이전 step 산출 파일 경로}

## 작업

{구체 지시 — 파일 경로·시그니처·핵심 규칙}

## Acceptance Criteria

(index.json 의 ac 배열과 동일한 커맨드를 여기 다시 적는다 — 세션이 스스로 돌려 보게)

## 금지사항

- {「X 를 하지 마라. 이유: Y」}
- 기존 테스트를 깨뜨리지 마라. 커밋하지 마라(커밋은 러너 소관).
```

### E. 실행

```bash
python3 tools/harness/execute.py <task-dir>          # 순차 실행
python3 tools/harness/execute.py <task-dir> --push   # 완주 후 push (PR 은 사람이)
```

러너가 하는 일: `feat/harness-<phase>` 브랜치 checkout → step 마다 [가드레일 4축
(CONTEXT.md + AGENTS.md 3장) + 이전 summary 누적 + 이전 에러 피드백] 프리앰블로
`codex exec` 호출(30분 timeout, 포착됨) → **AC 전건을 러너가 재실행해 판정** →
통과 시 step 당 커밋 1회 → 3회 실패 시 error 로 정지(작업 트리는 검시용으로 보존,
index.json 만 커밋). codex 트랜스크립트는 `phases/<dir>/runs/`(gitignore) 에 남는다.

에러/차단 복구: 사유 해결 → 해당 step 의 `status` 를 `"pending"` 으로 되돌리고
(`error_message`/`blocked_reason` 삭제) 재실행.

### 실행 환경 주의 (QuantBridge 고유)

- **메인 체크아웃에서 돌려라** — 워크트리에서는 celery 경유 검증이 침묵으로 메인 코드를
  돈다(AGENTS.md NEVER). AC 를 pytest/vitest/lint/build 로 한정하면 워크트리도 가능하다.
- 러너가 도는 동안 같은 체크아웃에서 다른 세션이 작업하면 안 된다(공유 작업 트리).
- codex CLI 가 로그인 상태여야 한다(세션 만료로 워커가 죽은 실측 있음).
- 완주 후 PR 생성·머지는 사람이 한다 — `--push` 는 branch push 까지만.
