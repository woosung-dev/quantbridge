// 인증된 코크핏 §06 진단 카드의 라이브 구조 불변식을 검증한다.
import { expect, test } from "@playwright/test";

test("코크핏 진단 카드 3장과 세션 미선택 안내를 렌더한다", async ({ page }) => {
  await page.goto("/trading", { timeout: 60_000 });

  await expect(page.getByRole("heading", { name: "포지션 동기화" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "알림 규칙" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "실시간 가격 스트림" })).toBeVisible();
  await expect(
    page.getByText("세션을 선택하면 거래소 포지션을 대조합니다."),
  ).toBeVisible();
});
