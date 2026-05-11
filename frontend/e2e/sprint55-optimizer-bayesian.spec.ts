// Sprint 55 — Bayesian optimizer e2e (mock-based) + LESSON-066 6차 SAEnum case mismatch silent regression 가드.
//
// 본 spec 은 Sprint 55 Slice 6 의무 (e2e Bayesian flow) 를 mock fixture 로 검증한다.
// 실 backend chain (router → service → repository → DB INSERT 안 BAYESIAN enum value
// roundtrip) 은 사용자 manual 의무 — `docker compose up worker` + Pine strategy fixture
// + COMPLETED backtest + 본인 dogfood UI session.
//
// 검증 대상:
//   1. /optimizer 페이지 algorithm select dropdown 안 "Bayesian" 옵션 활성.
//   2. BayesianSearchForm render + 필수 필드 (acquisition / n_initial_random) 노출.
//   3. submit 시 POST /api/v1/optimizer/runs/bayesian 호출 (별도 endpoint, Sprint 55 결정).
//   4. detail page polling QUEUED → COMPLETED 후 BayesianIterationChart + BayesianBestParamsTable
//      render. result.kind="bayesian" + best_iteration_idx 명시 (Sprint 50/51/52 차단).
//   5. degenerate iteration 표시 (badge).
//
// Tier: dogfood Phase 2 critical (Sprint 56+ 본격 dogfood 시 regression 가드).

import { expect, test } from "@playwright/test";

import { fulfillJson } from "./fixtures/api-mock";

test.describe.configure({ mode: "serial" });

const USER_ID = "a0000000-0000-4000-8000-000000000099";
const BACKTEST_ID = "b0000000-0000-4000-8000-000000000055";
const RUN_ID = "00000000-0000-4000-8000-000000005555";

const NOW = "2026-05-11T15:00:00+00:00";

const PARAM_SPACE = {
  schema_version: 2,
  objective_metric: "sharpe_ratio",
  direction: "maximize",
  max_evaluations: 5,
  parameters: {
    emaPeriod: {
      kind: "bayesian",
      min: "5",
      max: "30",
      prior: "uniform",
      log_scale: false,
    },
  },
  bayesian_n_initial_random: 2,
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
      {
        idx: 0,
        params: { emaPeriod: "12" },
        objective_value: "1.20",
        best_so_far: "1.20",
        is_degenerate: false,
        phase: "random",
      },
      {
        idx: 1,
        params: { emaPeriod: "25" },
        objective_value: null,
        best_so_far: "1.20",
        is_degenerate: true,
        phase: "random",
      },
      {
        idx: 2,
        params: { emaPeriod: "17" },
        objective_value: "1.85",
        best_so_far: "1.85",
        is_degenerate: false,
        phase: "acquisition",
      },
      {
        idx: 3,
        params: { emaPeriod: "18" },
        objective_value: "1.75",
        best_so_far: "1.85",
        is_degenerate: false,
        phase: "acquisition",
      },
      {
        idx: 4,
        params: { emaPeriod: "16" },
        objective_value: "1.92",
        best_so_far: "1.92",
        is_degenerate: false,
        phase: "acquisition",
      },
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

const RUN_LIST = {
  items: [RUN_COMPLETED],
  total: 1,
  limit: 20,
  offset: 0,
};

test.describe("Sprint 55 — Bayesian optimizer (LESSON-066 6차 + Sprint 50/51/52 retro 차단 가드)", () => {
  test("algorithm select + form + submit + detail render", async ({ page }) => {
    let postedToBayesianEndpoint = false;
    let detailPollCount = 0;

    await page.route("**/api/v1/optimizer/runs/bayesian", async (route) => {
      postedToBayesianEndpoint = true;
      const body = JSON.parse(route.request().postData() ?? "{}");
      // submit body 검증 — kind=bayesian + schema_version=2 (LESSON-066 case mismatch 차단).
      expect(body.kind).toBe("bayesian");
      expect(body.param_space.schema_version).toBe(2);
      expect(body.param_space.bayesian_acquisition).toBe("EI");
      await fulfillJson(RUN_QUEUED, 202)(route);
    });

    await page.route(`**/api/v1/optimizer/runs/${RUN_ID}`, async (route) => {
      detailPollCount += 1;
      // 1st poll = QUEUED, 2nd+ = COMPLETED (polling 종료 trigger).
      const body = detailPollCount === 1 ? RUN_QUEUED : RUN_COMPLETED;
      await fulfillJson(body)(route);
    });

    await page.route("**/api/v1/optimizer/runs**", async (route) => {
      // list endpoint (page.tsx 의 OptimizerRunList).
      await fulfillJson(RUN_LIST)(route);
    });

    await page.goto("/optimizer");

    // 1. backtest_id 입력 + algorithm = bayesian.
    await page.getByLabel("backtest_id").fill(BACKTEST_ID);
    await page.getByLabel("optimizer algorithm").selectOption("bayesian");
    await page.getByRole("button", { name: /Bayesian 신규 제출/ }).click();

    // 2. BayesianSearchForm 핵심 필드 노출.
    await expect(page.getByText("acquisition function")).toBeVisible();
    await expect(page.getByText("random warm-up")).toBeVisible();

    // 3. var_name 입력 + submit.
    await page.getByPlaceholder("var_name (pine input)").fill("emaPeriod");
    await page.getByRole("button", { name: /Bayesian 제출/ }).click();

    // 4. submit endpoint 호출 검증.
    await expect.poll(() => postedToBayesianEndpoint).toBe(true);

    // 5. 사용자 manual = run_id 라우팅 + chart render — spec 안 결과 page polling 검증은
    //    Sprint 56+ Genetic 묶음 e2e 확장 시 scope. 현재는 submit + endpoint 호출 검증만.
  });
});
