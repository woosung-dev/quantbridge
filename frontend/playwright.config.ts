import { defineConfig, devices } from "@playwright/test";

// Sprint FE-01 LESSON-004: React Query + Next.js 조합 infinite loop 검출용 E2E.
// vitest jsdom이 못 잡는 Fast Refresh / StrictMode / Query refetch 케이스 실제 브라우저 재현.
//
// CI/로컬 모두 pnpm dev 사용 — prod build는 Clerk API 의존 페이지가 prerender 실패.
// dev는 Clerk placeholder key로도 기동 가능. CI ubuntu는 초기 컴파일이 느리니 240s 대기.
const isCI = !!process.env.CI;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: isCI,
  retries: isCI ? 2 : 0,
  workers: isCI ? 1 : undefined,
  reporter: isCI ? [["github"], ["list"]] : "list",
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000",
    trace: "retain-on-failure",
    video: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: process.env.PLAYWRIGHT_BASE_URL
    ? undefined
    : {
        command: "pnpm dev",
        url: "http://localhost:3000",
        reuseExistingServer: !isCI,
        timeout: isCI ? 240_000 : 120_000,
        stdout: "pipe",
        stderr: "pipe",
      },
});
