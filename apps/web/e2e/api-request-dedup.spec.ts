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
  /**
   * SSR 이 prefetch 해 hydrate 로 넘긴 요청 — 브라우저에서는 **0회**여야 한다.
   * 페이지의 prefetch queryKey 와 컴포넌트의 queryKey 가 어긋나면 여기가 1회가 되고,
   * 그러면 같은 목록을 SSR 에서 한 번 · 브라우저에서 한 번, 한 화면 로드에 두 번 치는 것이다.
   */
  hydrated?: readonly string[];
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
    hydrated: ["/api/v1/backtests?limit=20&offset=0&order_by=created_at&order=desc"],
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
    const failedResponses: string[] = [];
    let capturing = true;
    page.on("request", (req) => {
      if (!capturing) return;
      const url = req.url();
      if (!url.includes(API_MARKER)) return;
      const key = `${req.method()} ${url}`;
      counts.set(key, (counts.get(key) ?? 0) + 1);
    });
    // ★실패 응답을 따로 모은다 — 재시도를 중복으로 오판하지 않기 위해서다.
    //   `QueryProvider` 의 기본값은 `retry: 1` 이고 TanStack 의 기본 첫 재시도 지연은 1초라
    //   (`networkidle` + SETTLE_MS 창 안이다) 429·5xx 한 건이 같은 URL 을 2회로 만든다.
    //   그것을 「중복」이라고 말하면 이 게이트가 **가짜 red** 를 내는 장치가 된다.
    page.on("response", (res) => {
      if (!capturing) return;
      const url = res.url();
      if (!url.includes(API_MARKER)) return;
      if (res.status() >= 400)
        failedResponses.push(`${res.status()} ${res.request().method()} ${url}`);
    });

    await page.goto(route.path, { timeout: 60_000 });
    await page.waitForLoadState("networkidle", { timeout: 60_000 });
    await page.waitForTimeout(SETTLE_MS);
    capturing = false;

    const observed = [...counts.entries()].sort(([a], [b]) => a.localeCompare(b));
    const inventory = observed.map(([key, n]) => `${n}x ${key}`).join("\n");

    // ⑴′ 측정 창에 실패 응답이 없었다.
    // ★이것은 중복 판정보다 **먼저** 온다. 실패가 있으면 재시도가 섞여 아래 카운트가
    //   의미를 잃으므로, 「중복이 있다」가 아니라 「측정이 오염됐다」로 red 를 내야 한다.
    //   red 인 것은 같지만 **사유가 다르고**, 사람이 다음에 할 일이 다르다.
    expect(
      failedResponses,
      `${route.path}: 측정 창 안에서 API 가 실패 응답을 냈다 — React Query 재시도가 섞여 중복 카운트를 신뢰할 수 없다. 이것은 [BL-786] 중복이 아니라 **측정 오염**이다.\n실패 응답:\n${failedResponses.join("\n")}\n관측 전체:\n${inventory}`,
    ).toEqual([]);

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

    // ⑵ SSR 이 이미 준 것은 브라우저가 다시 가져가지 않았다.
    for (const needle of route.hydrated ?? []) {
      const hits = observed.filter(([key]) => key.includes(needle));
      expect(
        hits.map(([key, n]) => `${n}x ${key}`),
        `${route.path}: \`${needle}\` 은 SSR prefetch 가 hydrate 로 넘긴 요청이라 브라우저에서 0회여야 한다. 나갔다면 페이지의 prefetch queryKey 와 컴포넌트의 queryKey 가 어긋난 것이다 ([BL-786]).\n관측 전체:\n${inventory}`,
      ).toEqual([]);
    }

    // ⑶ 어떤 요청도 두 번 나가지 않았다.
    const duplicated = observed.filter(([, n]) => n > 1).map(([key, n]) => `${n}x ${key}`);
    expect(
      duplicated,
      `${route.path}: 같은 URL 이 한 화면에서 두 번 이상 나갔다 ([BL-786]).\n관측 전체:\n${inventory}`,
    ).toEqual([]);
  });
}
