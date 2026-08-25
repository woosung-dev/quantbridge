# Step 0: 백테스트 실행 속도 측정기 + 머신 독립 회귀 가드

## 읽어야 할 파일

- `apps/api/tests/strategy/pine_v2/_corpus.py` — `RUNNABLE_CORPUS`(7벌) 목록 **SSOT**. 여기서 import 해라
- `apps/api/tests/strategy/pine_v2/test_trust_layer_parity.py` 185~220행 — `_load_frozen_ohlcv()` 와
  `_extract_trades_and_runtime()`. **실행 호출 시그니처의 정본**이다
- `apps/api/tests/fixtures/pine_corpus_v2/baseline_metrics.json` 머리 12줄 — 기존 baseline JSON 의
  스키마 관례(`schema_version` · `ohlcv_sha256` · `generated_at` · `corpora`)

## 배경 — 착수 전 실측 (2026-08-25 CONTROL 측정)

`corpus_ohlcv_frozen.parquet` = **4,368 bar** (2024-01-01 ~ 2024-06-30, 1H).
`run_backtest_v2(source, df)` 를 직접 호출해 잰 값:

```
s3_rsid        run_backtest_v2= 21.74s   parse_and_run_v2=  5.11s    201 bar/s
s1_pbr         run_backtest_v2=  3.88s   parse_and_run_v2=  1.39s   1127 bar/s
s5_ema_trend   run_backtest_v2=  1.20s   parse_and_run_v2=  1.07s   3631 bar/s
```

**전략 간 18배 편차가 있다.** 이 회차가 존재하는 이유다 — `docs/PRD.md` §5 는
「단일 심볼 1Y/1H 백테스트 < 10초」라는 **전략 무관 단일 숫자**를 목표로 적어 뒀는데,
그 정의로는 같은 제품이 통과와 실패를 동시에 낸다. 게다가 그 숫자는 `89ff1d4e`(초기 프로젝트 설정)
에서 나왔고 **유도 근거가 어디에도 없다.**

★**이 step 은 느린 것을 고치지 않는다.** 재는 것과 못 박는 것까지가 범위다.

## 작업

### 1. `apps/api/tests/strategy/pine_v2/test_execution_speed.py` 신설

corpus 7벌을 `run_backtest_v2` 로 실행해 실행 시간을 재고, **커밋된 baseline 과 대조**한다.
`parse_and_run_v2` 소요도 함께 기록하되 `bars_per_second` 의 분모는 **`run_backtest_v2` 하나**다
(PRD 가 말하는 「백테스트」가 그것이다).

### 2. `apps/api/tests/fixtures/pine_corpus_v2/execution_speed_baseline.json` 생성

스키마는 아래를 그대로 쓴다. 필드를 빼지 마라 — step1·step3 이 읽는다.

```json
{
  "schema_version": 1,
  "generated_at": "<UTC ISO8601>",
  "ohlcv_sha256": "<parquet sha256 — 기존 baseline_metrics.json 과 같은 값이어야 한다>",
  "bars": 4368,
  "machine": { "platform": "<platform.platform()>", "python": "<3.12>" },
  "corpora": {
    "<corpus_id>": {
      "run_backtest_seconds": 21.74,
      "parse_and_run_seconds": 5.11,
      "bars_per_second": 200.9,
      "ratio_to_fastest": 18.1
    }
  }
}
```

`ratio_to_fastest` = `(가장 빠른 corpus 의 bars_per_second) / (이 corpus 의 bars_per_second)`.
가장 빠른 corpus 자신은 `1.0` 이다.

**재생성 경로를 반드시 만들어라** — 환경변수 `REGEN_EXECUTION_SPEED=1` 이 설정된 경우에만
baseline 을 덮어쓴다. 없으면 **읽기 전용으로 대조만** 한다. 이유: 가드가 자기 기준을 자동으로
갱신하면 회귀가 영원히 감지되지 않는다(이 레포가 「빈 입력이 초록으로」로 여러 번 밟은 형태다).

