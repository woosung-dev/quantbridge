// 차트 팔레트 CSS 변수가 실제로 구동 중인 앱에서 해석되는지 검사하는 이식 안전망
//
// 자매 검사 `src/__tests__/chart-tokens-contract.test.ts` 는 소스 텍스트만 본다.
// vitest 는 jsdom 이고 jsdom 은 getComputedStyle 로 커스텀 프로퍼티를 해석하지 못하므로,
// "정말 해석되는가" 는 실제 브라우저에서만 확인할 수 있다. 그 절반이 이 파일이다.
//
// 공개 라우트(`/`)만 쓴다 — Clerk 인증이 필요 없어야 CI 에서 돌릴 수 있다.
// P1 4라우트(전부 authed)의 캐논 검사는 로컬 `pnpm e2e:authed` 몫이다.

import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

/**
 * resolveChartTokens() 가 읽는 변수 전체.
 * `src/lib/chart-tokens.ts` 와 `src/__tests__/chart-tokens-contract.test.ts` 의
 * CHART_TOKEN_CONTRACT 와 같은 목록을 유지해야 한다. 계약이 어긋나면 자매 검사가 빨개진다.
 */
const CHART_TOKEN_CONTRACT = [
  "--bullish",
  "--bearish",
  "--chart-equity",
  "--chart-benchmark",
  "--chart-compare",
  "--text-muted",
  "--border",
  "--chart-dd-line",
  "--chart-dd-top",
  "--chart-dd-bottom",
] as const;

/** 루트에서 변수를 읽는다. chart-tokens.ts 의 read() 와 같은 경로다. */
async function readRootTokens(
  page: Page,
  names: readonly string[],
): Promise<Record<string, string>> {
  return page.evaluate((tokenNames) => {
    const style = getComputedStyle(document.documentElement);
    const out: Record<string, string> = {};
    for (const name of tokenNames) {
      out[name] = style.getPropertyValue(name).trim();
    }
    return out;
  }, names as string[]);
}

test.describe("차트 팔레트 런타임 해석 (이식 S1a 안전망)", () => {
  test("다크 테마에서 10개 변수가 전부 해석된다", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("body")).toBeVisible();

    const resolved = await readRootTokens(page, CHART_TOKEN_CONTRACT);

    const unresolved = Object.entries(resolved)
      .filter(([, value]) => value === "")
      .map(([name]) => name);
    expect(
      unresolved,
      `해석되지 않은 변수 — chart-tokens.ts 가 폴백으로 조용히 떨어진다: ${unresolved.join(", ")}`,
    ).toEqual([]);
  });

  test("라이트 테마에서도 10개 변수가 전부 해석된다", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("body")).toBeVisible();

    // next-themes 는 html 에 클래스를 얹는다. `.dark` 를 걷어내면 `:root` 값이 드러난다.
    await page.evaluate(() => document.documentElement.classList.remove("dark"));

    const resolved = await readRootTokens(page, CHART_TOKEN_CONTRACT);

    const unresolved = Object.entries(resolved)
      .filter(([, value]) => value === "")
      .map(([name]) => name);
    expect(
      unresolved,
      `:root 에서 해석되지 않은 변수: ${unresolved.join(", ")}`,
    ).toEqual([]);
  });

  test("다크와 라이트가 서로 다른 값을 준다 (테마 인지 확인)", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("body")).toBeVisible();

    const dark = await readRootTokens(page, CHART_TOKEN_CONTRACT);
    await page.evaluate(() => document.documentElement.classList.remove("dark"));
    const light = await readRootTokens(page, CHART_TOKEN_CONTRACT);

    // 전부 같다면 `.dark` 블록이 실제로는 적용되지 않고 있다는 뜻이다.
    const differing = CHART_TOKEN_CONTRACT.filter(
      (name) => dark[name] !== light[name],
    );
    expect(
      differing.length,
      `다크와 라이트가 같은 값을 준다. .dark 블록이 적용되지 않는다`,
    ).toBeGreaterThan(0);
  });
});
