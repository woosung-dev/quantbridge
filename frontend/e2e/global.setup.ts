// Sprint 25 — Clerk Testing 공식 setup (codex G.0 iter 2 P1 #1+#2+#3 반영).
//
// `clerkSetup()` 단독으로는 인증되지 않음. Testing Token 은 bot detection bypass 만,
// user login 별도 호출 필요 → `clerk.signIn()` 으로 자동화.
//
// Required env (frontend/.env.local 채워야 함):
//   CLERK_PUBLISHABLE_KEY    (test runner 용 — NEXT_PUBLIC_ prefix 와 별도)
//   CLERK_SECRET_KEY         (Testing Token 발급)
//   E2E_CLERK_USER_EMAIL     (Clerk Dashboard 에서 dev 계정 1개)
//   E2E_CLERK_USER_PASSWORD
//
// 매 e2e:authed 실행 시 storageState 새로 발급 → 만료 자동 처리.
// Protected route 검증 (pathname + UI text 둘 다) — query param 우회 차단.

import { clerk, clerkSetup } from "@clerk/testing/playwright";
import { expect, test as setup } from "@playwright/test";

const REQUIRED_ENV = [
  "CLERK_PUBLISHABLE_KEY",
  "CLERK_SECRET_KEY",
  "E2E_CLERK_USER_EMAIL",
  "E2E_CLERK_USER_PASSWORD",
] as const;

const STORAGE_PATH = "e2e/.auth/storageState.json";

setup("authenticate", async ({ page }) => {
  // Sprint 25 codex G.2 P1 #1 fix — clerkSetup() 이 .env.local 을 로드하므로 env 검증을
  // 그 호출 후 실시. 호출 전 검증 시 dotenv 로딩 전 fail 하여 .env.local 사용자 깨짐.
  // Clerk Testing Token 발급 (CLERK_PUBLISHABLE_KEY + CLERK_SECRET_KEY 사용)
  await clerkSetup();

  // Env 검증 — fail loud (사용자가 .env.local 채울 안내)
  for (const key of REQUIRED_ENV) {
    if (!process.env[key]) {
      throw new Error(
        `[e2e setup] ${key} 미설정. frontend/.env.local 채울 것 (.env.example Sprint 25 섹션 참조).`,
      );
    }
  }

  const baseUrl =
    process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000";

  // 1) sign-in 페이지 방문 → 2) Testing Token 자동 첨부 → 3) clerk.signIn()
  await page.goto(`${baseUrl}/sign-in`);
  await clerk.signIn({
    page,
    signInParams: {
      strategy: "password",
      identifier: process.env.E2E_CLERK_USER_EMAIL!,
      password: process.env.E2E_CLERK_USER_PASSWORD!,
    },
  });

  // 4) Protected route 검증 — pathname + UI text 둘 다 (codex iter 2 P1 #3)
  // 단순 waitForURL(/strategies/) 은 query param 에 strategies 포함된 unauth redirect 통과.
  // Next.js 16 dev server 첫 page render 가 JIT 컴파일로 5-30초 → timeout 60s
  await page.goto(`${baseUrl}/strategies`, { timeout: 60_000 });
  await expect(page).toHaveURL(({ pathname }) => pathname === "/strategies", {
    timeout: 30_000,
  });
  // 페이지 로드 완료 + 인증된 사용자만 보이는 heading
  await expect(
    page.getByRole("heading", { name: "내 전략" }),
  ).toBeVisible({ timeout: 30_000 });

  // 5) Pre-warm — chromium-authed 프로젝트의 첫 spec 이 dev server JIT compile 안 만나도록
  // 모든 protected page 미리 방문해서 컴파일 cache 채움. 각 페이지 첫 컴파일 5-30초.
  // pre-warm 후 후속 spec 의 page.goto 는 cache hit → 즉시 렌더.
  const preWarmPaths = ["/trading", "/backtests/new", "/strategies/new"];
  for (const path of preWarmPaths) {
    await page.goto(`${baseUrl}${path}`, { timeout: 60_000 });
    // networkidle 까지 대기 — RSC + client query 완료 보장
    await page.waitForLoadState("networkidle", { timeout: 60_000 });
  }

  // 6) storageState 저장 — chromium-authed project 가 dependency 로 활용
  await page.context().storageState({ path: STORAGE_PATH });
});
