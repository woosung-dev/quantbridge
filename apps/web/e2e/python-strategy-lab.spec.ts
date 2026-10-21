// 인증은 실제 세션, Python 실행 응답은 고정한다. 공통 DB에 새 테이블이나 실험을 만들지 않는다.
import { expect, test, type Page } from "@playwright/test";
import { STRATEGY, makeRun } from "../src/features/python-strategy/__tests__/fixtures";
import { fulfillJson } from "./fixtures/api-mock";

async function stubShell(page: Page) {
  await page.route("**/api/v1/**", fulfillJson({ items: [], total: 0 }));
}

test("실행기 미설정에서도 코드를 저장하고 잘못된 입력을 바로잡을 수 있다", async ({ page }) => {
  await stubShell(page);
  let saved = false;
  await page.route("**/api/v1/python-strategies**", async (route, request) => {
    const path = new URL(request.url()).pathname;
    if (path.endsWith("/capabilities"))
      return fulfillJson({ available: false, reason: "격리 실행기 미설정" })(route);
    if (request.method() === "POST") {
      saved = true;
      return fulfillJson({ ...STRATEGY, ...request.postDataJSON() }, 201)(route);
    }
    if (path.endsWith("/backtests")) return fulfillJson({ items: [] })(route);
    return fulfillJson({ items: saved ? [STRATEGY] : [] })(route);
  });
  await page.goto("/strategies/python");
  await expect(page.getByRole("heading", { name: "Python 전략 실험실" })).toBeVisible();
  await expect(page.getByText("격리 실행기 미설정", { exact: false })).toBeVisible();
  await page.getByLabel("파라미터 JSON").fill("[]");
  await page.getByRole("button", { name: "첫 버전 저장" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "객체 형태의 JSON" })).toBeVisible();
  expect(saved).toBe(false);
  await page.getByLabel("파라미터 JSON").fill('{"period":20}');
  await page.getByRole("button", { name: "첫 버전 저장" }).click();
  await expect(page.getByRole("button", { name: "새 버전 저장" })).toBeVisible();
  await expect(page.getByRole("button", { name: "저장한 버전으로 백테스트" })).toBeDisabled();
  await page.setViewportSize({ width: 320, height: 760 });
  await expect
    .poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth))
    .toBe(true);
  await test.info().attach("python-lab-mobile", {
    body: await page.screenshot({
      path: test.info().outputPath("python-lab-mobile.png"),
      fullPage: true,
    }),
    contentType: "image/png",
  });
});

test("저장한 버전을 실행하고 완료 후 폴링을 멈춘다", async ({ page }) => {
  await stubShell(page);
  let hasRun = false;
  let reads = 0;
  let run = makeRun({ status: "pending" });
  await page.route("**/api/v1/python-strategies**", async (route, request) => {
    const path = new URL(request.url()).pathname;
    if (path.endsWith("/capabilities"))
      return fulfillJson({ available: true, reason: null })(route);
    if (path.endsWith(`/backtests/${run.id}`)) {
      reads += 1;
      run = makeRun({
        status: "completed",
        completed_at: "2026-10-21T00:01:00Z",
        result: {
          metrics: {
            total_return: "0.12",
            max_drawdown: "-0.08",
            profit_factor: "1.3",
            num_trades: 35,
            sharpe_ratio: "0",
            sharpe_convention: "unavailable",
            total_fees: "3E-2",
            total_slippage: "1E-2",
          },
          equity_curve: [],
          trades: [],
          provenance: { source_hash: STRATEGY.source_hash },
        },
      });
      return fulfillJson(run)(route);
    }
    if (path.endsWith("/backtests")) {
      if (request.method() === "POST") {
        hasRun = true;
        const body = request.postDataJSON();
        expect(body.expected_version_id).toBe(STRATEGY.version_id);
        run = { ...run, request: body };
        return fulfillJson(run, 202)(route);
      }
      return fulfillJson({ items: hasRun ? [run] : [] })(route);
    }
    return fulfillJson({ items: [STRATEGY] })(route);
  });
  await page.goto("/strategies/python");
  await page.getByRole("button", { name: STRATEGY.name, exact: true }).click();
  await page.getByRole("button", { name: "저장한 버전으로 백테스트" }).click();
  await expect(page.getByText("12.00%", { exact: true })).toBeVisible();
  await expect(page.getByText("단일 백테스트 · 후보 검증 미완료.")).toBeVisible();
  const completedReads = reads;
  await page.waitForTimeout(2_200);
  expect(reads).toBe(completedReads);
  expect(reads).toBeGreaterThan(0);
  await expect(page.getByRole("button", { name: "실행 취소", exact: true })).toHaveCount(0);
  await test.info().attach("python-lab-result", {
    body: await page.screenshot({
      path: test.info().outputPath("python-lab-result.png"),
      fullPage: true,
    }),
    contentType: "image/png",
  });
});
