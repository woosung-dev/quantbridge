# 하네스 Eval — AGENTS.md 룰 준수

> 코드에 테스트가 있다면, 하네스엔 Eval이 있다.

이 Eval은 QuantBridge의 비즈니스 로직이 아니라 **하네스 품질**을 측정한다.
AGENTS.md 한 줄·프롬프트 한 문장이 에이전트 행동을 바꾸므로, 하네스도 코드처럼
회귀한다. 두 축을 본다 (원본 finsight 하네스의 oncall 트랙은 제외):

- **review 트랙** — 리뷰 하네스가 AGENTS.md의 CRITICAL 룰 위반(Decimal·Repository·
  SecretStr·prefork·H-1~H-3)을 일관되게 잡아내고, 정상 코드를 오탐하지 않는지.
- **qa 트랙** — 라이브 `CONTEXT.md`+`AGENTS.md`가 코드베이스 질문(규약·함정)에 정확히
  답할 만큼 충분한지, 그리고 응답자가 틀린 전제에 동조하지 않는지(환각 방지).
  함정 한 줄을 AGENTS.md에서 지우면 해당 qa 케이스가 회귀로 잡힌다.

## 메커니즘

```
golden set → subject(리뷰어/응답자) 실행 → LLM-as-judge 채점 → 회귀 게이트
```

- **golden set**(`cases/*.md`): 입력 + 기대 라벨. `kind: review|qa`로 트랙을 가른다.
  - review(5): 본문=코드, 라벨=`expect`/`severity`/`rule`. 위반 4(금액 float ·
    Service 직접 DB · API 키 하드코딩 · prefork 모듈 전역 클라이언트) + 정상(오탐 방지) 1.
  - qa(2): 본문=질문, 라벨=`must`(반드시 담겨야 할 사실)·`must_not`(말하면 안 되는 오답).
    둘 다 틀린 전제 반박 가드(워크트리 celery · pytest DATABASE_URL 단독 주입).
- **리뷰어**(`reviewer.ts`): review 트랙 대상. AGENTS.md 룰 요약(`rules.ts`)을 적용해
  코드를 리뷰하는 경량 단일 호출(Sonnet, temperature 0). 산문 리뷰를 출력한다.
- **응답자**(`responder.ts`): qa 트랙 대상. **라이브 `CONTEXT.md`+`AGENTS.md`**를
  컨텍스트로 받아 질문에 답하는 경량 단일 호출(Sonnet, temperature 0).
- **judge**(`judge.ts`): 다른 모델(Opus)이 "subject가 기대대로 했나"를 pass/fail로
  채점한다(`judge`=review, `judgeQa`=qa).
- **게이트**(`run.ts`): kind로 분기해 실행하고, 하나라도 실패하면 `exit 1`.
  `ANTHROPIC_API_KEY`가 없으면 아무것도 호출하지 않고 `exit 2`.

## 실행

```bash
cd evals/harness && pnpm install   # 독립 패키지 (루트는 pnpm workspace 가 아니다)
ANTHROPIC_API_KEY=... pnpm eval    # 전체 Eval (Claude 호출 — 네트워크·비용·비결정성)
pnpm typecheck                     # 키 불필요 — tsc --noEmit
```

## golden set 키우기 — 사고 1건 = 케이스 1건

처음부터 크게 만들지 않는다. **문서화된 사고(회귀·오판·환각) 1건마다 케이스 1개**를
`cases/`에 `.md`로 추가한다 — 제로베이스 하네스 원칙의 "사고 1건 = 슬림 복귀 1건"과
같은 규칙이다. 새 케이스의 라벨(review=`expect`/`severity`, qa=`must`/`must_not`)은
**사람이 검수해 박제**한다 — 자동 라벨은 judge와 같은 모델 편향을 공유해 회귀를 놓친다.

## 한계 (의도된 트레이드오프)

- **judge는 흔들린다.** subject는 temperature 0으로 고정하지만 judge(Opus)는
  temperature를 지원하지 않아, LLM 채점이 완벽히 결정적이지는 않다. 판정이 애매하면
  사람이 최종 검토한다(judge 맹신 금지).
- **경량 리뷰어 ≠ 실제 리뷰 워크플로우.** 게이트 속도를 위해 단일 호출로 대리한다.
  산문 입출력이라 `reviewer.ts`만 headless 리뷰로 교체하면 실제 워크플로우를 eval할
  수 있다(judge·게이트는 불변).
- **qa 응답자는 CONTEXT.md+AGENTS.md를 통째로 받는다.** 사실이 문서에 있으면 거의
  맞힌다 — 즉 positive qa 케이스는 추론력 테스트가 아니라 **문서 커버리지 회귀
  센티넬**이다(그 줄을 지우면 red). 진짜 변별력은 전제반박 가드(틀린 전제에 동조
  안 하나)에서 나온다.
