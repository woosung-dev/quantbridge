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
    // Sprint 25 — Next.js 16 dev server 첫 page render JIT 컴파일 5-30초.
    // setup pre-warm 후 cache hit 으로 빨라지지만 안전망으로 navigation 60s, action 30s.
    navigationTimeout: 60_000,
    actionTimeout: 30_000,
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
    // Sprint 31-D BL-157 — live dev smoke gate (.github/workflows/live-smoke.yml 전용).
    // public pages (Clerk 미의존) console.error / pageerror 0 검증 — chart lib
    // SSR/CSR boundary throw 같은 dogfood Day 3 currentColor 회귀 차단.
    // 별도 project 로 분리한 이유: 기본 `chromium` 은 smoke.spec.ts 만 매치하므로
    // live-smoke 는 명시적 --project 호출 (e2e 워크플로우 영향 없음).
    {
      name: "chromium-live-smoke",
      testMatch: /live-smoke\.spec\.ts$/,
      use: { ...devices["Desktop Chrome"] },
    },
    // C 디자인 언어 이식 S0 — 인증 없는 디자인 캐논 게이트.
    // 공개 라우트만 쓰므로 CI 에서 돌릴 수 있다 (`pnpm e2e:design-canon`).
    // P1 4라우트는 전부 authed 라 `chromium-authed` 몫이고 로컬 전용이다.
    {
      name: "chromium-design-canon",
      testMatch: /design-canon-.*\.spec\.ts$/,
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "chromium-authed",
      // Sprint 38 BL-188 v3 D — `backtest-live-mirror` 추가 (5 case Live mirror E2E).
      // Sprint 46 W2 — `sprint46-tier1-critical` 추가 (5 case Tier 1 critical user journey).
      // Sprint 46 W3 — `sprint46-tier2-high` 추가 (4 case Tier 2 dogfood polish).
      // Sprint 46 W4 — `sprint46-tier3-nth` 추가 (Tier 3 polish 7 시나리오).
      // C 이식 S0 — `sprint55-optimizer-bayesian` 은 배선하지 않는다. testMatch 에 넣어 실행하니
      //   폼 UX 가 통째로 stale (텍스트 backtest_id 입력 -> useBacktests 드롭다운 피커, P1-8/S7-B).
      //   파일 안 test.skip + TODO 로 남겨 optimizer 이식 때 현행 UX 로 재작성한다.
      // C 이식 S0 — `authed-canon-p1` 추가 (P1 4라우트 디자인 캐논 baseline, 로컬 전용).
      // C 이식 W2 — `authed-canon-remaining` 추가 (잔여 authed 라우트 캐논 게이트, /backtests/[id] 등).
      //   열거식 testMatch 라 파일명을 여기 넣지 않으면 spec 이 발견조차 안 된다 (coverage 함정).
      testMatch:
        /(trading-ui|dogfood-flow|live-session-flow|sprint32-dogfood-gate|backtest-live-mirror|sprint46-tier1-critical|sprint46-tier2-high|sprint46-tier3-nth|authed-canon-p1|authed-canon-remaining)\.spec\.ts$/,
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
