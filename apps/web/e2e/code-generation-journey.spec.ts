// 실제 인증·코드 저장 API·DB를 사용한다. 생성 응답과 백테스트 접수/조회만 대체한다.
// Gemini 추론·Celery·격리 코드 실행·실제 주문의 검증 증거는 아니다.
import { randomUUID } from "node:crypto";

import { expect, test } from "@playwright/test";

import {
  CodeStrategySchema,
  GenerateCodeStrategyRequestSchema,
} from "../src/features/strategy/code-schemas";

test("code_generation_preview: 검토 → 적용 → 불변 버전 저장 → 별도 백테스트 요청", async ({
  page,
  request,
  baseURL,
}, testInfo) => {
  const email = `code-journey-${randomUUID()}@dogfood.local`;
  const password = randomUUID();
  const signup = await request.post("/api/auth/sign-up/email", {
    headers: { Origin: baseURL! },
    data: { name: "Python 생성 여정", email, password },
  });
  expect(signup.ok(), `가입 HTTP ${signup.status()}`).toBeTruthy();

  const consoleErrors: string[] = [];
  const pageErrors: string[] = [];
  const calls = { generation: 0, save: 0, backtest: 0, demo: 0 };
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("request", (outgoing) => {
    const path = new URL(outgoing.url()).pathname;
    if (outgoing.method() !== "POST" && outgoing.method() !== "PUT") return;
    if (/\/api\/v1\/strategies\/code(?:\/[0-9a-f-]+)?$/.test(path)) calls.save += 1;
    if (path === "/api/v1/live-sessions") calls.demo += 1;
  });
  const source = 'def on_bar(ctx, state):\n    return {"action": "hold"}\n';
  const provenance = {
    kind: "gemini_generated",
    provider: "gemini",
    requested_model: "ci-fake-gemini",
    actual_model: null,
    test_fixture: true,
  };
  await page.route("**/api/v1/strategies/code/generate", async (route) => {
    calls.generation += 1;
    GenerateCodeStrategyRequestSchema.parse(route.request().postDataJSON());
    await route.fulfill({
      json: {
        status: "preview",
        code: {
          schema_version: 1,
          execution_policy: "code_v1",
          language: "python",
          source_code: source,
          warmup_bars: 200,
          params: {},
          provenance,
        },
        assumptions: ["검증용 가짜 응답이며 hold 의도만 반환합니다."],
        provider: "gemini",
        requested_model: "ci-fake-gemini",
        actual_model: null,
        usage: null,
      },
    });
  });

  const backtestId = randomUUID();
  let strategyId = "";
  let submitted: Record<string, unknown> | null = null;
  await page.route("**/api/v1/backtests", async (route) => {
    if (route.request().method() !== "POST") {
      await route.continue();
      return;
    }
    calls.backtest += 1;
    submitted = route.request().postDataJSON() as Record<string, unknown>;
    await route.fulfill({
      status: 202,
      json: { backtest_id: backtestId, status: "queued", created_at: "2026-01-01T00:00:00Z" },
    });
  });
  await page.route(`**/api/v1/backtests/${backtestId}`, (route) =>
    route.fulfill({
      json: {
        id: backtestId,
        strategy_id: strategyId,
        symbol: "BTC/USDT",
        timeframe: "1h",
        period_start: "2026-01-01T00:00:00Z",
        period_end: "2026-02-01T00:00:00Z",
        status: "queued",
        created_at: "2026-01-01T00:00:00Z",
        completed_at: null,
        initial_capital: "10000",
        config: { execution_policy: "code_v1" },
      },
    }),
  );
  await page.route(`**/api/v1/backtests/${backtestId}/progress`, (route) =>
    route.fulfill({
      json: {
        backtest_id: backtestId,
        status: "queued",
        started_at: null,
        completed_at: null,
        error: null,
      },
    }),
  );

  await page.goto("/sign-in");
  await page.getByLabel("이메일 주소").fill(email);
  await page.getByLabel("비밀번호", { exact: true }).fill(password);
  await page.getByRole("button", { name: "로그인", exact: true }).click();
  await page.waitForURL(/\/(strategies|onboarding)/);
  await page.goto("/strategies/code");
  await expect(page.getByRole("heading", { name: "코드 전략", exact: true })).toBeVisible();
  await page.getByLabel("전략 이름", { exact: true }).fill("Gemini preview 검토 여정");
  await page.getByLabel("진입·청산 조건").fill("이동평균 교차 조건을 Python 코드로 작성해 주세요.");
  await page.getByRole("button", { name: "Python 초안 생성", exact: true }).click();
  await expect(page.getByTestId("code-generation-preview")).toBeVisible();
  await expect(page.getByLabel("소스 코드", { exact: true })).toHaveValue("");
  expect(calls).toEqual({ generation: 1, save: 0, backtest: 0, demo: 0 });
  await expect(page.getByRole("button", { name: "백테스트 실행", exact: true })).toBeDisabled();
  await page.getByRole("button", { name: "이 Python 초안 적용", exact: true }).click();
  await expect(page.getByLabel("소스 코드", { exact: true })).toHaveValue(source);
  expect(calls).toEqual({ generation: 1, save: 0, backtest: 0, demo: 0 });

  const firstSavedResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/v1/strategies/code") && response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "전략 저장", exact: true }).click();
  const firstResponse = await firstSavedResponse;
  expect(firstResponse.ok()).toBeTruthy();
  const first = CodeStrategySchema.parse(await firstResponse.json());
  strategyId = first.id;
  expect(first.version.provenance).toEqual(provenance);
  await expect(page.getByText("저장한 원문과 일치합니다.", { exact: true })).toBeVisible();
  expect(calls.backtest).toBe(0);
  expect(calls.demo).toBe(0);

  await page.getByLabel("소스 코드", { exact: true }).fill(`${source}# 검토 후 수정\n`);
  await expect(page.getByRole("button", { name: "백테스트 실행", exact: true })).toBeDisabled();
  const secondSavedResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith(`/api/v1/strategies/code/${strategyId}`) &&
      response.request().method() === "PUT",
  );
  await page.getByRole("button", { name: "새 버전 저장", exact: true }).click();
  const secondResponse = await secondSavedResponse;
  expect(secondResponse.ok()).toBeTruthy();
  const second = CodeStrategySchema.parse(await secondResponse.json());
  expect(second.version.id).not.toBe(first.version.id);
  expect(second.version.source_hash).not.toBe(first.version.source_hash);
  expect(second.version.provenance).toEqual({
    origin: "manual_editor",
    parent_version_id: first.version.id,
  });
  await expect(page.getByText("저장한 원문과 일치합니다.", { exact: true })).toBeVisible();
  await page.getByLabel("시작일 (UTC)", { exact: true }).fill("2026-01-01");
  await page.getByLabel("종료일 (UTC·미포함)", { exact: true }).fill("2026-02-01");
  await page.getByRole("button", { name: "백테스트 실행", exact: true }).click();
  await page.waitForURL(`**/backtests/${backtestId}`);
  await expect(page.getByTestId("backtest-in-progress")).toBeVisible();
  expect(submitted).toMatchObject({
    strategy_id: strategyId,
    execution_policy: "code_v1",
    fill_timing: "next_bar_open",
    leverage: "1",
    include_funding: true,
  });
  expect(calls).toEqual({ generation: 1, save: 2, backtest: 1, demo: 0 });
  expect(pageErrors).toEqual([]);
  expect(consoleErrors).toEqual([]);
  await testInfo.attach("code-generation-boundary.json", {
    body: JSON.stringify(
      {
        actual: ["인증", "코드 저장 API", "DB 불변 버전"],
        replaced: ["Gemini 생성 응답", "백테스트 접수·조회"],
        strategyId,
        firstVersion: first.version.id,
        secondVersion: second.version.id,
        calls,
        consoleErrors,
        pageErrors,
      },
      null,
      2,
    ),
    contentType: "application/json",
  });
  await page.screenshot({ path: testInfo.outputPath("code-backtest-request.png"), fullPage: true });
});
