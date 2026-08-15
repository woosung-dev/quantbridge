# Step 0: guardrail-proof

이 step 의 목적은 기능 구현이 아니다. **러너가 주입한 프로젝트 규칙이 실제로 이 세션에 도달했는지**를
증명하는 것 하나다. 코드를 고치지 마라.

## 읽어야 할 파일

없다. 이 프롬프트 **앞부분에 이미 주입된 프로젝트 규칙**만 근거로 삼아라.
파일을 새로 열어서 답을 찾지 마라 — 그러면 이 step 이 재려는 것을 못 잰다.

## 작업

`.harness/phases/smoke/PROOF.md` 파일 하나를 만들어라. 내용은 아래 5줄이다.
**주입된 규칙에서만** 답을 뽑아라.

```markdown
# guardrail-proof

- backend 패키지 매니저: <답>
- frontend 패키지 매니저: <답>
- 워크트리에서 `make up` 을 돌려도 되나: <예/아니오 + 한 줄 이유>
- Golden Rules (Immutable) 항목 수: <숫자>
- 주입된 4축 문서의 제목 4개: <쉼표로 구분>
```

그 파일을 만든 뒤 아무것도 더 하지 마라.

## Acceptance Criteria

```bash
test -f .harness/phases/smoke/PROOF.md
```

## 검증 절차

1. 위 AC 커맨드를 실행한다.
2. `.harness/phases/smoke/index.json` 의 step 0 을 갱신한다:
   - 성공 → `"status": "completed"`, `"summary": "PROOF.md 작성 — 주입 4축에서 5문항 응답"`
   - 실패 → `"status": "error"`, `"error_message": "<구체적 사유>"`

## 금지사항

- `tools/scripts/final-gates.sh` 를 실행하지 마라. 이유: 게이트는 **회차 단위**이고 사람이 돌린다.
  세션 단위로 오독해 66분 33초를 태운 실측이 있다 (ADR-030 §발견②).
- `pytest`·`vitest`·`pnpm build`·`ruff`·`eslint` 중 어느 것도 돌리지 마라.
  이유: 이 step 의 AC 는 위 `test -f` 하나뿐이고, AC 에 없는 것을 돌리다 1800s 상한에 걸린 실측이 있다.
- `docs/**` 를 만지지 마라. 이유: `backlog.md` 단일 파일 9천 줄이라 충돌한다.
- `make up`/`down`/`migrate`/`seed` 를 하지 마라. 이유: 앱 DB 는 1벌 공유다.
- 코드 파일(`apps/**`, `tools/**`)을 **한 줄도** 고치지 마라. 이유: 이 step 은 측정이지 구현이 아니다.
