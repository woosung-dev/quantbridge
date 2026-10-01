import { defineConfig, devices } from "@playwright/test";

import { getBaseURL } from "./e2e/_base-url";

export default defineConfig({
  testDir: "./e2e",
  testMatch: /verified-strategy-journey\.spec\.ts$/,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 300_000,
  expect: { timeout: 30_000 },
  outputDir: "test-results/verified-journey",
  reporter: [["list"], ["json", { outputFile: "test-results/verified-journey/results.json" }]],
  use: {
    ...devices["Desktop Chrome"],
    baseURL: getBaseURL(),
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: process.env.CI
    ? {
        command: "pnpm dev --port 3100",
        url: getBaseURL(),
        timeout: 240_000,
        reuseExistingServer: false,
      }
    : undefined,
});
