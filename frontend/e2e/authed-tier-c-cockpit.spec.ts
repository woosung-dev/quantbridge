// 인증된 코크핏 KPI·§08 진단 카드의 라이브 구조 불변식을 검증한다.
import { expect, test } from "@playwright/test";

test("코크핏 잔고·포지션 섹션과 진단 카드 2장을 렌더한다", async ({ page }) => {
  await page.goto("/trading", { timeout: 60_000 });

  // 미실현 추정 KPI 는 환경에 따라 두 정직 상태를 가진다 — 활성 세션 0 이면 0.00,
  // 활성 세션 ≥1 이고 ticker 미수신이면 "시세 수신 대기" (e2e 는 WS 미연결).
  await expect(page.getByText("미실현 손익 · 추정")).toBeVisible();
  await expect(page.getByTestId("kpi-unrealized-pnl")).toHaveText(
    /^(시세 수신 대기|[+-]?0\.00 USDT)$/,
  );
  await expect(page.getByText("총 세션")).toHaveCount(0);
  await expect(page.getByTestId("account-balance-section")).toBeVisible();
  await expect(page.getByTestId("open-positions-table")).toBeVisible();
  await expect(page.getByText("활성 라이브 세션이 없습니다.").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "포지션 동기화" })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "알림 규칙" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "실시간 가격 스트림" })).toBeVisible();
});
