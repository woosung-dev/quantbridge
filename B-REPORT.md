# 레인 β 보고 — [BL-429] 대시보드 §03 최적화 행이 성과를 못 보여준다

브랜치 `stage/night3-bl429-optimizer-row` (base `origin/main` = `acdc12c5`) · 슬롯 4.
원장 초안 = `B-ledger.md`. **수치의 정본은 이 문서다.**

---

## 결론 한 줄

대시보드 §03 의 최적화 행이 이제 **백테스트 행과 같은 열에 같은 의미의 숫자**(수익률·MDD)를
그린다. 값이 없는 실행은 여전히 빈칸이고 **0 이 아니다** — 그 구분을 재는 테스트가 5건,
변이는 3/3 red 다.

---

## AC 별 판정

| AC                                    | 판정           | 근거                                                        |
| ------------------------------------- | -------------- | ----------------------------------------------------------- |
| AC-1 대상 실재 확인                   | ✅             | 아래 §「대상은 실재했다」                                   |
| AC-2 갈래 ⒜/⒝ 결정                    | ✅ ⒜ 채택      | 아래 §「왜 ⒜ 인가」                                         |
| AC-3 목록 응답에 탑재 · N+1 없음      | ✅             | 쿼리 수 1행 2회 = 4행 2회 (테스트가 잰다)                   |
| AC-4 FE 렌더 · `EMPTY_CELL` 고정 제거 | ✅             | `dashboard-cockpit.tsx:510-511` 이 `MetricValue` 2개로 교체 |
| AC-5 「없음 ≠ 0」을 재는 테스트       | ✅             | FE 3건 + BE 2건 (아래 표)                                   |
| AC-6 BE·FE·canon 전량 초록            | ✅             | 아래 §게이트                                                |
| AC-7 레인 α 증거 게이트 사용          | ⚠️ **못 했다** | α 가 미완이다 — 아래 §「AC-7」                              |

---

## 대상은 실재했다 (AC-1)

계약 §「원장이 낡았다」가 요구한 코드 대조를 먼저 했다. **둘 다 지금도 참이다.**

- `apps/web/src/features/dashboard/components/dashboard-cockpit.tsx:510-511` —
  `<td className="num" title="결과는 최적화 상세에서 확인">{EMPTY_CELL}</td>` 두 줄이 그대로 있었다.
  같은 표의 백테스트 행(534-535)은 `MetricValue` 로 숫자를 그린다.
- `apps/api/src/optimizer/schemas.py:229` `OptimizationRunResponse` — 필드는
  `param_space` 와 `result: dict[str, Any] | None` 이고 metric 필드는 **없었다.**

★**다만 원장의 인과 문장 하나는 거짓이었다.** 원장은 「OptimizationRun 은
param_space/result(iterations) 만 보유, best 조합의 백테스트 metric 은 **목록에 없어**」라고
적는데, **grid_search 에는 있었다** — `result` JSONB 의 `cells[]` 가 cell 마다
`total_return`·`max_drawdown` 을 갖고 `best_cell_index` 도 있으며, 목록 응답은 `result` 를
**통째로** 싣는다. 즉 그 숫자는 이미 클라이언트에 도착해 있었고 없던 것은 **꺼내는 이름**이다.
진짜로 metric 이 없던 것은 **bayesian·genetic** 둘이다(`BayesianIteration`·`GeneticIndividual`
가 `objective_value` 만 보관 — `outcome.result.metrics` 를 계산하고 **버린다**).
이 차이가 아래 설계 결정의 절반을 정했다.

---

## 왜 ⒜ 인가 (AC-2)

**갈래 ⒜ — best 조합의 backtest metric denormalize 를 골랐다.** 근거 셋이다.

**⑴ 열이 이미 백테스트 행과 공유돼 있다.** §03 표의 헤더는 「수익률」·「MDD」(`:368-369`)이고
같은 열의 백테스트 행은 `metrics_summary.total_return`·`max_drawdown` 을 그린다. 갈래 ⒝ 의
`objective_value` 는 run 마다 의미가 갈린다 — `objective_metric` 이 `sharpe_ratio`면 무차원,
`total_return`이면 비율, `max_drawdown`이면 음수 비율이다. 그것을 「수익률」 열에 넣으면
**한 열에 두 컨벤션이 섞이고 정렬이 거짓말을 한다** — 이 레포가 [BL-462]·[BL-463] 에서 겪은 그 사고다.
열 제목을 바꾸는 길은 **백테스트 행의 의미까지 함께 바꾸므로** 답이 아니다.

