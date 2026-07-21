// Sprint 55 — Bayesian optimizer e2e (mock-based) + LESSON-066 6차 SAEnum case mismatch silent regression 가드.
//
// 본 spec 은 Bayesian optimizer 제출 flow 와 결과 렌더 가드를 mock fixture 로 검증한다.
// 실 backend chain (router → service → repository → DB INSERT 안 BAYESIAN enum value roundtrip)
// 은 사용자 manual 의무 — `docker compose up worker` + Pine strategy + COMPLETED backtest + dogfood.
//
// ★C 이식 W3-C(2026-07-21) 재작성. 이 파일은 S0 시점에 testMatch 미등록 고아였고 폼 UX 가 통째로
// stale 이었다(텍스트 backtest_id 입력 → useBacktests 완료-백테스트 SelectWithDisplayName 피커,
// "최적화 알고리즘" 네이티브 select, "베이지안 탐색 새 실행" 폼 열기 버튼 + "베이지안 탐색 실행"
// 폼 내부 제출). 현행 UX 로 재작성하고 skip 을 풀었다.
// ★베이지안 완료 run 은 실 데이터에 없다 — 존재를 전제하지 않고 detail 은 mock 으로만 렌더한다.
//
// 검증 대상:
//   1. /optimizer picker 에서 완료 백테스트 선택 + algorithm=bayesian → "베이지안 탐색 새 실행".
//   2. BayesianSearchForm 핵심 필드(획득 함수 / 초기 랜덤 탐색 횟수) 노출.
//   3. submit 시 POST /api/v1/optimizer/runs/bayesian (별도 endpoint) + kind=bayesian + schema_version=2.
//   4. detail(mock COMPLETED)에서 BayesianIterationChart + BayesianBestParamsTable render.
//      result.kind="bayesian" + best_iteration_idx 명시 + degenerate 배지 (LESSON-066 6차 · Sprint 50/51/52 차단).

import { expect, test } from "@playwright/test";

import { fulfillJson } from "./fixtures/api-mock";

test.describe.configure({ mode: "serial" });

const USER_ID = "a0000000-0000-4000-8000-000000000099";
const STRATEGY_ID = "c0000000-0000-4000-8000-000000000055";
const BACKTEST_ID = "b0000000-0000-4000-8000-000000000055";
const RUN_ID = "00000000-0000-4000-8000-000000005555";

const NOW = "2026-05-11T15:00:00+00:00";

// 완료 백테스트 1건 — picker 는 status="completed" 만 노출한다.
const BACKTEST_SUMMARY = {
  id: BACKTEST_ID,
  strategy_id: STRATEGY_ID,
  symbol: "BTC/USDT",
  timeframe: "1h",
  period_start: "2024-01-01T00:00:00+00:00",
  period_end: NOW,
  status: "completed",
  created_at: NOW,
  completed_at: NOW,
};
const BACKTEST_LIST = { items: [BACKTEST_SUMMARY], total: 1, limit: 100, offset: 0 };

const PARAM_SPACE = {
  schema_version: 2,
  objective_metric: "sharpe_ratio",
  direction: "maximize",
  max_evaluations: 15,
  parameters: {
    emaPeriod: {
      kind: "bayesian",
      min: "5",
      max: "30",
      prior: "uniform",
      log_scale: false,
    },
  },
  bayesian_n_initial_random: 5,
  bayesian_acquisition: "EI",
};

const RUN_QUEUED = {
  id: RUN_ID,
  user_id: USER_ID,
  backtest_id: BACKTEST_ID,
  kind: "bayesian",
  status: "queued",
  param_space: PARAM_SPACE,
  result: null,
  error_message: null,
  created_at: NOW,
  started_at: null,
  completed_at: null,
};

