이 프로젝트는 순차 step 러너(harness)를 **G2 의 두 번째 판**으로 쓴다. 아래에 따라 진행하라.

> **정본** — [ADR-033](../../docs/decisions/033-harness-readopt-codex.md) · [`.harness/README.md`](../../.harness/README.md) ·
> 파이프라인 [`generator-evaluator-pipeline.md`](../../docs/reference/operations/workflows/generator-evaluator-pipeline.md) §4
> **출처** — <https://github.com/jha0313/harness_framework> `.claude/commands/harness.md` 를 우리 파이프라인에 맞춰 개작.
> 상류 원문은 그린필드 단일 앱 전제라 A~E 를 그대로 쓰면 우리 레이아웃과 9곳에서 어긋난다(ADR-033 §꼬임).

---

## 0. 먼저 — 이 회차에 하네스가 맞는가

**적용** — step **3개 이상**으로 쪼개지고 · step 간 **순서 의존**이 있고 · **사람이 못 붙는 회차**.
**비적용** — step 1~2개. `codex exec` 1회가 더 싸다(저작 3~6분 + step 당 커밋 2개가 붙는다).
**영구 비적용** — 게이트 판정 · `docs/**` · celery 경유 · 거래소 쓰기 (역할 계약 §1 생성자 금지 목록).

아니면 여기서 멈추고 G2-a(단일 `codex exec`)로 가라.

## A. 탐색

`CONTEXT.md` · `AGENTS.md` · 해당 스택의 `apps/*/AGENTS.md` 를 읽는다.
`docs/status.md` 의 「다음 스프린트」와 대상 BL 을 연다. 필요하면 Explore 에이전트를 병렬로.

★`docs/backlog.md`·`roadmap.md` 는 **grep 으로만** 연다 — 통째로 읽지 마라(9천 줄).

## B. 논의

구체화·기술 결정을 사용자와 합의한다. **여기까지가 사람이 개입하는 구간이다.**

## C. Step 설계 — G1(수용 기준 동결)과 같은 행위다

★**step 파일의 `## Acceptance Criteria` 가 곧 G1 산출물**이다. 그래서 이 단계를 건너뛰면
파이프라인의 「생성/검증 분리」가 통째로 무너진다 — 생성자가 자기 기준을 쓰게 된다.

1. **Scope 최소화** — 1 step = 1 레이어/모듈. 여러 모듈이면 쪼갠다.
2. **자기완결성** — 각 step 은 **독립 세션**에서 돈다. 「이전에 논의한 대로」 금지.
3. **사전 준비 강제** — 읽어야 할 파일 경로와 이전 step 산출물 경로를 명시한다.
4. **시그니처 수준 지시** — 인터페이스만 주고 구현은 맡긴다. 단 벗어나면 안 되는 규칙(멱등성·
   `Decimal`·Repository-only·prefork-safe)은 박아 넣는다.
5. **AC 는 실행 가능한 커맨드** — 「~가 동작해야 한다」 금지.
   ★**착수 전에 red/green 양쪽을 실측해라.** 파일럿에서 헛초록 4건이 여기서 걸렸다(판정 없이
   `wc -l` · 기준을 `main` 으로 잡아 후속 step 의 정당한 변경까지 위반으로 셈 · 결함을 설명하는
   **주석** 때문에 `grep -q` 가 이미 rc=0 · 무관한 동명 상수).
6. **AC 를 시점 독립으로 짜라** — 「아직 X 를 안 건드렸다」는 뒤 step 이 X 를 정당하게 고치면
   영원히 red 다. 사후 재실행이 불가능해진다.
7. **네이밍** — kebab-case slug (`api-layer`, `auth-flow`).

## D. 파일 생성

`.harness/step-template.md` 를 복사해 채운다. ★**금지사항 블록을 지우지 마라** —
codex 는 `.claude/settings.json` 을 읽지 않아 상류의 ③층(Stop 훅)이 우리에겐 없다.
그 자리를 메우는 것이 ⑴ 이 금지사항과 ⑵ 어댑터의 `STEP_CHECKS` 둘뿐이다.

```
.harness/phases/<task>/
├── index.json     { "project": "QuantBridge", "phase": "<task>",
│                    "steps": [ { "step": 0, "name": "<slug>", "status": "pending" } ] }
└── step0.md …     ← 템플릿에서
```

`.harness/phases/index.json`(전체 현황)은 **선택**이다 — 없으면 러너가 조용히 건너뛴다.

★**step 파일까지 커밋한 뒤** 러너를 돌려라. dirty tree 로 돌리면 러너가 그것까지 주워
커밋이 늘고, 상류에 clean-tree 검사가 **0건**이라 아무도 막지 않는다(as-is 위험 1).

## E. 실행

```bash
git status --porcelain            # ★반드시 빈 출력
git rev-parse --abbrev-ref HEAD   # ★워크트리 브랜치인지 눈으로 확인

python3 tools/scripts/qb_harness.py <task>
```

★**워크트리에서만.** 권한 bypass 가 `.claude/settings.json` 의 deny 10종을 통째로 우회한다.
★**`--push` 는 없다** — 어댑터가 아예 안 받는다(Golden Rule).

러너가 하는 일: 가드레일 4축 주입 → step 순차 실행 → **어댑터 고정 검사**(FE typecheck · BE ruff)로
자기신고 검증 → `index.json` 갱신 → step 당 커밋. 실패 시 에러 원문을 프롬프트에 넣어 최대 3회 재시도.

**에러 복구** — `index.json` 의 status 를 `pending` 으로 되돌리고 `error_message` 를 지운 뒤 재실행.
★★**러너가 traceback 으로 죽었다면 재실행이 먼저가 아니다.** `index.json` 을 **눈으로 먼저 봐라** —
`completed` 가 남아 있으면 다음 run 이 그 step 을 **건너뛴다**(as-is 위험 7, 파일럿 B회차를 죽인 그것).

## F. 그 다음 — 러너가 끝나면 파이프라인으로 돌아온다

러너의 `completed` 는 **검증이 아니다.** G3(변이+오라클) 부터는 평가자(CONTROL)가 잡는다.
G8 종결에서 `.harness/phases/<task>/` 를 **승격·강등·삭제 중 하나**로 닫아라([ADR-026] §3).
