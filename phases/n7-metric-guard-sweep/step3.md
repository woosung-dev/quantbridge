# Step 3: 변이 자기검사 — metric 을 **실제로 죽여** 주문 경로가 사는지 본다

## 읽어야 할 파일

- **`phases/n7-common.md`** — 특히 「0건이니 통과를 믿지 마라」 절
- `apps/api/src/common/metrics_multiproc.py` — `record_metric_safely` 가 **무엇을 삼키는지**
- Step 1·2 가 감싼 4자리

## 왜 이 step 이 있나

지금까지의 AC 는 전부 **정적**이다 — census 가 「감싸졌다고 말한다」를 잰다.
**「감싸졌으니 실제로 안 막는다」는 아직 아무도 안 쟀다.**

이 레포는 그 구별을 비싸게 배웠다. 「돌았다 ≠ 발화했다」 · 「변이가 파일에 도달해도 그 경로가
안 돌면 무증거」 · 「★로 표시한 가드에 커버리지 0」. **이 step 의 산출은 코드가 아니라 증거다.**

## 작업

1. **런타임 변이 — metric 을 실제로 던지게 만든다.**
   Step 1 의 자리 ①(`live_signal.py` 의 sweep filled)에서, `qb_live_conditional_sweep_filled_total`
   의 mutation 이 **예외를 던지도록** 테스트에서 patch 한다.
   - **기대**: 주문은 여전히 **`filled`** 로 처리되고 `sweep_cancel_failed` 로 **안 뒤집힌다**
   - ★이것이 [BL-520] 이 지키려는 계약의 **유일한 직접 증인**이다
2. **음성 대조** — 같은 예외를 **가드 밖 자리**(아직 `_FROZEN_CENSUS` 에 남아 있는 아무 자리)에
   주입하면 **여전히 경로가 깨져야** 한다. 안 깨지면 이 테스트는 무엇도 재고 있지 않다.
3. **모양 B 도 한 건 재라** — `webhook.py` 또는 `realtime_publisher.py` 의 `except` 본문에서
   metric 이 던져도 **예외가 밖으로 안 새는지**.
4. ★**도달 확인** — 각 변이가 **그 코드 경로를 실제로 지났는지** 따로 확인해라.
   도달 못 한 변이의 「안 깨졌다」는 **무증거**다. (해당 함수가 호출됐는지 · 분기를 탔는지)
5. 케이스를 추가해 census 파일 총 **9건 이상**으로 만든다.

★**소스를 고치지 마라.** 이 step 은 patch/mock 으로 런타임 행동만 잰다.
Step 1·2 가 이미 소스를 고쳤고, 여기서 또 고치면 무엇이 증거인지 흐려진다.

## Acceptance Criteria

1. `cd apps/api && uv run --env-file .env.local pytest tests/common/test_metric_guard_census.py -q`
2. `cd apps/api && test "$(uv run --env-file .env.local pytest tests/common/test_metric_guard_census.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 9`
3. `cd apps/api && test "$(grep -c 'len(_FROZEN_CENSUS) == 36' tests/common/test_metric_guard_census.py)" -ge 1`
4. `cd apps/api && uv run --env-file .env.local pytest tests/tasks tests/common tests/trading -q`
5. `cd apps/api && uv run ruff check src/tasks/live_signal.py src/tasks/trading.py src/trading/realtime_publisher.py src/trading/webhook.py tests/common/test_metric_guard_census.py`

★런타임 변이 테스트를 census 파일이 아닌 다른 파일에 두는 편이 자연스러우면 그렇게 해라 —
그때는 AC 2 의 하한을 못 넘으므로 **census 파일에도 케이스가 남아야 한다.** 둘 다 채워라.

## `summary` 에 반드시 담을 것

- **양성**: 어느 자리에 어떻게 예외를 주입했고, 주문이 `filled` 로 남았다는 **단언 원문**
- **음성**: 가드 밖 자리에서는 **여전히 깨졌다**는 확인 (안 깨졌으면 그 사실을 크게 적어라)
- **도달 확인** 근거
- 모양 B 검증 결과
- 4자리 중 **런타임으로 못 잰 것이 있으면 그것과 이유** — 정직한 미검증이 거짓 초록보다 낫다

## 금지사항

- **소스(`apps/api/src`)를 이 step 에서 고치지 마라.** 측정만 한다.
- **「patch 했더니 안 죽더라」로 끝내지 마라** — 그 경로를 **실제로 지났는지** 확인해야 한다.
- **음성 대조를 생략하지 마라.** 양성만 재면 「아무것도 안 깨지는 테스트」와 구별이 안 된다.
- **celery worker 에 실제로 붙지 마라** — 워크트리의 worker 는 **메인 코드**를 돈다(침묵 실패).
- `phases/n7-common.md` 의 공통 금지사항 전부.
- 커밋하지 마라(커밋은 러너 소관).
