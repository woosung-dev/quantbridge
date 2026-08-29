# Step 2: `mypy src` 에러 3건 수리 — CI 차단 게이트로 올리기 전에 초록을 만든다

## 읽어야 할 파일

- `apps/api/mypy.ini` (`strict = True` 는 **이미 켜져 있다** · `warn_unused_ignores = True`)
- `apps/api/src/strategy/pine_v2/py_renderer.py`
- `apps/api/src/strategy/narrative/service.py`
- `apps/api/src/strategy/service.py`

## 배경 (2026-08-30 실측 — `cd apps/api && uv run mypy src`)

```
src/strategy/pine_v2/py_renderer.py:251: error: Returning Any from function declared to return "str"  [no-any-return]
src/strategy/narrative/service.py:133: error: Argument "style" to "StrategyNarrativeResponse" has incompatible type "Any | Literal['other'] | None"; expected "Literal['trend_following', 'mean_reversion', 'breakout', 'volatility', 'other']"  [arg-type]
src/strategy/service.py:500: error: Argument "track" to "StrategyBriefResponse" has incompatible type "str | None"; expected "Literal['S', 'A', 'M'] | None"  [arg-type]
Found 3 errors in 3 files (checked 230 source files)
```

셋 다 **경계에서 타입이 넓어진 것**이다 — `getattr` 로 얻은 핸들러, LLM 이 준 dict 의 값,
헬퍼의 반환 타입. 좁히는 자리는 각 경계다.

## 작업

세 에러를 **원인 자리에서** 없앤다. 벗어나면 안 되는 계약:

1. **`# type: ignore` 를 새로 넣지 마라.** 이유: 그것은 수리가 아니라 은폐이고, 이 lane 이
   step 3 에서 mypy 를 차단 게이트로 올리는 목적 자체를 무너뜨린다. AC 가 diff 를 검사한다.
2. **런타임 동작을 바꾸지 마라.** 지금 흐르는 값의 집합은 그대로여야 한다. 타입을 좁히려고
   값을 버리거나 예외로 바꾸지 마라.
3. `typing.cast` 는 **코드가 이미 그 타입을 보장할 때만** 쓰고, 왜 보장되는지 주석 1줄을 남겨라.
   보장이 없으면 cast 가 아니라 **좁히는 검사**(멤버십·`isinstance`)로 풀어라.
4. `narrative/service.py:130` 의 기존 `# type: ignore[arg-type]`(provider) 은 **건드리지 마라** —
   이 step 의 대상이 아니고, `warn_unused_ignores = True` 라 잘못 손대면 새 에러가 난다.

## Acceptance Criteria

`phases/ci-gates/index.json` 의 step 2 `ac` 와 동일하다. 요지:
`uv run mypy src` 가 `Success: no issues found in N source files` · diff 에 새 `type: ignore` 0건 ·
diff 가 비어 있지 않음(양성 대조) · 해당 3모듈의 BE 테스트 90건 통과.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. ★최종 판정은 러너가 재실행해 내린다 —
   `status` 를 `completed` 로 바꾸지 마라.
2. `pytest` 는 `.env.local` 통째 소싱이 의무다(AGENTS.md §5) — `DATABASE_URL` 단독 주입 금지.
3. 사람 개입이 필요하면 `status:"blocked"` + `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- `mypy.ini` 를 완화하지 마라(`strict` 해제 · 모듈별 `ignore_errors` 추가 · `exclude` 확대).
  이유: 3건을 없애려고 게이트를 무디게 만들면 이 lane 이 하는 일이 사라진다.
- 에러 3건과 무관한 파일을 리팩터하지 마라. 이유: 이 lane 은 게이트를 켜는 회차이지
  타입 대청소 회차가 아니다. 무관한 변경은 `openapi` diff 와 섞여 리뷰를 못 하게 만든다.
- `.github/workflows/ci.yml` 을 건드리지 마라(step 3 소관).
- `docs/status.md` · `docs/backlog.md` 를 건드리지 마라. 이유: lane 공유 파일이다.
- 커밋하지 마라(커밋은 러너 소관).
