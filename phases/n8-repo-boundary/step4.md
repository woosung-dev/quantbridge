# Step 4: mutation-selfcheck — 가드가 실제로 잡는지 증명한다

## 읽어야 할 파일

- **`phases/n8-common.md`** — 특히 「0건이니 통과를 믿지 마라」 절
- `apps/api/tests/common/test_repository_boundary_guard.py` — Step 0~3 산출
- `apps/api/src/trading/` — 변이를 심을 자리

## 작업

### 변이 2종 — 심고, red 를 확인하고, 반드시 복원한다

- **변이 ⑴ 새 위반** — 스코프 **안**의 파일(예: `src/trading/services/` 아무 파일)에
  `stmt = select(Order).where(Order.id == order_id)` 한 줄을 심는다. 가드가 **red** 여야 한다.
- **변이 ⑵ 동명이인 음성 대조** — 같은 자리에 `from numpy import select` 를 쓰는 형태나,
  스코프 **밖**(`src/tasks/` 또는 `src/common/`)에 진짜 `sqlmodel.select` 를 심는다.
  가드는 **green 이어야 한다**(위양성이 없다는 증거).

★**⑵ 가 red 가 나면 스코프 판정이 틀린 것**이다. 스코프를 넓히지 말고 판정 로직을 고쳐라.

★복원은 SHA 로 확인해라 — `shasum -a 256 <파일>` 을 변이 전후로 비교한다.

### 이 step 이 남겨야 할 테스트 (누적 6개 이상)

5. **음성 대조 고정** — 스코프 밖 디렉터리(`tasks/`·`common/`·`core/` 중 하나)에 실제로
   `sqlmodel.select` 호출이 존재하지만 위반으로 세지 않는다는 것을 단언한다.
   ★대상이 실재하는지 먼저 확인해라. 없으면 이 단언은 항진명제다 — 그때는 `repositor` 제외
   축(실제 repository 파일 안의 `select` 가 위반이 아님)으로 대체해라.
6. **동명이인 배제** — `sqlalchemy`/`sqlmodel` 이 아닌 출처의 `select` 이름은 안 센다.
   `optimizer/engine/genetic.py` 가 실측 제어군이다(스코프 밖이지만 판정 로직의 증인).

변이 결과는 `summary` 에 적어라 — 어느 변이가 어느 테스트를 어떤 메시지로 red 로 만들었는지.

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/common/test_repository_boundary_guard.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/common/test_repository_boundary_guard.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 6
cd apps/api && uv run --env-file .env.local pytest tests/trading tests/common -q
cd apps/api && uv run ruff check tests/common/test_repository_boundary_guard.py src/trading
cd apps/api && uv run ruff format --check tests/common/test_repository_boundary_guard.py
```

## 자기 점검

1. AC 를 직접 실행해 green 을 확인한다. `status` 를 바꾸지 마라.
2. **변이 복원을 SHA 로 확인한다.**
3. blocked 사유가 생기면 즉시 중단한다.

## 금지사항

- **변이를 커밋에 남기지 마라.** 이유: 다음 사람이 그것을 코드로 읽는다.
- **`xfail` 을 쓰지 마라.** 이유: 근거 없는 「제품 코드가 틀렸다」 주장이다. 2026-08-21 에
  phantom `xfail` 1건이 AC·변이·diff 세 층을 전부 통과했다.
- `phases/n8-common.md` 의 공통 금지사항 전부.
