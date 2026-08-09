// BL-397 — 백테스트 리포트 섹션 앵커 딥링크
//
// `/backtests/<id>#<앵커>` 로 리포트의 특정 섹션을 공유할 수 있어야 한다.
// 착수 시점 실측: `<Section>` 10개 중 `id` 를 받는 것이 08(`stress-test`) 하나뿐이라
// 나머지 아홉은 링크로 도달할 수 없었다.
//
// ★여기가 이 계약의 진짜 판정자다. vitest 는 jsdom 이라 레이아웃을 계산하지 않으므로
//   "섹션이 뷰포트에 들어왔는가" 도 "제목이 상단바에 가렸는가" 도 잴 수 없다.
//   그래서 두 축을 서로 다른 어서션으로 나눠 둔다 (변이 M3 이 그 분리를 실증한다).
//
// chromium-authed project — Clerk storageState 필요. API 는 전부 mock 이라 DB 무관.

import { expect, test } from "@playwright/test";

import { API_ROUTES, fulfillJson } from "./fixtures/api-mock";
import {
  MOCK_BACKTEST_DETAIL,
  MOCK_BACKTEST_ID,
  routeBacktestDetail,
} from "./fixtures/backtest-report";

// `.topbar` 는 sticky, `--topbar-h: 60px` (`globals.css`). 앵커 스크롤이 섹션 상단을
// y=0 에 맞추면 그 아래로 제목이 숨는다.
const TOPBAR_H = 60;

// ★`mode: "serial"` 을 쓰지 않는다. 이 파일의 둘째 테스트는 첫째의 음성 대조라
//   첫째가 red 일 때도 반드시 돌아야 한다. serial 이면 건너뛰어서 "판별력이 있었는지" 를
//   알 수 없게 된다(실측: 착수 baseline 에서 정확히 그렇게 skip 됐다).
//   flake 방어는 project 의 `fullyParallel: false` + `--workers=1` 이 이미 한다.

test.beforeEach(async ({ page }) => {
  await routeBacktestDetail(page, MOCK_BACKTEST_DETAIL);
  await page.route(API_ROUTES.stressTests, fulfillJson({ items: [], total: 0 }));
});

test("#trades 로 진입하면 04 거래 내역 섹션이 뷰포트에 들어온다", async ({ page }) => {
  await page.goto(`/backtests/${MOCK_BACKTEST_ID}#trades`, { timeout: 60_000 });
  await expect(page.getByTestId("backtest-report-shell")).toBeVisible({
    timeout: 30_000,
  });

  const trades = page.locator("section#trades");
  await expect(trades).toHaveCount(1);
  await expect(trades).toBeInViewport();

  // 축 2 — 뷰포트에 들어온 것만으로는 읽을 수 있다는 뜻이 아니다. 섹션 제목이
  // sticky 상단바 아래에 깔리면 사용자는 자기가 어느 섹션에 왔는지 못 본다.
  const heading = trades.locator("h2.section-title");
  await expect(heading).toBeVisible();
  const box = await heading.boundingBox();
  expect(box).not.toBeNull();
  expect(box!.y).toBeGreaterThanOrEqual(TOPBAR_H);
});

test("없는 fragment 로 들어와도 리포트가 정상 렌더된다", async ({ page }) => {
  // ★음성 대조. 앵커를 붙이는 변경이 "모르는 fragment 를 만나면 깨진다" 로 번지지 않는지 본다.
  const consoleErrors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });

  await page.goto(`/backtests/${MOCK_BACKTEST_ID}#nope`, { timeout: 60_000 });
  await expect(page.getByTestId("backtest-report-shell")).toBeVisible({
    timeout: 30_000,
  });

  // 매칭되는 대상이 없으면 브라우저는 스크롤하지 않는다 = 상단에 머문다.
  const scrollY = await page.evaluate(() => window.scrollY);
  expect(scrollY).toBeLessThan(50);

  expect(consoleErrors).toEqual([]);
});
