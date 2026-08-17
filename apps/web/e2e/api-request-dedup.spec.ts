// [BL-786] 같은 화면의 같은 API 요청이 **한 번만** 나가는지 재는 게이트.
//
// ★이 결함이 넉 달간 안 보인 이유는 「요청이 두 번 나간다」를 재는 검사면이 하나도 없었기
//   때문이다. 화면은 안 깨지고 데이터도 맞다 — 값만 두 배로 나간다. 그래서 여기서 센다.
//
// ★단언은 **정확히 1회**여야 한다. 「최소 1회」(`>= 1`)로 느슨하게 쓰면 중복이 있어도 초록이라
//   이 파일은 아무것도 막지 못한다.
// ★동시에 **0회로 통과하면 안 된다**. 요청을 한 건도 관측하지 못한 실행(로그인 실패·화면
//   미렌더)은 「중복 없음」이 아니라 「측정 실패」다 — `REQUIRED` 앵커가 그것을 가른다.
import { expect, test } from "@playwright/test";

const API_MARKER = "/api/v1/";

/**
 * 측정 창은 `networkidle`(500ms 무통신) + 여유 1초까지다.
 * 이 화면들의 가장 빠른 폴링이 5초(`ORDERS_REFETCH_INTERVAL_ACTIVE_MS`)라, 정상 폴링이
 * 창 안에 들어와 「중복」으로 오판되지 않는다.
 */
const SETTLE_MS = 1_000;

interface RouteCase {
  path: string;
  /** 이 실행이 실제로 화면을 그렸다는 증거. 하나라도 없으면 측정 실패로 red. */
  required: readonly string[];
}

const ROUTES: readonly RouteCase[] = [
  {
    path: "/backtests",
    required: [
      // 내비 배지 프로브 — [BL-786] 이 「전부 쌍」이라고 적은 그 요청들.
      "/api/v1/backtests?limit=1&offset=0",
      "/api/v1/orders?state=pending&state=submitted&limit=1&offset=0",
      // 목록 화면이 전략 이름 맵을 채우는 요청.
      "/api/v1/strategies?limit=100&offset=0",
    ],
  },
  {
    path: "/dashboard",
    required: ["/api/v1/backtests?limit=8&offset=0", "/api/v1/exchange-accounts"],
  },
];

for (const route of ROUTES) {
  test(`${route.path} — 같은 API 요청이 두 번 나가지 않는다`, async ({ page }) => {
    test.setTimeout(120_000);

    const counts = new Map<string, number>();
    let capturing = true;
    page.on("request", (req) => {
      if (!capturing) return;
      const url = req.url();
      if (!url.includes(API_MARKER)) return;
      const key = `${req.method()} ${url}`;
      counts.set(key, (counts.get(key) ?? 0) + 1);
    });

    await page.goto(route.path, { timeout: 60_000 });
    await page.waitForLoadState("networkidle", { timeout: 60_000 });
    await page.waitForTimeout(SETTLE_MS);
    capturing = false;

    const observed = [...counts.entries()].sort(([a], [b]) => a.localeCompare(b));
    const inventory = observed.map(([key, n]) => `${n}x ${key}`).join("\n");

    // ⑴ 측정이 실제로 일어났다 — 앵커 요청이 정확히 1회씩.
    for (const needle of route.required) {
      const hits = observed.filter(([key]) => key.includes(needle));
      expect(
        hits.map(([key, n]) => `${n}x ${key}`),
        `${route.path}: 앵커 요청 \`${needle}\` 을 관측하지 못했다 — 중복이 없는 것이 아니라 측정이 실패한 것이다.\n관측 전체:\n${inventory}`,
      ).toHaveLength(1);
      expect(
        hits[0]?.[1],
        `${route.path}: 앵커 요청 \`${needle}\` 이 ${hits[0]?.[1]}회 나갔다 (기대 1회).\n관측 전체:\n${inventory}`,
      ).toBe(1);
    }

    // ⑵ 어떤 요청도 두 번 나가지 않았다.
    const duplicated = observed.filter(([, n]) => n > 1).map(([key, n]) => `${n}x ${key}`);
    expect(
      duplicated,
      `${route.path}: 같은 URL 이 한 화면에서 두 번 이상 나갔다 ([BL-786]).\n관측 전체:\n${inventory}`,
    ).toEqual([]);
  });
}