**⑵ 단위가 실제로 같음을 코드로 확인했다.** 추정이 아니다. optimizer 의 cell/iteration metric 은
`outcome.result.metrics`(= `BacktestMetrics`)에서 오고, 백테스트 행의
`metrics_summary.total_return` 도 같은 `BacktestMetrics.total_return` 에서 온다
(`backtest/serializers.py:135`). 둘 다 ratio 이고 FE `formatPercent` 가 ×100 한다.
**같은 열에 넣어도 되는 이유가 「비슷해 보여서」가 아니라 같은 출처이기 때문이다.**

**⑶ 갈래 ⒝ 는 다른 화면이 이미 하고 있다.** `apps/web/src/features/optimizer/components/optimizer-run-list.tsx`
(`/optimizer` 목록)는 **objective 열**(`OBJECTIVE_METRIC_LABEL[objective_metric]` + 방향)과
**best 열**(raw objective value, `:222-231`)을 따로 두고 있다 — 즉 ⒝ 를 열 제목까지 바꿔서
제대로 구현한 화면이 이미 있다. 대시보드에서 ⒝ 를 또 하면 **같은 정보를 라벨 없이 반복**하는
것이고, 어느 화면도 안 보여주던 것은 「그래서 그 조합이 실제로 얼마를 벌었나」였다.

**⑷ 대가가 작았다.** grid 는 저장된 JSONB 에 이미 값이 있어 **엔진 변경 0**. bayesian·genetic 은
metric 을 이미 계산하고 버리던 것을 best 하나만 붙잡게 했다. `models.py` 변경이 없으므로
**alembic migration 도 없다.**

★**「둘 다」는 하지 않았다** — 열이 늘면 그 표의 반응형이 깨진다(`apps/web/AGENTS.md` §10).

### 재계산 시점 문제를 어떻게 처리했나

갈래 ⒜ 의 대가로 원장이 적은 「재계산 시점 문제」는 **denormalize 를 DB 컬럼이 아니라 응답
파생으로 두어** 없앴다. 값은 `run.result`(이미 로드된 JSONB)에서 매 응답 파생하므로
쓰기 경로가 늘지 않고 원본과 어긋날 수 없다. 대신 bayesian·genetic 의 **저장 JSONB** 에는
best 의 metric 을 추가했다 — 그 둘은 애초에 값이 없어서 파생이 불가능하다.

---

## 무엇이 바뀌었나

**BE (`apps/api/src/optimizer/`)**

| 파일                                     | 변경                                                                                                                                                                                          |
| ---------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `engine/bayesian.py`·`engine/genetic.py` | `BayesianSearchResult`·`GeneticSearchResult` 에 `best_total_return`·`best_max_drawdown` 신설. 루프가 iteration 위치별 `BacktestMetrics` 를 모아 두고 best 확정 후 **그 하나만** 결과에 싣는다 |
| `serializers.py`                         | 요약 블록 직렬화/역직렬화에 두 키 추가(구 row 는 `.get()` → `None`) + **`best_metrics_from_jsonb`** 신설 — 저장 JSONB → `(total_return, max_drawdown)` 추출 SSOT (kind 분기)                  |
| `schemas.py`                             | `OptimizationRunResponse.best_total_return`·`best_max_drawdown` (`Decimal \| None`) + `field_serializer` → str. `BacktestMetricsSummary` 와 같은 표기                                         |
| `service.py`                             | `_to_response` 가 이미 로드된 `run.result` 에서 파생. **추가 쿼리 0**                                                                                                                         |

★**iteration 별로 싣지 않았다.** 그러면 목록 응답이 `iterations` 를 통째로 실으므로
`max_evaluations` 에 비례해 payload 가 커진다(AC-3 의 「악화시키지 않는지」).

**FE (`apps/web/src/features/`)**

| 파일                                         | 변경                                                                                                                                                                            |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `dashboard/components/dashboard-cockpit.tsx` | `EMPTY_CELL` 고정 2줄 → 백테스트 행이 쓰던 `MetricValue` 2개. **새 컴포넌트를 만들지 않았다** — `value == null ? EMPTY_CELL : format(value)` 가 이미 「없음 ≠ 0」을 하고 있었다 |
| `optimizer/schemas.ts`                       | `OptimizationRunResponseSchema` 에 두 필드(`nullable().optional()`). Bayesian·Genetic result schema 에도 두 필드(`nullable().default(null)` — 구 row 에는 키가 없다)            |

