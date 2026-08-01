// BL-570 — 트레이딩 설정 저장이 조용히 죽지 않는지 실브라우저에서 판정한다.
//
// ★이 결함은 **jsdom 에서 재현되지 않는다** (jsdom 은 버튼을 disabled 로 낸다). 그래서
//   1232개 단위 테스트가 전부 초록인 채로 세 회차를 살아남았다 — 실브라우저 몫이다.
//
// 기전(2026-08-01 실측 확정): RHF 는 registration 시점에 **DOM 문자열이 아니라 defaultValue 를
// 그대로** `setValueAs` 에 넘긴다. 그래서 `""` 만 거르던 구현에서는 `null` 이 새어
// `Number(null) === 0` 이 되고, zod `.gt(0)` 이 그 0 을 거부해 `handleSubmit` 이 막혔다.
// 화면에는 요청도 토스트도 필드 에러도 남지 않았다.
//
// 사전등록 매핑 — Z1/Z2 = "무편집 클릭이 침묵하지 않는다", Z2b = "검증 탈락이 화면에 보인다",
// Z4 = 음성 대조("편집 후 저장"이 그대로 200).

import { test, expect, type Page } from "@playwright/test";

const STRATEGY_ID = process.env.QB_BL570_STRATEGY_ID ?? "0d94167b-8c24-444b-a124-870a2a9f0243";
const EDIT_URL = `/strategies/${STRATEGY_ID}/edit`;
const SAVE_BUTTON = /설정 저장|설정 등록/;

async function gotoSettings(page: Page) {
  await page.goto(EDIT_URL, { waitUntil: "domcontentloaded" });
  // heading 은 화면에 2개라 입력칸 자체를 기다린다.
  await page.locator("#s-lev").waitFor({ timeout: 60_000 });
  await page.locator("#s-trigger-breach-cap").waitFor({ timeout: 60_000 });
}

/** PUT /strategies/{id}/settings 응답 상태를 수집한다. */
function trackSettingsPuts(page: Page) {
  const puts: number[] = [];
  page.on("response", (r) => {
    if (r.request().method() === "PUT" && r.url().includes("/settings")) puts.push(r.status());
  });
  return puts;
}

test.describe("BL-570 트레이딩 설정 저장", () => {
  test("Z1/Z2 — 무편집 저장이 조용히 죽지 않는다", async ({ page }) => {
    const puts = trackSettingsPuts(page);
    await gotoSettings(page);

    const btn = page.getByRole("button", { name: SAVE_BUTTON });
    // ★클릭 전 disabled 를 먼저 읽는다 — 이걸 빼먹으면 "이미 disabled 라 클릭이 무효였던 것"을
    //   "요청이 안 나갔다"로 오독한다(2026-08-01 교란 사례).
    const disabledBefore = await btn.isDisabled();

    if (!disabledBefore) {
      await btn.click();
      await page.waitForTimeout(2000);
    }

    const toasts = await page.locator("[data-sonner-toast]").allTextContents();
    const fieldErrors = await page.locator(".field-error").allTextContents();

    // Z2 — 셋 중 하나는 반드시 참이어야 한다. 셋 다 거짓인 상태가 정확히 BL-570 이었다.
    const savedOk = puts.includes(200);
    const gaveFeedback = toasts.length > 0 || fieldErrors.length > 0;
    expect(
      disabledBefore || savedOk || gaveFeedback,
      `무편집 저장이 침묵했다 — disabled=${disabledBefore} puts=${JSON.stringify(puts)} ` +
        `toasts=${JSON.stringify(toasts)} fieldErrors=${JSON.stringify(fieldErrors)}`,
    ).toBe(true);
  });

  test("Z2b — 검증 탈락은 화면에 보인다 (토스트 + 필드 에러)", async ({ page }) => {
    const puts = trackSettingsPuts(page);
    await gotoSettings(page);

    // ★상한 입력에 `0` 을 넣는다. `min={0}` 이라 **브라우저 네이티브 검증은 통과**하고
    //   zod `.gt(0)` 만 거부한다 — 즉 handleSubmit 이 실제로 돌아 onInvalid 까지 도달한다.
    //   (`leverage=999` 같은 native 위반은 submit 이벤트 자체가 안 나서 이 경로를 검사하지 못한다.)
    await page.locator("#s-trigger-breach-cap").fill("0");
    await page.getByRole("button", { name: SAVE_BUTTON }).click();
    await page.waitForTimeout(2000);

    expect(puts, "검증 탈락인데 요청이 나갔다").not.toContain(200);
    await expect(
      page.locator("[data-sonner-toast]").filter({ hasText: "저장하지 못했습니다" }),
      "onInvalid 토스트가 뜨지 않았다 — 검증 탈락이 다시 침묵한다",
    ).toBeVisible();
    await expect(
      page.locator(".field-error").first(),
      "필드 에러가 렌더되지 않았다",
    ).toBeVisible();
  });

  test("Z4 — 편집 후 저장은 그대로 200 (음성 대조)", async ({ page }) => {
    const puts = trackSettingsPuts(page);
    await gotoSettings(page);

    const lev = page.getByLabel("레버리지 (1 ~ 125)");
    const original = await lev.inputValue();
    const probe = original === "3" ? "2" : "3";

    await lev.fill(probe);
    await page.getByRole("button", { name: SAVE_BUTTON }).click();
    await expect(
      page.locator("[data-sonner-toast]").filter({ hasText: "트레이딩 설정을 저장했습니다" }),
    ).toBeVisible({ timeout: 15_000 });
    expect(puts).toContain(200);

    // ★원장을 원상복구한다 — 이 spec 은 반복 실행돼도 설정을 바꾸지 않는다.
    await gotoSettings(page);
    await page.getByLabel("레버리지 (1 ~ 125)").fill(original);
    await page.getByRole("button", { name: SAVE_BUTTON }).click();
    await expect(
      page.locator("[data-sonner-toast]").filter({ hasText: "트레이딩 설정을 저장했습니다" }),
    ).toBeVisible({ timeout: 15_000 });
    await expect(page.getByLabel("레버리지 (1 ~ 125)")).toHaveValue(original);
  });
});
