// 종단 데모 리허설 — G4 화면 검증. 렌더된 페이지에서 확인한다(API 응답·DB 행으로 대체 금지).
// storageState 재사용 → 자격증명이 이 프로세스에 들어오지 않는다.
// 실행: node e2e/.demo-rehearsal.mjs  (BASE 기본 http://localhost:3100)
import { chromium } from "@playwright/test";
import { mkdirSync } from "node:fs";

const BASE = process.env.DEMO_BASE_URL ?? "http://localhost:3100";
const STATE = process.env.DEMO_STATE ?? "e2e/.auth/storageState.json";
const OUT = process.env.DEMO_OUT ?? "e2e/.demo-shots";
mkdirSync(OUT, { recursive: true });

const ROUTES = [
  ["01-strategies", "/strategies"],
  ["02-backtests", "/backtests"],
  ["03-optimizer", "/optimizer"],
  ["04-orders", "/orders"],
  ["05-trading", "/trading"],
  ["06-dashboard", "/dashboard"],
];

const browser = await chromium.launch();
const ctx = await browser.newContext({ storageState: STATE, viewport: { width: 1440, height: 900 } });
const page = await ctx.newPage();

const consoleErrors = [];
page.on("console", (m) => {
  if (m.type() === "error") consoleErrors.push(`${m.location().url}: ${m.text()}`.slice(0, 240));
});

for (const [slug, route] of ROUTES) {
  const res = await page.goto(BASE + route, { waitUntil: "domcontentloaded", timeout: 120_000 });
  await page.waitForTimeout(3500); // 데이터 패칭 + 첫 컴파일
  const title = await page.title();
  const h1 = await page.locator("h1, h2.section-title, .report-title").first().textContent().catch(() => null);
  const rows = await page.locator("tbody tr").count();
  const chips = await page.locator('td .chip, [data-lifecycle]').allTextContents().catch(() => []);
  const bodyText = (await page.locator("body").innerText().catch(() => "")).replace(/\s+/g, " ");
  await page.screenshot({ path: `${OUT}/${slug}.png`, fullPage: false });
  console.log(
    JSON.stringify({
      route,
      status: res?.status() ?? null,
      title,
      heading: (h1 ?? "").trim().slice(0, 80),
      tbodyRows: rows,
      chipSample: chips.slice(0, 6).map((c) => c.trim()).filter(Boolean),
      hasEmptyState: /데이터가 없|비어 있|없습니다|등록된 .*없/.test(bodyText),
      excerpt: bodyText.slice(0, 220),
    }),
  );
}

console.log(JSON.stringify({ consoleErrorCount: consoleErrors.length, consoleErrors: consoleErrors.slice(0, 8) }));
await browser.close();
