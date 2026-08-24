# Step 0: `uv run mypy src` 를 에러 0 으로 만든다

## 읽어야 할 파일

- `apps/api/mypy.ini` — 설정 정본(`strict = True` · `warn_unused_ignores = True` · `exclude = (alembic/versions|tests)`)
- `apps/api/src/trading/repositories/order_repository.py` 355~362행

## 배경 — 착수 전 실측 (2026-08-25 CONTROL 측정)

```
src/trading/repositories/order_repository.py:359: error: Unused "type: ignore" comment  [unused-ignore]
src/trading/repositories/order_repository.py:360: error: Argument 1 to "where" of "Select" has incompatible type "bool"; ...  [arg-type]
Found 2 errors in 1 file (checked 219 source files)
```

**한 파일 · 두 줄 · 인접**이다. 형태는 이렇다:

```python
result = await self.session.execute(
    select(Order).where(  # type: ignore[arg-type]   ← 359: 여기선 불필요
        Order.exchange_order_id == exchange_order_id  # ← 360: 여기가 필요한 자리
    )
)
```

`# type: ignore` 는 **에러가 보고되는 줄**에 붙어야 한다. 여러 줄로 나뉜 호출에서 `where(` 줄에
붙이면 mypy 는 그 줄에 억제할 에러가 없다고 보고(`unused-ignore`), 정작 인자 줄은 무방비다.
바로 위 `get_by_idempotency_key`(352행)가 **한 줄 형태라 올바르게 동작하는 대조군**이다.

★**CI 에 mypy 잡을 추가하지 마라.** 이유: mypy 는 [ADR-037] 제로베이스가 **의도적으로 걷어낸**
것이다(`ci.yml` 헤더의 「지운 것」 목록에 이름이 있다). 재입힘은 「문서화된 사고 1건 = 슬림 복귀 1건」
규칙을 따라야 하고 그 판단은 사용자·CONTROL 소관이다. 이 step 의 범위는 **로컬 rc=0** 까지다.

## 작업

두 에러를 없앤다. 방법은 둘 중 하나이며 **너의 판단이다**:

- ⑴ ignore 주석을 에러가 보고되는 줄(인자 줄)로 옮긴다 — 최소 변경
- ⑵ 인접 메서드처럼 표현식을 한 줄로 합쳐 형태를 맞춘다

어느 쪽이든 **`# type: ignore` 를 새로 늘리지 마라.** 순증이 0 이하여야 한다.
`type: ignore[...]` 는 **코드를 명시**해라 — bare ignore 금지(`strict` 하에서 다른 에러를 함께 숨긴다).

★**다른 파일을 손대지 마라.** 에러는 이 한 파일에 있다. 「지나가는 김에」 다른 타입을 고치면
이 lane 의 diff 가 다른 lane 과 겹칠 위험이 생긴다.

## Acceptance Criteria

```bash
cd apps/api && uv run mypy src
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/trading -q
cd apps/api && uv run ruff check src/trading/repositories
```

첫 번째가 이 step 의 판정이다 — mypy 는 에러가 있으면 rc≠0 이다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. **판별력 확인** — 수리한 자리의 ignore 를 임시로 지워 `uv run mypy src` 가 red 가 되는지 보고
   **반드시 원복**해라(`git diff --stat`). red 가 안 나면 그 ignore 는 애초에 불필요했던 것이고,
   그렇다면 지우는 것이 정답이다.
3. `git diff` 로 **변경이 그 한 파일에만** 있는지 확인해라.
4. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- **`.github/workflows/**` 를 수정하지 마라.** 이유: mypy CI 편입은 [ADR-037] 재입힘 규칙의
  대상이라 사용자 결정이 선행한다. 또한 그 디렉터리는 다른 lane 의 소유 구역이다.
- **`mypy.ini` 의 엄격도를 낮추지 마라**(`strict` 해제 · `ignore_errors` 추가 · exclude 확대).
  이유: 에러 2건을 설정으로 지우는 것은 수리가 아니다.
- **`# type: ignore` 를 새로 늘리지 마라.** 이유: 살아 있는 ignore 가 이미 488건이다.
- **`tests/common/**` · `tests/scripts/**` · `src/tasks/**` · `src/common/**` 를 만지지 마라.**
  이유: 다른 lane 의 소유 구역이다.
- **`docs/**` · `CONTEXT.md` · `AGENTS.md` 계열 · `phases/index.json` 을 수정하지 마라.**
- 커밋하지 마라(커밋은 러너 소관).
