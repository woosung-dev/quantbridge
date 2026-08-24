# Step 8: 고장 주입 self-check — 「감쌌다」가 실제로 막는지 증명한다

## 읽어야 할 파일

- `apps/api/tests/tasks/test_closed_pnl_sweep_metric_failure.py` — **선례.** `.labels()` 에 예외를 주입한다
- `apps/api/src/common/metrics_multiproc.py` — 가드 3종
- 이전 step 들의 `summary` — 무엇을 어디서 감쌌는지

## 배경

앞 step 들은 **정적 검사기**(census · labels-outside-guard)로 판정했다. 정적 검사기는
「그 자리에 가드 이름이 있다」만 말한다 — **런타임에 실제로 막는지는 말하지 않는다.**

이 레포는 정확히 그 간극에서 두 번 탔다:

- 「가드가 있다」와 「그 경로가 지나는가」는 다른 축이다([LESSON-087] — ★로 표시한 가드에 커버리지 0)
- 변이가 파일에 도달해도 **그 경로가 안 돌면 무증거**다

이 step 은 **가드가 예외를 실제로 삼키는지**를 런타임으로 증명한다.

## 작업

`.labels()` 에 예외를 주입해 **업무 경로가 살아남는지** 재는 테스트를 신설한다.

- 테스트 이름에 **`metric_failure_does_not_escape`** 를 포함시켜라(러너 AC 가 `-k` 로 건다)
- 주입 지점은 **`.labels()`** 다. `.inc()` 만 터뜨리면 이번 회차가 고친 결함을 못 잰다 —
  선례 파일의 `_explode_labels` 방식을 따라라
- **서로 다른 도메인 4곳 이상**을 덮어라. 앞 step 들이 감싼 파일 중에서 고르되,
  최소한 **머니-패스 1건**(`tasks/trading.py` 또는 `tasks/live_signal.py`)과
  **락/기반 1건**(`common/redlock.py` 등)을 포함해라
- 각 테스트의 단언은 **업무 결과**여야 한다 — 「예외가 안 났다」가 아니라
  「주문이 체결로 기록됐다」·「락이 해제됐다」처럼 **그 함수가 하려던 일이 끝났는가**를 재라

★**음성 대조를 함께 넣어라** — 가드를 우회한 형태(`record_metric_safely(C.labels(..).inc)`)를
테스트 안에서 국소적으로 만들어, 그 형태에서는 예외가 **빠져나가는지** 확인해라.
이것이 없으면 테스트가 「원래 안 터지는 자리」를 재고 있어도 초록이다.

## Acceptance Criteria

```bash
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/tasks tests/trading tests/common -k metric_failure_does_not_escape -q
cd apps/api && set -a; . ./.env.local; set +a; test "$(uv run pytest tests/tasks tests/trading tests/common -k metric_failure_does_not_escape --collect-only -q 2>/dev/null | grep -c '::')" -ge 4
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/common/test_metric_guard_census.py tests/common -k 'census or labels_outside_guard' -q
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/tasks tests/trading tests/common -q
```

두 번째가 **양성 대조**(4건 미만이면 red), 네 번째가 **광역 회귀**다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. ★**변이로 판별력을 증명해라** — 감싼 자리 **하나**를 원래의 raw 형태로 되돌리고 새 테스트가
   red 가 되는지 확인한 뒤 **반드시 원복**해라. 앵커가 1건인지 먼저 세고(0 이면 못 심은 것,
   2 이상이면 어디가 바뀌었는지 모른다), 원복은 `git diff --stat` 으로 확인해라.
3. `summary` 에 **회차 총결산**을 남겨라: 감싼 자리 수 · `_FROZEN_CENSUS` 최종 항목/합 ·
   allowlist 항목 수 · 신설 테스트 수 · 변이 결과. CONTROL 이 이것으로 원장을 닫는다.
4. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- **`try/except Exception: pass` 로 테스트를 통과시키지 마라.** 이유: 그것은 가드가 아니라 은폐다.
- **주입을 `.inc()` 에만 걸지 마라.** 이유: 이번 회차가 고친 결함은 `.labels()` 축이다.
  `.inc()` 만 터뜨리면 수리 전에도 초록이 난다 — 판별력 0.
- **`xfail(strict=True)` 를 쓰지 마라.** 이유: 그것은 「제품 코드가 틀렸다」는 주장을 원장에 박는 것이고,
  코드 대조 없이 쓰면 AC·변이·diff 세 층이 전부 통과시킨 전례가 있다([LESSON-121]).
- **`docs/status.md`·`docs/backlog.md`·가드레일 4축을 수정하지 마라.**
- **최상위 `phases/index.json` 을 수정하지 마라.**
- 커밋하지 마라(커밋은 러너 소관).
