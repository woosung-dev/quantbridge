// 실제 인증·API·Celery·엔진·화면을 통과한다. 네트워크 mock은 사용하지 않는다.
import { randomUUID } from "node:crypto";
import { resolve } from "node:path";

import { expect, test } from "@playwright/test";

import { BacktestDetailSchema, StressTestDetailSchema } from "../src/features/backtest/schemas";

const email = `journey-${randomUUID()}@dogfood.local`;
const password = randomUUID();
const candidates = ["s1_pbr", "s2_utbot", "s3_rsid", "s4_hma_curvature", "s5_ema_trend"];

test.beforeAll(async ({ request, baseURL }) => {
  const response = await request.post("/api/auth/sign-up/email", {
    headers: { Origin: baseURL! },
    data: { name: "전략 검증 여정", email, password },
  });
  expect(response.ok(), `가입 HTTP ${response.status()}`).toBeTruthy();
});

for (const candidate of candidates) {
  test(`${candidate}: 임포트 → 백테스트 → 스트레스 테스트`, async ({ page }, testInfo) => {
    const started = Date.now();
    await page.goto("/sign-in");
    await page.getByLabel("이메일 주소").fill(email);
    await page.getByLabel("비밀번호", { exact: true }).fill(password);
    await page.getByRole("button", { name: "로그인", exact: true }).click();
    await page.waitForURL(/\/(strategies|onboarding)/);

    await page.goto("/strategies/new");
    await page
      .getByTestId("pine-file-input")
      .setInputFiles(resolve(`../api/tests/fixtures/pine_corpus_v2/${candidate}.pine`));
    await expect(page.getByTestId("parse-supported")).toBeVisible({ timeout: 90_000 });
    await page.locator("#f-name").fill(`검증 ${candidate}`);
    await page.getByTestId("parse-save").click();
    await page.waitForURL(/\/strategies\/[^/]+\/edit/);
    const strategyId = page.url().split("/strategies/")[1]!.split("/")[0]!;

    await page.goto(`/backtests/new?strategy_id=${strategyId}`);
    await expect(page.getByTestId("backtest-form-layout")).toBeVisible();
    await page.locator("#timeframe").selectOption("1h");
    await page.locator("#period_start").fill("2026-04-01");
    await page.locator("#period_end").fill("2026-06-30");
    const submitted = page.waitForResponse(
      (response) =>
        response.url().endsWith("/api/v1/backtests") && response.request().method() === "POST",
    );
    await page.getByTestId("backtest-submit").click();
    const submission = await submitted;
    if (submission.status() === 422) {
      // degraded 기능은 제품의 명시 동의 절차를 거친다.
      await expect(page.getByTestId("backtest-form-degraded-consent")).toBeVisible();
      await page.getByTestId("backtest-form-degraded-consent").check();
      await page.getByTestId("backtest-submit").click();
    } else {
      expect(submission.status()).toBe(202);
    }
    await page.waitForURL(/\/backtests\/[0-9a-f-]+$/);
    const backtestId = page.url().split("/").pop()!;
    const detailResponse = await page.waitForResponse(
      async (response) => {
        if (
          !response.url().endsWith(`/api/v1/backtests/${backtestId}`) ||
          response.status() !== 200
        )
          return false;
        const body = await response.json();
        return body.status === "completed" || body.status === "failed";
      },
      { timeout: 180_000 },
    );
    const detail = BacktestDetailSchema.parse(await detailResponse.json());
    expect(detail.status, detail.error ?? "백테스트 완료").toBe("completed");
    expect(detail.data_coverage).toBeTruthy();
    expect(detail.data_coverage!.bar_count).toBeGreaterThan(0);
    expect(detail.metrics!.num_trades).toBeGreaterThan(0);
    await expect(page.getByTestId("backtest-report-shell")).toBeVisible();
    await expect(page.getByText("실제 데이터 구간", { exact: true })).toBeVisible();
    if (detail.data_coverage!.missing_bars > 0) {
      await expect(page.getByTestId("backtest-data-incomplete-note")).toBeVisible();
    }

    const mcResponse = page.waitForResponse(
      async (response) => {
        if (
          !/\/api\/v1\/stress-tests\/[0-9a-f-]+$/.test(response.url()) ||
          response.status() !== 200
        )
          return false;
        const body = await response.json();
        return body.status === "completed" || body.status === "failed";
      },
      { timeout: 120_000 },
    );
    await page.getByRole("button", { name: "Monte Carlo 실행", exact: true }).click();
    const stress = StressTestDetailSchema.parse(await (await mcResponse).json());
    expect(stress.status, stress.error ?? "스트레스 테스트 완료").toBe("completed");
    await expect(page.getByTestId("monte-carlo-summary-table")).toBeVisible();
    await testInfo.attach("decision-evidence.json", {
      body: JSON.stringify(
        {
          candidate,
          strategyId,
          backtestId,
          elapsed_ms: Date.now() - started,
          data_coverage: detail.data_coverage,
          config: detail.config,
          metrics: detail.metrics,
          warnings: detail.warnings,
          stress,
        },
        null,
        2,
      ),
      contentType: "application/json",
    });
    await page.screenshot({ path: testInfo.outputPath("report.png"), fullPage: true });
  });
}
