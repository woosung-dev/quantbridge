# Step 1: 실행 시간을 단계별로 가른다 — 어디가 느린가

## 읽어야 할 파일

- `apps/api/src/backtest/engine/v2_adapter.py` 52~200행 — `run_backtest_v2` 본문. 단계 경계가 여기 있다
- `apps/api/src/strategy/pine_v2/compat.py` 42~90행 — `parse_and_run_v2` 의 `classify_script` → runner dispatch
- `apps/api/tests/fixtures/pine_corpus_v2/execution_speed_baseline.json` — **step0 산출**. 어느 corpus 가
  느린지의 정본이다
- `apps/api/tests/strategy/pine_v2/test_execution_speed.py` — **step0 산출**. 측정 헬퍼를 재사용해라

## 배경 — step0 이 답하지 못한 것

step0 은 「s3_rsid 가 18배 느리다」까지만 안다. **무엇이** 느린지는 모른다.
CONTROL 이 착수 전에 잰 값이 이미 하나를 시사한다:

```
s3_rsid   run_backtest_v2 = 21.74s      parse_and_run_v2(단독 호출) = 5.11s
```

`run_backtest_v2` 는 **내부에서 `parse_and_run_v2` 를 호출한다**(`v2_adapter.py:97`).
그런데 단독 호출은 5.11초다. 차이 16.6초의 정체는 둘 중 하나이며 **아직 모른다**:

- ⑴ `run_backtest_v2` 가 `strict=True` + `initial_capital`/`leverage` 를 넘겨 **사이징이 활성화**되고,
  그래서 같은 스크립트가 더 많은 일을 한다
- ⑵ `parse_and_run_v2` 이후의 후처리(`_build_raw_trades` → `_compute_equity_curve` →
  `_compute_metrics`)가 오래 걸린다

**이 step 의 산출은 그 둘을 가르는 숫자다.** 추측을 적지 마라 — 재라.

## 작업

### 1. `apps/api/tests/strategy/pine_v2/test_execution_stage_breakdown.py` 신설

`monkeypatch` 로 아래 경계 함수를 래핑해 **누적 소요를 구간별로 적산**한다.
`src/` 를 고치지 마라 — 계측은 테스트 쪽에서만 한다.

| 구간 키 | 대상 |
| --- | --- |
| `parse` | `src.strategy.pine_v2.compat` 이 부르는 `classify_script` |
| `execute` | `parse_and_run_v2` 전체 − `parse` (= runner 의 bar 루프) |
| `trades` | `v2_adapter._build_raw_trades` |
| `equity` | `v2_adapter._compute_equity_curve` + `_compute_equity_extremes` |
| `metrics` | `v2_adapter._compute_metrics` |

`funding` 구간은 이 corpus 에 funding_rates 가 없어 no-op 이다 — 넣어도 되고 빼도 된다.

### 2. `apps/api/tests/fixtures/pine_corpus_v2/execution_stage_breakdown.json` 생성

**최소한 `s3_rsid`(가장 느림) 와 `s5_ema_trend`(가장 빠름) 두 벌**을 담아라. 7벌 전부 재면
소요가 커지므로, 나머지는 넣어도 되지만 의무가 아니다.

```json
{
  "s3_rsid": {
    "total_seconds": 21.74,
    "stages": { "parse": 0.0, "execute": 0.0, "trades": 0.0, "equity": 0.0, "metrics": 0.0 },
    "unaccounted_seconds": 0.0
  }
}
```

`unaccounted_seconds` = `total_seconds − sum(stages)`. **이 값을 숨기지 마라** — 구간 합이 전체의
90% 에 못 미치면 계측이 경계를 놓친 것이고, 그 사실 자체가 산출이다.

### 3. 단언 — 최소 2건

| 테스트 | 단언 |
| --- | --- |
| 구간 커버리지 | `sum(stages) / total_seconds >= 0.90`. 미달이면 **어느 구간이 빠졌는지** 실패 메시지에 적어라 |
| 지배 구간 식별 | `s3_rsid` 의 최대 구간이 JSON 에 기록돼 있고, 그 구간이 전체의 **50% 이상**을 차지한다 |

★두 번째 단언이 **50% 를 못 넘으면 그것도 산출이다** — 「병목이 하나가 아니다」가 답이 된다.
그 경우 단언을 억지로 통과시키지 말고 **임계를 실측값에 맞춰 낮추고 `summary` 에 이유를 적어라.**
AC 를 통과시키려고 실측을 왜곡하는 것이 이 도구가 가장 경계하는 실패다.

## Acceptance Criteria

```bash
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/strategy/pine_v2/test_execution_stage_breakdown.py -q
cd apps/api && set -a; . ./.env.local; set +a; test "$(uv run pytest tests/strategy/pine_v2/test_execution_stage_breakdown.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 2
cd apps/api && uv run python -c "import json; d=json.load(open('tests/fixtures/pine_corpus_v2/execution_stage_breakdown.json')); s=d['s3_rsid']['stages']; assert set(s)>= {'parse','execute','metrics'}, sorted(s); assert all(v>=0 for v in s.values()); cov=sum(s.values())/d['s3_rsid']['total_seconds']; assert cov>=0.90, cov; print('coverage', round(cov,3))"
cd apps/api && uv run ruff check tests/strategy/pine_v2
```

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. **판별력 확인** — 래핑 대상 하나를 임시로 빼고 돌려 `unaccounted_seconds` 가 그만큼 커지는지 본다.
   안 커지면 그 래퍼는 아무것도 재고 있지 않았다.
3. `summary` 에 **⑴ 과 ⑵ 중 무엇이었는지**를 숫자와 함께 적어라. step2 가 그 위에서 프로파일한다.

## 금지사항

- **`src/` 를 수정하지 마라.** 계측 코드를 제품 코드에 넣으면 그 자체가 오버헤드가 되고, 다음 회차가
  그것을 지우는 일부터 하게 된다. `monkeypatch` 로 충분하다.
- **추정치를 JSON 에 적지 마라.** 재지 못한 구간은 `unaccounted_seconds` 로 남겨라. 이 레포는
  「적혀 있다 ≠ 그렇게 동작한다」를 8건 한꺼번에 밟은 적이 있다.
- **step0 의 baseline JSON 을 갱신하지 마라.** 이 step 은 읽기만 한다.
- 커밋하지 마라(커밋은 러너 소관).