**schema_version 은 올리지 않았다.** 순수 추가 필드이고, 구 row 는 키 부재 → `None` 으로 읽힌다.

---

## 변이 결과표

| #   | 변이                                               | 심은 곳                                         | 결과       | red 낸 테스트                                                                                                                                       |
| --- | -------------------------------------------------- | ----------------------------------------------- | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| M1  | BE 새 필드를 `None` 고정으로 되돌린다              | `service.py` `_to_response`                     | ✅ **red** | `test_list_carries_best_metrics_and_distinguishes_absent_from_zero` · `test_list_best_metrics_serialize_as_decimal_strings` (2 failed / 200 passed) |
| M2  | FE 「없음」 분기를 `0` 으로 바꾼다                 | `dashboard-cockpit.tsx` `MetricValue`           | ✅ **red** | `best 가 없는 실행 — 빈칸이고 0 이 아니다` · `RUNNING 실행 — best 필드 자체가 없어도 빈칸이다` (2 failed / 17 passed)                               |
| M3  | 엔진의 best metric capture 를 `None` 으로 되돌린다 | `engine/bayesian.py` + `engine/genetic.py` 동시 | ✅ **red** | `test_best_backtest_metrics_come_from_the_best_iteration` · `..._best_individual` (2 failed / 200 passed)                                           |

M1·M3 은 문자열 치환으로 심고 **되돌린 뒤 sha256 이 원본과 일치**함을 확인했다
(`git checkout` 미사용). M2 도 동일.

★**M3 은 계약이 준 두 변이에 없던 것이고, 그것을 추가한 이유가 이 회차의 함정이었다.**
M1(service 고정)만 돌리면 **엔진의 capture 는 아무 테스트도 재지 않는다** — bayesian·genetic
엔진 테스트 13건이 전부 초록인 채로 `best_total_return=None` 이 커밋될 수 있었다.
그래서 엔진 레벨 테스트 4건을 따로 추가했고(각 kind 마다 best 있음/전건 degenerate),
best 를 **첫도 마지막도 아닌 중간 iteration**에 두어 「어느 iteration 의 값인지」를 가렸다
(bayesian idx=2 / genetic idx=5).

---

## 새로 추가한 테스트

| 층           | 파일                                                        | 건수           | 무엇을 재나                                                                                                                  |
| ------------ | ----------------------------------------------------------- | -------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| FE 컴포넌트  | `dashboard/components/__tests__/dashboard-cockpit.test.tsx` | 3              | ⑴ best 있는 완료 실행 → `18.42%`/`-7.31%` ⑵ best 없음 → `—` 이고 `0.00%` **아님** ⑶ RUNNING(필드 부재) → `—`                 |
| BE 배선      | `tests/optimizer/test_runs_list_denormalized.py`            | 3              | 목록 응답이 **best cell(index=1)** 값을 싣는다(cell 0 은 미끼) · 직렬화가 decimal 문자열 · **쿼리 수가 행 수에 안 비례한다** |
| BE 순수 함수 | `tests/optimizer/test_serializers.py`                       | 4(+9 파라미터) | kind 3종 추출 · 값 없음 9가지가 전부 `(None, None)`(구 row·손상 row 포함) · 구 row round-trip                                |
| BE 엔진      | `test_bayesian_engine.py` · `test_genetic_engine.py`        | 4              | best 의 metric 을 싣는다(중간 iteration) · 전건 degenerate → `None`                                                          |

기존 테스트 중 하나를 **지웠다**: `getAllByTitle("결과는 최적화 상세에서 확인")` 단언
(`dashboard-cockpit.test.tsx`). 그 title 이 사라지는 것이 AC-4 자체다.

---

## 게이트 (AC-6)

| 게이트                                | rc    | 결과                                   |
| ------------------------------------- | ----- | -------------------------------------- |
| BE pytest 전량                        | **0** | **4801 passed, 32 skipped** (429초)    |
| BE `ruff check src tests`             | 0     | All checks passed                      |
| BE `mypy src`                         | 0     | 218 files, no issues                   |
| FE vitest 전량                        | 0     | 220 files / **1433 passed**            |
| FE `tsc --noEmit`                     | 0     |                                        |
| FE `eslint`                           | 0     | 0 errors / 7 warnings (전부 기존 파일) |
| `pnpm e2e:design-canon`               | 0     | **44 passed** (48.7s)                  |
| `final-gates.sh --run bl429 --pre-pr` | **0** | 아래 §final-gates                      |

