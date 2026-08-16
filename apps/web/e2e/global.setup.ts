// authed e2e 의 로그인 하네스 — 실제 `/sign-in` 폼을 채워 storageState 를 만든다(ADR-034).
//
// ★★2026-08-17 반증 — 종전 이 파일의 `clerkSetup()` 이 **e2e 의 유일한 `.env.local` 로더**였다.
//   `playwright.config.ts` 에는 dotenv 가 없다(2026-08-14 [BL-707] 이 같은 사실을 다른 증상으로
//   밟았다). Clerk 를 걷어내면 env 로딩이 **조용히** 사라지므로 여기서 명시적으로 읽는다.
//
// Required env (apps/web/.env.local):
//   E2E_AUTH_EMAIL / E2E_AUTH_PASSWORD  — 로컬 개발 DB 의 e2e 전용 계정
//
// 매 실행마다 storageState 를 새로 발급 → 세션 만료를 자동 처리한다.

import { existsSync } from "node:fs";
import path from "node:path";

import { expect, test as setup } from "@playwright/test";

import { getBaseURL } from "./_base-url";

const REQUIRED_ENV = ["E2E_AUTH_EMAIL", "E2E_AUTH_PASSWORD"] as const;
const STORAGE_PATH = "e2e/.auth/storageState.json";

/** `.env.local` → `.env` 순으로 읽어 **아직 없는 키만** 채운다(실제 셸 env 가 우선). */
function loadEnvFiles(): void {
  for (const name of [".env.local", ".env"]) {
    const file = path.resolve(process.cwd(), name);
    if (!existsSync(file)) continue;
    // Node 20+ 내장 로더. dotenv 의존성을 새로 들이지 않는다.
    process.loadEnvFile?.(file);
  }
}

setup("authenticate", async ({ page, request }) => {
  // Sprint 46 W3: pre-warm 4 paths × Next.js cold JIT compile (5-30s each) →
  // 합산 1-2 분 소요. default 30s test timeout 으론 부족.
  setup.setTimeout(240_000);

  loadEnvFiles();
  for (const key of REQUIRED_ENV) {
    if (!process.env[key]) {
      throw new Error(
        `[e2e setup] ${key} 미설정. apps/web/.env.local 을 채워라 (.env.example 의 e2e 절 참조).`,
      );
    }
  }
  const email = process.env.E2E_AUTH_EMAIL!;
  const password = process.env.E2E_AUTH_PASSWORD!;
  const baseUrl = getBaseURL();

  // 0) 계정 부트스트랩 — 없으면 만든다. 이미 있으면 서버가 거부하고 그대로 진행한다.
  //    ★로컬 개발 DB 전용 편의다. 상태를 지우지 않으므로 재실행에 안전하다.
  const signUp = await request.post(`${baseUrl}/api/auth/sign-up/email`, {
    data: { name: "E2E", email, password },
    failOnStatusCode: false,
  });
  if (!signUp.ok() && signUp.status() !== 422 && signUp.status() !== 400) {
    // 409/422 계열(이미 존재)만 정상 통과시킨다. 그 밖의 실패는 조용히 넘기지 않는다.
    const body = await signUp.text();
    throw new Error(
      `[e2e setup] 계정 부트스트랩이 예상 밖 status 로 실패했다: ${signUp.status()} ${body.slice(0, 200)}`,
    );
  }

  // 1) sign-in 페이지 방문 — 포트에 다른 앱이 떠 있는 경우를 여기서 잡는다([BL-707]).
  const signInUrl = new URL("/sign-in", baseUrl).toString();
  const signInResponse = await page.goto(signInUrl, { timeout: 120_000 });
  const signInStatus = signInResponse?.status() ?? "응답 없음";
  if (signInStatus !== 200) {
    throw new Error(
      `[e2e setup] sign-in HTTP status 검증 실패. 요청 URL: ${signInUrl}, 받은 status: ${signInStatus}. 이 포트에 다른 앱이 떠 있을 수 있다.`,
    );
  }

  const pageTitle = await page.title();
  if (!pageTitle.includes("QuantBridge")) {
    throw new Error(
      `[e2e setup] QuantBridge 정체성 확인 실패. 요청 URL: ${signInUrl}, 실제 title 원문: ${JSON.stringify(pageTitle)}`,
    );
  }

  // 2) 실제 로그인 폼을 채운다 — 프로그래매틱 API 가 아니라 **화면**을 지난다.
  //    ★이것이 Clerk 시절보다 나아진 점이다: 로그인 화면이 깨지면 이 setup 이 먼저 죽는다.
  await page.getByLabel("이메일 주소").fill(email);
  await page.getByLabel("비밀번호").fill(password);
  await page.getByRole("button", { name: "로그인" }).click();

  // ★★클릭 뒤 **반드시 기다려야 한다.** 종전 `clerk.signIn()` 은 흐름 전체를 await 했지만
  //   진짜 폼 제출은 클릭 시점에 fetch 가 in-flight 로 남는다. 곧바로 `page.goto('/strategies')`
  //   를 하면 쿠키가 아직 없어 proxy 가 `/sign-in` 으로 되돌리고, 증상은 「로그인이 안 된다」로
  //   보인다(실측 — 이 하네스를 옮기면서 실제로 밟았다). 폼이 성공하면 `/sign-in` 을 떠난다.
  await page.waitForURL((url) => !url.pathname.startsWith("/sign-in"), { timeout: 60_000 });

  // 3) Protected route 검증 — pathname + UI text 둘 다 (codex iter 2 P1 #3)
  // 단순 waitForURL(/strategies/) 은 query param 에 strategies 포함된 unauth redirect 통과.
  await page.goto(`${baseUrl}/strategies`, { timeout: 60_000 });
  await expect(page).toHaveURL(({ pathname }) => pathname === "/strategies", {
    timeout: 30_000,
  });
  // 페이지 로드 완료 + 인증된 사용자만 보이는 heading (C 이식 screen-06: report-title "전략")
  await expect(page.getByRole("heading", { name: "전략", exact: true })).toBeVisible({
    timeout: 30_000,
  });

  // 4) Pre-warm — chromium-authed 프로젝트의 첫 spec 이 dev server JIT compile 안 만나도록
  // 모든 protected page 미리 방문해서 컴파일 cache 채움. 각 페이지 첫 컴파일 5-30초.
  const preWarmPaths = ["/trading", "/backtests/new", "/strategies/new"];
  for (const path of preWarmPaths) {
    await page.goto(`${baseUrl}${path}`, { timeout: 60_000 });
    // networkidle 까지 대기 — RSC + client query 완료 보장
    await page.waitForLoadState("networkidle", { timeout: 60_000 });
  }

  // 5) storageState 저장 — chromium-authed project 가 dependency 로 활용
  await page.context().storageState({ path: STORAGE_PATH });
});
