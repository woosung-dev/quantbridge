# Step 2: 가장 느린 corpus 의 hotspot 을 프로파일로 특정한다 — **수리하지 않는다**

## 읽어야 할 파일

- `apps/api/tests/fixtures/pine_corpus_v2/execution_stage_breakdown.json` — **step1 산출**.
  어느 구간이 지배적인지가 여기 있다. 프로파일은 그 구간을 겨눈다
- `apps/api/tests/strategy/pine_v2/test_execution_speed.py` — **step0 산출**. corpus 로딩 헬퍼 재사용
- `apps/api/src/strategy/pine_v2/event_loop.py`(814줄) · `interpreter.py`(1,760줄) ·
  `strategy_state.py`(1,391줄) — bar 루프의 무게가 실린 곳들. **읽기 전용**

## 배경

step1 이 「어느 **구간**」까지 답했다. 이 step 은 「어느 **함수**」까지 내린다.
`s3_rsid`(RSI divergence)는 201 bar/s 이고 `s5_ema_trend` 는 3,631 bar/s 다 — 같은 엔진, 같은
4,368 bar 인데 18배다. 그 차이를 만드는 코드가 반드시 존재한다.

★**이 step 은 고치지 않는다.** 이유는 회차 설계에 있다: 무엇이 느린지 모르는 상태에서 수리
step 을 저작하면 AC 를 **추측 위에** 써야 하고, 그러면 러너는 「돌았다」만 보증한다. 수리는
이 회차의 산출을 읽은 뒤 **다음 회차**가 정한다.

## 작업

### 1. `apps/api/tests/strategy/pine_v2/test_execution_hotspots.py` 신설

`cProfile` + `pstats` 로 `run_backtest_v2(s3_rsid)` 를 프로파일하고, **누적 시간(cumulative) 상위
함수**를 추출한다. 비교군으로 `s5_ema_trend` 도 함께 프로파일해라 — 18배의 원인은 **s3 에만 있는
호출** 이거나 **양쪽에 있지만 s3 에서 호출 횟수가 폭증하는 것** 이고, 비교군 없이는 그 둘을 못 가른다.

### 2. `apps/api/tests/fixtures/pine_corpus_v2/execution_hotspots.json` 생성

```json
{
  "s3_rsid": {
    "total_seconds": 21.74,
    "hotspots": [
      {
        "function": "<함수명>",
        "file": "src/strategy/pine_v2/<...>.py",
        "line": 0,
        "call_count": 0,
        "cumulative_seconds": 0.0,
        "tottime_seconds": 0.0
      }
    ]
  },
  "s5_ema_trend": { "...": "동일 구조" },
  "call_count_ratio": {
    "<함수명>": { "s3_rsid": 0, "s5_ema_trend": 0, "ratio": 0.0 }
  }
}
```

- `hotspots` 는 **최소 5개**. 경로는 `apps/api/` 기준 상대경로로 정규화해라(절대경로를 커밋하면
  다른 머신에서 무의미해진다)
- `call_count_ratio` 는 두 corpus 에 **모두 등장하는** 함수만 담고 `ratio` = s3 호출수 / s5 호출수.
  **이 표가 이 step 의 핵심 산출**이다 — 18배의 원인이 호출 폭증이면 여기에 그대로 드러난다

### 3. 단언 — 최소 2건

| 테스트 | 단언 |
| --- | --- |
| hotspot 실재 | 상위 5개 중 **`src/` 경로가 하나 이상**이다(전부 stdlib·pandas 면 우리 코드 밖이라는 뜻이고, 그것도 산출이지만 그때는 `summary` 에 명시해라) |
| **phantom 차단** | 기록된 각 `function`/`file`/`line` 이 **실제 소스에 존재**한다 — `ast` 로 그 파일을 파싱해 같은 이름의 `FunctionDef`/`AsyncFunctionDef` 가 있는지 확인 |

★**두 번째가 이 step 의 필수 산출이다.** 이 레포는 「원장에 적힌 좌표가 코드에 없더라」를 반복해
밟았고(죽은 앵커·phantom finding), 프로파일 출력은 `<built-in>`·`<listcomp>` 같은 **파일이 아닌
항목**을 섞어 낸다. `src/` 가 아닌 항목은 AST 검사에서 **건너뛰되 JSON 에는 남겨라**.

## Acceptance Criteria

```bash
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/strategy/pine_v2/test_execution_hotspots.py -q
cd apps/api && set -a; . ./.env.local; set +a; test "$(uv run pytest tests/strategy/pine_v2/test_execution_hotspots.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 2
cd apps/api && uv run python -c "import json; d=json.load(open('tests/fixtures/pine_corpus_v2/execution_hotspots.json')); h=d['s3_rsid']['hotspots']; assert len(h)>=5, len(h); assert all(x['cumulative_seconds']>0 for x in h); assert any('src/' in x['file'] for x in h), [x['file'] for x in h]; print('ok', len(h))"
cd apps/api && uv run ruff check tests/strategy/pine_v2
```

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. **판별력 확인** — JSON 의 `function` 하나를 존재하지 않는 이름으로 임시 조작해 phantom 차단
   테스트가 red 가 되는지 본다.
3. `summary` 에 **18배의 원인 가설 1문장 + 그 근거 숫자**를 적어라. 다음 회차의 수리 lane 이
   그 문장 위에 AC 를 쓴다. 가설이 안 서면 「안 선다」를 적어라 — 지어내지 마라.

## 금지사항

- **`src/` 를 수정하지 마라.** 이 step 은 관측이다. 한 줄이라도 고치면 그 아래 프로파일 숫자가
  전부 다른 코드의 것이 된다.
- **cProfile 오버헤드를 무시하고 절대값을 baseline 과 비교하지 마라.** 프로파일러가 붙으면 실행이
  느려진다 — 이 step 의 숫자는 **함수 사이의 상대 비교**에만 쓴다. step0 baseline 을 갱신하지 마라.
- **상위 함수를 손으로 골라 적지 마라.** `pstats` 가 정렬한 결과를 그대로 직렬화해라. 사람이 고른
  목록은 다음 사람이 검증할 수 없다.
- 커밋하지 마라(커밋은 러너 소관).