### 3. 가드 테스트 — 최소 3건

| 테스트 | 단언 |
| --- | --- |
| corpus 전건 존재 | baseline `corpora` 키 집합 == `RUNNABLE_CORPUS` (양방향). 누락·잉여 둘 다 잡아라 |
| 상대비 회귀 | 각 corpus 의 **재측정 `ratio_to_fastest`** 가 baseline 값의 **2.0배를 넘지 않는다** |
| **양성 대조** | baseline 을 **메모리에서 조작한 사본**(어느 corpus 의 `ratio_to_fastest` 를 10배로)을 판정 함수에 넣으면 실패한다 |

★**양성 대조는 이 step 의 필수 산출이다.** 「0건이니 통과」는 대상에 닿지 않아도 참이다 —
판정 로직을 **함수로 분리**해 테스트가 조작된 입력으로 부를 수 있게 만들어라.

## 왜 절대 시간이 아니라 상대비인가

측정 머신이 다르면 `bars_per_second` 의 절대값이 통째로 움직인다. GitHub runner 는 이 개발
머신보다 느리고, 그 차이는 임계를 아무리 관대하게 잡아도 흡수되지 않는다. 반면
**corpus 사이의 비율은 같은 실행 안에서 재므로 머신에 불변**이다 — 코드가 느려질 때만 움직인다.

`bars_per_second` 절대값은 **기록만** 하고 단언하지 마라. 그 숫자는 step3 이 PRD 에 옮겨 적는다.

## Acceptance Criteria

```bash
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/strategy/pine_v2/test_execution_speed.py -q
cd apps/api && set -a; . ./.env.local; set +a; test "$(uv run pytest tests/strategy/pine_v2/test_execution_speed.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 3
cd apps/api && uv run python -c "import json,sys; d=json.load(open('tests/fixtures/pine_corpus_v2/execution_speed_baseline.json')); c=d['corpora']; assert len(c)==7, len(c); assert all(v['bars_per_second']>0 for v in c.values()); assert all('ratio_to_fastest' in v for v in c.values()); print('ok', len(c))"
cd apps/api && uv run ruff check tests/strategy/pine_v2
```

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. ★최종 판정은 러너가 재실행해 내린다 —
   `status` 를 `completed` 로 바꾸지 마라.
2. **판별력 확인** — 양성 대조 테스트를 임시로 뒤집어(조작 사본이 아니라 원본을 넣어) 그 테스트가
   red 가 되는지 본다. red 가 안 나면 그 테스트는 항진명제다.
3. 전체 실행이 60초를 넘으면 `summary` 에 실측 소요를 적어라 — 다음 step 이 그 예산 위에서 돈다.

## 금지사항

- **절대 시간(초)을 단언에 쓰지 마라.** 이유: 머신 성능 차이로 간헐 red 가 되고, 그러면 다음 사람이
  가드를 꺼 버린다. 이 레포는 「AC 가 간헐 red」를 이미 실패 모드로 기록해 뒀다.
- **`src/` 를 수정하지 마라.** 이유: 이 회차는 측정이다. 무엇이 느린지 모르는 상태에서 손대면
  step2 의 프로파일이 이미 바뀐 코드를 재게 된다.
- **`baseline_metrics.json` 을 건드리지 마라.** 이유: 그것은 **golden 지표 회귀**의 기준이고
  속도와 별개 축이다. 같은 파일에 속도를 섞으면 한쪽 재생성이 다른 쪽을 오염시킨다.
- **`_corpus.py` 의 목록을 복사하지 마라.** import 해라. 이유: [BL-588] 이 그 목록의 사본 3벌 중
  하나가 5벌에서 멈춰 있어 mutation oracle 이 2벌을 영원히 놓친 사고를 기록하고 있다.
- 커밋하지 마라(커밋은 러너 소관).
