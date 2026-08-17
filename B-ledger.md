# 레인 β 원장 초안 — [BL-429]

> 수치의 정본은 `B-REPORT.md` 다. 이 문서는 원장(`docs/backlog.md`)에 그대로 옮길 문장만 담는다.
> 브랜치 `stage/night3-bl429-optimizer-row` · 슬롯 4.

---

## 1. [BL-429] 상태줄 교체

**지금 원장(`docs/backlog.md:1918-1919`)에 있는 두 줄:**

```
**상태:** ⏳ 대기 (트리거 미도래) — §03 최적화 행의 수익률/MDD 칸이 여전히 EMPTY_CELL + "결과는 최적화 상세에서 확인" 고정이라 역산·objective 표기 미구현. (2026-08-09 status-triage-mass 확인)
**트리거 판정:** 미도래 — 외생 조건(사용자 결정·요청). 우리 의지로 만들 수 없다 (2026-08-10 bl-trigger-triage)
```

**바꿀 두 줄:**

```
**상태:** ✅ **RESOLVED** — 갈래 ⒜(best 조합의 backtest metric denormalize) 채택. BE `OptimizationRunResponse` 에 `best_total_return`·`best_max_drawdown` 신설(목록 응답에 직접 탑재, 상세 왕복 0·추가 쿼리 0), FE `dashboard-cockpit.tsx` 가 백테스트 행과 같은 `MetricValue` 로 렌더. 값이 없는 실행(RUNNING·FAILED·best 미확정·구 row)은 여전히 빈칸이고 **0 이 아니다** — 그 구분을 재는 테스트 5건 + 변이 3/3 red. (2026-08-17 night3 레인 β)
**트리거 판정:** ✅ **도래** — 2026-08-17 사용자가 요청했다. 종전 판정(「외생 조건이라 우리 의지로 만들 수 없다」)은 트리거가 실제로 온 지금 더 이상 유효하지 않다 (2026-08-17 night3 레인 β)
```

★**원장 본문의 인과 한 문장도 틀렸다.** 지금 「**원인 / 영향**」이 이렇게 적혀 있다:

> OptimizationRun 은 param_space/result(iterations) 만 보유, best 조합의 백테스트 metric 은 목록에 없어 §03 최적화 행 성과 칸이 빈칸.

**grid_search 에 한해 거짓이다.** `result` JSONB 의 `cells[]` 는 처음부터 cell 마다
`total_return`·`max_drawdown` 을 갖고 있었고 `best_cell_index` 도 있었다. 목록 응답은
`result` 를 **통째로** 실으므로 그 숫자는 이미 클라이언트에 도착해 있었다 — 없던 것은
데이터가 아니라 **그것을 꺼내는 이름**이다. 진짜로 metric 이 없던 것은 bayesian·genetic
둘이고(iteration 은 `objective_value` 만 보관), 그 둘만 엔진 수정이 필요했다.
⇒ 본문에 다음을 덧붙인다:

```
**2026-08-17 정정:** 「metric 이 목록에 없다」는 grid_search 에는 거짓이었다 — `result.cells[best_cell_index]` 에 처음부터 있었고 목록 응답이 `result` 를 통째로 싣는다. 없던 것은 값이 아니라 **꺼내는 이름**이다. 실제로 값이 없던 것은 bayesian·genetic(iteration 이 `objective_value` 만 보관)이고, 그 둘만 엔진이 best 의 metric 을 결과에 싣도록 고쳤다.
```

---

## 2. 새 BL 초안 — 최적화 목록 응답이 `result` 를 통째로 싣는다

★**번호 미확정.** 이 회차의 다음 번호는 797 이었으나 **레인 α 가 이미 797 을 썼다**
(2026-08-17 `quant-bridge-wt3/apps/web/e2e/screen-evidence.config.json` 실측). 레인 γ 도 도는
중이라 798 도 안전하지 않다. **아침에 오케스트레이터가 부여해라.**

```
### BL-XXX

**Title:** 최적화 목록 응답이 `result` JSONB 를 행마다 통째로 싣는다
**Category:** Backend / 성능
**Priority:** P3
**Trigger:** 최적화 실행이 쌓이거나 `max_evaluations` 가 큰 run 이 목록에 섞일 때
**Est:** S
**상태:** ⏳ **대기 (트리거 미도래)** — 현 규모(대시보드가 8행만 당긴다)에서는 측정 가능한 피해가 없다.
**트리거 판정:** 미도래 — **규모 조건**이다. [BL-710] 과 같은 성격이되 대상이 다르다(그쪽은 `/strategies`).
**출처:** 2026-08-17 night3 레인 β ([BL-429] 작업 중 관측)

**원인 / 영향:** `GET /api/v1/optimizer/runs` 의 `OptimizationRunResponse.result` 는 `dict[str, Any]` 전량이다. grid 는 cell 전부, bayesian·genetic 은 iteration 전부가 행마다 실린다. 대시보드 §03 은 그중 best 두 값만 쓰는데, `max_evaluations=100` 짜리 run 8건이면 목록 한 번에 iteration 800개가 따라온다. **[BL-429] 가 그 두 값을 별도 필드로 뽑았으므로 이제 목록에서 `result` 를 뺄 수 있다** — 다만 `/optimizer` 목록 화면이 `result` 를 쓰는지 먼저 확인해야 한다.

**권장 접근:** 목록 전용 응답에서 `result` 를 제외(또는 `best_*` 요약만 남김). 상세(`GET /runs/{id}`)는 그대로 둔다.
```

---

## 3. 원장에 적을 반증 (`docs/lessons.md` 후보 — 승격 여부는 오케스트레이터 판단)

**「목록에 없다」가 「응답에 없다」를 뜻하지 않았다.** [BL-429] 의 착수 근거는 「best 조합의
백테스트 metric 이 목록에 없다」였는데, grid_search 에서는 값이 **이미 응답에 실려** 있었다.
빠져 있던 것은 그 값을 가리키는 **이름**이고, 화면은 이름이 없어서 빈칸을 그리고 있었다.
⇒ 「데이터가 없다」는 진단을 받으면 **응답 바이트를 먼저 봐라** — 스키마 필드 목록만 보면
JSONB 안에 든 것을 못 본다.