const RUN_COMPLETED = {
  ...RUN_QUEUED,
  status: "completed",
  started_at: NOW,
  completed_at: NOW,
  result: {
    schema_version: 2,
    kind: "bayesian",
    param_names: ["emaPeriod"],
    iterations: [
      { idx: 0, params: { emaPeriod: "12" }, objective_value: "1.20", best_so_far: "1.20", is_degenerate: false, phase: "random" },
      { idx: 1, params: { emaPeriod: "25" }, objective_value: null, best_so_far: "1.20", is_degenerate: true, phase: "random" },
      { idx: 2, params: { emaPeriod: "17" }, objective_value: "1.85", best_so_far: "1.85", is_degenerate: false, phase: "acquisition" },
      { idx: 3, params: { emaPeriod: "18" }, objective_value: "1.75", best_so_far: "1.85", is_degenerate: false, phase: "acquisition" },
      { idx: 4, params: { emaPeriod: "16" }, objective_value: "1.92", best_so_far: "1.92", is_degenerate: false, phase: "acquisition" },
    ],
    best_params: { emaPeriod: "16" },
    best_objective_value: "1.92",
    best_iteration_idx: 4,
    objective_metric: "sharpe_ratio",
    direction: "maximize",
    bayesian_acquisition: "EI",
    bayesian_n_initial_random: 2,
    max_evaluations: 5,
    degenerate_count: 1,
    total_iterations: 5,
  },
};

const RUN_LIST = { items: [RUN_COMPLETED], total: 1, limit: 20, offset: 0 };

test.describe("Bayesian optimizer (LESSON-066 6차 + Sprint 50/51/52 retro 차단 가드)", () => {
  test("picker + form + submit → POST bayesian endpoint", async ({ page }) => {
    let postedToBayesianEndpoint = false;

    await page.route("**/api/v1/optimizer/runs/bayesian", async (route) => {
      postedToBayesianEndpoint = true;
      const body = JSON.parse(route.request().postData() ?? "{}");
      // submit body 검증 — kind=bayesian + schema_version=2 (LESSON-066 case mismatch 차단).
      expect(body.kind).toBe("bayesian");
      expect(body.param_space.schema_version).toBe(2);
      expect(body.param_space.bayesian_acquisition).toBe("EI");
      await fulfillJson(RUN_QUEUED, 202)(route);
    });
    // 완료 백테스트 picker 소스.
    await page.route("**/api/v1/backtests**", async (route) => {
      await fulfillJson(BACKTEST_LIST)(route);
    });
    // /optimizer 하단 실행 목록.
    await page.route("**/api/v1/optimizer/runs**", async (route) => {
      await fulfillJson(RUN_LIST)(route);
    });

    await page.goto("/optimizer");

    // 1. 완료 백테스트 선택 (SelectWithDisplayName combobox).
    await page.getByRole("combobox", { name: "백테스트 선택" }).click();
    await page.getByRole("option", { name: /BTC\/USDT/ }).click();

    // 2. algorithm = bayesian (네이티브 select aria-label "최적화 알고리즘").
    await page.getByLabel("최적화 알고리즘").selectOption("bayesian");

    // 3. "베이지안 탐색 새 실행" 으로 폼 열기.
    await page.getByRole("button", { name: /베이지안 탐색 새 실행/ }).click();

    // 4. BayesianSearchForm 핵심 필드 노출.
    await expect(page.getByText("획득 함수 (acquisition)")).toBeVisible();
    await expect(page.getByText("초기 랜덤 탐색 횟수 (워밍업)")).toBeVisible();

    // 5. var_name 입력 + 폼 내부 제출.
    await page.getByPlaceholder("변수 이름 (예: length)").fill("emaPeriod");
    await page.getByRole("button", { name: /베이지안 탐색 실행/ }).click();

    // 6. submit endpoint 호출 검증.
    await expect.poll(() => postedToBayesianEndpoint).toBe(true);
  });

  test("detail(mock COMPLETED) — 반복 곡선 + 최적 파라미터 + 축퇴 배지 (LESSON-066 가드)", async ({
    page,
  }) => {
    await page.route(`**/api/v1/optimizer/runs/${RUN_ID}`, async (route) => {
      await fulfillJson(RUN_COMPLETED)(route);
    });

    await page.goto(`/optimizer/${RUN_ID}`);

    // BayesianIterationChart (best_so_far 곡선, SVG aria-label).
    await expect(page.getByRole("img", { name: /베이지안 반복 곡선/ })).toBeVisible();
    // BayesianBestParamsTable — 최적 파라미터 + best_iteration_idx 명시.
    await expect(page.getByText("최적 파라미터").first()).toBeVisible();
    await expect(page.getByText(/최적 반복 #/)).toBeVisible();
    // degenerate 배지 (1 / 5) — Sprint 50/51/52 retro 차단 가드.
    await expect(page.getByText(/축퇴 1 \/ 5/)).toBeVisible();
  });
});
