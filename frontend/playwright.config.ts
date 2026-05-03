import { defineConfig, devices } from "@playwright/test";

// Sprint FE-01 LESSON-004: React Query + Next.js 조합 infinite loop 검출용 E2E.
// vitest jsdom이 못 잡는 Fast Refresh / StrictMode / Query refetch 케이스 실제 브라우저 재현.
//
// CI/로컬 모두 pnpm dev 사용 — prod build는 Clerk API 의존 페이지가 prerender 실패.
// dev는 Clerk placeholder key로도 기동 가능. CI ubuntu는 초기 컴파일이 느리니 240s 대기.
//
// Sprint 25 — projects 분리 (codex G.0 iter 1 P1 #4 + iter 2 P2 #3):
//   chromium         — public routes only (smoke.spec.ts)
//   chromium-authed  — Clerk authed only (trading-ui, dogfood-flow). storageState 의존
//   setup            — global.setup.ts 가 chromium-authed 시작 전 storageState 발급
//
// chromium-authed 는 fullyParallel:false + --workers=1 (script 명시) 이중 보장 —
// 공유 storageState flake 차단.
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
      name: "setup",
      testMatch: /global\.setup\.ts$/,
    },
    {
      name: "chromium",
      testMatch: /smoke\.spec\.ts$/,
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "chromium-authed",
      testMatch: /(trading-ui|dogfood-flow)\.spec\.ts$/,
      fullyParallel: false,
      use: {
        ...devices["Desktop Chrome"],
        storageState: "e2e/.auth/storageState.json",
      },
      dependencies: ["setup"],
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
