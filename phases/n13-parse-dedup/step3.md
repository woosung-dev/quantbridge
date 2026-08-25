# Step 3: regen-execution-fixtures

## 읽어야 할 파일

- 앞 세 step 의 `summary`
- `apps/api/tests/strategy/pine_v2/test_execution_hotspots.py` (`_REGEN_ENV = "REGEN_EXECUTION_HOTSPOTS"`)
- `apps/api/tests/strategy/pine_v2/test_execution_speed.py` (`_REGEN_ENV = "REGEN_EXECUTION_SPEED"`)
- `apps/api/tests/strategy/pine_v2/test_execution_stage_breakdown.py`
- `apps/api/tests/fixtures/pine_corpus_v2/execution_{hotspots,speed_baseline,stage_breakdown}.json`

## 작업

step 1 이 파스 횟수를 4→1 로 바꿨으므로 세 픽스처의 수치가 전부 낡았다. 재생성한다.

**순서 고정** — hotspots 먼저, speed 나중:

```
cd apps/api && set -a; . ./.env.local; set +a; REGEN_EXECUTION_HOTSPOTS=1 uv run pytest tests/strategy/pine_v2/test_execution_hotspots.py -q
cd apps/api && set -a; . ./.env.local; set +a; REGEN_EXECUTION_SPEED=1 uv run pytest tests/strategy/pine_v2/test_execution_speed.py -q
```

`execution_stage_breakdown.json` 은 **재생성 경로가 레포에 없다**(REGEN env 도 writer 함수도 0건).
`test_execution_stage_breakdown.py` 를 읽어 그 테스트가 계산하는 값과 같은 방식으로 **손으로** 갱신하고,
`unaccounted_seconds` 를 포함한 내부 정합이 맞는지 테스트로 확인해라.
★이 파일에 재생성 수단이 없다는 사실 자체를 `summary` 에 적어라.

## ★이 step 이 반드시 기록해야 할 것 — 픽스처의 알려진 결함

재생성은 **아래 결함을 고치지 않는다.** 고치는 것은 이 회차의 범위가 아니다. 그러나 **덮어쓰기 전에
알고 있어야** 다음 사람이 이 숫자를 잘못 읽지 않는다. `summary` 에 그대로 옮겨 적어라:

1. **`execution_speed_baseline.json` 은 실행 순서에 오염돼 있다.** `test_execution_speed.py:56` 이
   단일 프로세스에서 `RUNNABLE_CORPUS` 를 순서대로 돌고 `bars_per_second` 를 **콜드 호출**로만 잰다.
   첫 corpus 만 온전한 콜드 비용을 물고 나머지는 앞 corpus 가 데운 DFA 를 물려받는다.
   그래서 20줄짜리 `s1_pbr` 의 `ratio_to_fastest` 8.43 이 42줄짜리 `s4_hma_curvature` 의 2.19 보다 나쁘다.
   같은 `s3_rsid` 가 breakdown(자기 프로세스 1번째) 21.752s vs speed(3번째) 14.471s — **50% 차이가
   순서 하나에서 난다.** 격리 실측(corpus 당 새 프로세스, median-of-3)의 진짜 콜드는
   `s1_pbr` 5.35s · `s3_rsid` 11.55s · `s5_ema_trend` 2.61s · `i3_drfx` 52.37s 다.
2. **`execution_stage_breakdown.json` 의 `parse` 는 그 실행의 총 파싱 시간이 아니다.**
   계측 래퍼가 `classify_script` **하나만** 감싼다(`test_execution_stage_breakdown.py:49-53`).
   나머지 파스는 `execute` 구간 안에 숨는다.
3. **`test_execution_stage_breakdown.py:87`** 의 `parse_and_run >= parse` 부등식은 파스 진입점이
   `classify_script` 바깥으로 나가면 깨진다. step 1 은 진입점을 옮기지 않았으므로 유지되어야 한다 —
   **깨졌다면 그것은 이 step 이 아니라 step 1 이 범위를 벗어났다는 신호다.** `blocked` 로 멈춰라.

## Acceptance Criteria

```
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/strategy/pine_v2/test_execution_hotspots.py -q
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/strategy/pine_v2/test_execution_speed.py -q
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/strategy/pine_v2/test_execution_stage_breakdown.py -q
```

★AC 는 **REGEN 없이** 돈다 — 저장된 픽스처가 현재 코드와 정합인지가 판정 대상이다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 ⑴ 재생성 전/후의 `s5_ema_trend`(또는 step 0 이 고른 corpus)의 파스 관련 수치
   ⑵ 위 「알려진 결함」 3건 ⑶ stage_breakdown 을 어떻게 갱신했는지를 적어라.
3. 사람 개입이 필요하면 `status:"blocked"` + `blocked_reason` 후 즉시 중단.

## 금지사항

- **픽스처를 손으로 편집해 AC 를 통과시키지 마라**(stage_breakdown 은 예외 — 재생성 수단이 없다).
  이유: 그러면 픽스처가 코드의 증인이 아니라 AC 의 사본이 된다.
- **위 「알려진 결함」을 이 step 에서 고치지 마라.** 이유: 측정 구조를 바꾸면 이 회차의 전/후 비교가
  무엇 때문에 움직였는지 갈리지 않는다. 원장에 별건으로 올리는 것이 CONTROL 의 일이다.
- 커밋하지 마라(커밋은 러너 소관).