모든 판정은 **파이프 없이** `rc=$?` 로 잡았다(계약 §함정).

### final-gates

첫 실행이 **`BE openapi drift` 하나로 rc=1** 이었다. 새 응답 필드 2개가
`contracts/openapi/openapi.json` 스냅샷과 어긋난 것이고, 재생성
(`uv run python scripts/export_openapi.py`)해서 커밋했다. 생성된 diff 는 **+22줄, 두 필드뿐**
이고 타입이 `string | null` 로 나와 `BacktestMetricsSummary` 와 같은 표기임이 계약 층에서도
확인됐다. 재실행 결과 **rc=0** (117초).

유예 9종은 계약대로 손대지 않았다 — 원장은 `.claude/gates/bl429/deferred.txt` 에 남아 있고
`--deferred-only` 는 push 뒤 아침에 돈다.

★**BE 문턱을 직접 재려 한 첫 시도는 오염됐다 — 내 잘못이다.** 착수 직후 백그라운드로
전량 pytest 를 걸어 두고 **그 실행 중에 소스를 고쳤다.** 결과는 `23 failed, 4759 passed`
였고 실패 23건이 **전부 `tests/optimizer/` 안**이었다 — 즉 그것은 기준선이 아니라 내
편집 중간 상태를 잰 것이다. 되돌려 다시 재는 대신 **최종 트리에서 전량을 다시 돌리는
쪽**을 택했다(그것이 AC-6 이 요구하는 수치이기도 하다). ⇒ **「착수 시점 baseline」은 이
회차에 확보하지 못했다.** 다만 오염된 실행에서도 optimizer 밖 실패가 0 이었으므로
「선행 실패가 optimizer 밖에 있었다」는 사실은 아니다.

---

## AC-7 — 레인 α 의 증거 게이트는 못 돌렸다

**α 는 아직 산출을 커밋하지 않았다.** 2026-08-17 실측: `quant-bridge-wt3` 의 브랜치
`stage/night3-evidence-gate` 는 여전히 `acdc12c5` 에 있고(커밋 0건), 작업물은 미커밋
상태다(`screen-evidence.spec.ts`·`screen-evidence.mjs`·`screen-evidence-lib.mjs` 등 5개 신규 +
`playwright.config.ts`·`package.json` 수정).

가져오지 않은 이유는 둘이다. ⑴ 미커밋 파일을 워크트리 사이로 복사하면 아침 통합에서
어느 쪽이 정본인지 모르게 된다. ⑵ α 의 산출은 `playwright.config.ts` 수정을 포함하는데
그 파일은 **레인 α 소유**라 내가 만지면 안 된다.

**아침 통합에 필요한 정보:** α 의 경로 SSOT 는 `apps/web/e2e/screen-evidence.config.json`
이고 BL 번호로 **797** 을 쓰고 있다. 내 변경의 증거 대상 라우트는 `/dashboard` 하나다
(§03 표). before/after 는 α 의 게이트를 내 브랜치에 병합한 뒤 한 번 돌리면 나온다.

---

## 확인하지 못한 것

- **브라우저로 눈으로 본 화면.** 컴포넌트 테스트와 design-canon e2e 로만 검증했다.
  실제 값이 들어간 §03 표를 띄우려면 완료된 최적화 run 이 개발 DB 에 있어야 하는데,
  최적화 실행은 celery 를 타고 **워크트리에서 celery 경유 검증은 금지**다(worker 가 메인의
  `src` 를 mount 한다). ⇒ 렌더 경로의 증거는 테스트뿐이다.
- **구 row 가 실제 DB 에 몇 건인지.** bayesian·genetic 의 기존 완료 run 은 `best_total_return`
  키가 없어 계속 빈칸으로 보인다. 그것이 **의도한 동작**이지만(없는 값을 만들어내지 않는다),
  「빈칸으로 남는 행이 몇 개인가」는 개발 DB 를 조회하지 않아 모른다.
- **레인 α 의 증거 팩** (위 AC-7).
- **BL 번호.** 새 BL(§2 of `B-ledger.md`) 의 번호를 비워 뒀다 — 797 은 α 가 이미 썼고
  레인 γ 도 도는 중이라 798 도 안전하지 않다.
