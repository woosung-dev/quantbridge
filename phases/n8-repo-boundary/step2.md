# Step 2: move-dependencies-queries — `trading/dependencies.py` 의 쿼리 4건을 repository 로 옮긴다

## 읽어야 할 파일

- **`phases/n8-common.md`**
- `apps/api/src/trading/dependencies.py` — 옮길 쿼리 4건이 있는 자리
- `apps/api/src/trading/repositories/` — 11개 repository. **가장 가까운 것을 골라 메서드를 추가한다**
- `apps/api/src/strategy/repository.py` · `apps/api/src/auth/` — 어느 도메인이 `Strategy`·`User` 를 소유하는지 확인
- `apps/api/tests/trading/` — 기존 회귀. 여기가 green 이어야 한다
- `apps/api/tests/common/test_repository_boundary_guard.py` — Step 0·1 산출

## 작업

`trading/dependencies.py` 의 `select(...)` **4건을 전부 제거**하고, 각 쿼리를 소유 도메인의
repository 메서드로 옮긴다.

CONTROL 실측 좌표(재확인해라): `:159`·`:168` `select(Strategy)` · `:183` `select(User)` · 나머지 1건.

### 벗어나면 안 되는 계약

- **동작을 바꾸지 마라.** 이 step 은 **위치 이동**이다. 반환 타입·예외·`None` 처리·
  `HTTPException` 의 status·detail 을 그대로 유지해라. 기존 `tests/trading` 이 증인이다.
- **소유 도메인의 repository 에 넣어라.** `Strategy` 는 `strategy` 도메인이, `User` 는 `auth`
  도메인이 소유한다. `trading` 의 repository 에 남의 엔티티 쿼리를 넣지 마라 —
  경계를 옮기는 것이 목적인데 다른 경계를 깨면 순손실이다.
- **세션은 인자로 받아라.** repository 가 세션을 만들지 않는다.
- ★**`# type: ignore[arg-type]` 주석이 붙어 있다.** 옮긴 뒤에도 타입 검사가 통과하는지 확인해라 —
  주석을 그냥 따라 옮기지 말고, 필요 없어졌으면 지워라.

### 동결 목록 갱신

Step 1 의 `_FROZEN_VIOLATIONS` 에서 `trading/dependencies.py` 항목을 **지워라.**
「죽은 동결 금지」 래칫이 red 를 낼 것이다 — 그것이 이 step 이 실제로 고쳤다는 증거다.

## Acceptance Criteria

```bash
test "$(grep -c 'select(' apps/api/src/trading/dependencies.py)" -eq 0
cd apps/api && uv run --env-file .env.local pytest tests/common/test_repository_boundary_guard.py -q
cd apps/api && uv run --env-file .env.local pytest tests/trading -q
cd apps/api && uv run ruff check src/trading
```

## 자기 점검

1. AC 를 직접 실행해 green 을 확인한다. `status` 를 바꾸지 마라.
2. **`tests/trading` 이 이 step 의 증인이다** — 하나라도 red 면 동작을 바꾼 것이다.
3. blocked 사유가 생기면 즉시 중단한다.

## 금지사항

- **동작을 바꾸지 마라.** 이유: 이 step 은 이동이다. 기능 변경은 별도 회차의 일이다.
- **테스트를 고쳐서 green 을 만들지 마라.** 이유: 기존 회귀가 계약이다. 테스트가 틀렸다고
  판단되면 고치지 말고 `summary` 에 근거와 함께 적어라.
- **`raw SQL` 문자열로 도피하지 마라.** 이유: `grep -c 'select('` 를 0으로 만드는 우회로일 뿐
  경계는 그대로 깨져 있다.
- `phases/n8-common.md` 의 공통 금지사항 전부.
