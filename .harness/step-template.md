# Step {N}: {이름}

<!-- 이 템플릿은 `.claude/commands/harness.md` §D 가 쓰는 정본이다.
     ★「금지사항」 블록을 지우지 마라 — codex 는 `.claude/settings.json` 을 읽지 않아
     상류의 ③층(Stop 훅 = lint+build+test)이 우리에겐 없다. 그 자리를 메우는 것이
     이 블록과 어댑터의 STEP_CHECKS 둘뿐이다. -->

## 읽어야 할 파일

먼저 아래를 읽고 설계 의도를 파악하라. **이 프롬프트 앞에 주입된 규칙 4축**(도메인 헌법 ·
루트 규약 · backend · frontend)은 이미 들어와 있으니 다시 열지 마라.

- {이 step 이 건드릴 파일}
- {이전 step 이 만든/고친 파일 — 경로를 명시}

## 작업

{구체적 지시. 파일 경로 · 함수/클래스 시그니처 · 로직.
코드는 **인터페이스 수준까지만** 주고 구현체는 맡겨라.
단 벗어나면 안 되는 규칙은 박아라 — 멱등성 · `Decimal` · Repository-only · prefork-safe 등.}

## Acceptance Criteria

<!-- ★착수 전에 red/green 양쪽을 실측하고 여기 적어라. 실측 안 한 AC 는 헛초록이 된다. -->

```bash
{실행 가능한 커맨드}
```

- 수정 전 실측: {red 인가 green 인가 — 근거}
- 수정 후 기대: {무엇이 어떻게 바뀌어야 통과인가}

★**시점 독립으로 짜라** — 「아직 X 를 안 건드렸다」류는 뒤 step 이 X 를 정당하게 고치면 영원히 red 다.

## 검증 절차

1. 위 AC 커맨드를 실행한다.
2. `.harness/phases/{task}/index.json` 의 해당 step 을 갱신한다:
   - 통과 → `"status": "completed"`, `"summary": "산출물 한 줄"` (다음 step 프롬프트에 실린다)
   - 3회 시도 후 실패 → `"status": "error"`, `"error_message": "<구체적 사유>"`
   - 사람이 필요(키·인증·수동 설정) → `"status": "blocked"`, `"blocked_reason": "<사유>"` 후 즉시 중단

★네가 `completed` 라고 써도 **러너가 고정 검사(FE typecheck · BE ruff)로 뒤집을 수 있다.**
자기신고를 낙관적으로 쓰지 마라 — 뒤집히면 그 에러가 다음 시도 프롬프트에 그대로 실린다.

## 금지사항

<!-- ★이 4줄은 지우지 마라. 각 줄은 실측 사고 기록이다. -->

- `tools/scripts/final-gates.sh` 를 실행하지 마라. 이유: 게이트는 **회차 단위**이고 사람이 돌린다.
  세션 단위로 오독해 **66분 33초**를 태운 실측이 있다([ADR-030] §발견②).
- `docs/**` 를 만지지 마라. 이유: `backlog.md` 단일 파일 9천 줄이라 충돌한다.
- celery 경유 검증(백테스트·라이브신호·옵티마이저)을 하지 마라. 이유: worker 컨테이너가
  **메인의 `apps/api/src`** 를 mount 하므로 내 코드가 아니라 메인 코드가 돈다 — **침묵 실패**다.
- `make up`/`down`/`migrate`/`seed` 를 하지 마라. 이유: 컨테이너·앱 DB 는 1벌 공유다.

- {이 step 고유의 금지 — "X 를 하지 마라. 이유: Y" 형식}
- 기존 테스트를 깨뜨리지 마라. 스펙 밖 리팩토링을 하지 마라.
