import { expect, test } from "@playwright/test";

// Sprint FE-01 LESSON-004 E2E smoke.
// 목적:
// - Next.js dev/production 번들 + React Query 실제 동작 + Clerk 인증이
//   단위 테스트로는 재현 불가한 infinite-loop / render-storm을 검출.
// - 핵심 happy path가 렌더 폭주 없이 정상 동작하는지 5초 내로 확인.
//
// Clerk dev 키 / 로그인은 CI에서 별도 e2e-auth 플로우로 주입 예정 (미래).
// 지금은 landing / sign-in 리다이렉트 + 공용 페이지만 검증.

test("landing page renders without render storm", async ({ page }) => {
  const responses: number[] = [];
  page.on("response", (r) => responses.push(r.status()));

  await page.goto("/");
  await expect(page).toHaveTitle(/QuantBridge/i);

  // 네트워크 요청이 100건 초과면 polling/loop 의심
  expect(
    responses.filter((s) => s < 400).length,
    "landing should not trigger more than 50 successful requests",
  ).toBeLessThan(50);
});

test("strategies redirect to sign-in (auth gate works)", async ({ page }) => {
  await page.goto("/strategies");
  // Clerk sign-in 페이지로 리다이렉트되는지 URL 확인
  await page.waitForURL(/sign-in|accounts\.dev/, { timeout: 10_000 });
  await expect(page).not.toHaveURL(/\/strategies$/);
});

test("no console errors on landing (LESSON-004 render loop proxy)", async ({
  page,
}) => {
  const consoleErrors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });

  await page.goto("/");
  // 2초 대기하며 추가 console error 포집 (render loop이면 계속 에러 찍힘)
  await page.waitForTimeout(2_000);

  // Clerk dev keys 경고는 무시
  const relevantErrors = consoleErrors.filter(
    (e) =>
      !e.includes("development keys") &&
      !e.includes("Clerk has been loaded"),
  );

  expect(
    relevantErrors,
    `console errors found:\n${relevantErrors.join("\n")}`,
  ).toHaveLength(0);
});
