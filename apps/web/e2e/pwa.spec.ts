// PWA 수용 기준 AC-1~AC-7 — 구현 **전에** 고정한다.
//
// 정본 = `docs/architecture/pwa.md` §5(무엇을·어떻게) · 기대 동작 = 같은 문서 §2.
// project = `chromium-pwa`(`playwright.config.ts`). AC-1~6 은 인증, AC-7 은 비인증(파일 안에서 비운다).
//
// ★측정기 함정 3개 (2026-10-02 실측) — 이 파일이 왜 이렇게 생겼는지:
//   ⑴ 기본 headless shell 은 `Page.getInstallabilityErrors` 에 **항상 `[]`** 를 돌려준다(구현이 없다).
//      그래서 project 가 `channel: "chromium"` 을 쓰고, AC-1 은 매니페스트 없는 페이지에서
//      오류가 나오는지부터 확인한다(자기검증). 이것을 빼면 AC-1 은 공허하게 초록이 된다.
//   ⑵ Playwright 의 일반 컨텍스트는 off-the-record 라 `in-incognito` 가 항상 붙는다 → AC-1 만
//      **영속 컨텍스트**로 띄운다. 이 오류를 필터로 지우지 않는다 — 그러면 `[]` 가 아니다.
//   ⑶ AC-5 「`/api/` 캐시 0건」은 SW 가 없어도 참이다(음성 대조). SW 제어 ∧ 제어 하의 `/api/` 응답
//      ∧ 열거기가 precache 를 보는지를 먼저 세워야 게이트가 된다(§5 변이 ⑴).
//
// ★「인증 실패」는 red 가 아니다 — `gotoApp` 이 `/sign-in` 으로 튕긴 것을 인프라 실패로 따로 적는다.

import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { type BrowserContext, type CDPSession, expect, type Page, test } from "@playwright/test";

import { BRAND_PALETTE } from "../src/lib/brand-palette";

const STORAGE_STATE = resolve(__dirname, ".auth/storageState.json");
const SW_WAIT_MS = 15_000;
const OFFLINE_HEADING = "오프라인 상태입니다";

// §2.1 — 전부 루트 경로(하위 폴더면 proxy 가 `/sign-in` 으로 보낸다).
const MANIFEST_ICONS = [
  { src: "/icon-192.png", sizes: "192x192", purpose: "any" },
  { src: "/icon-512.png", sizes: "512x512", purpose: "any" },
  { src: "/icon-maskable-512.png", sizes: "512x512", purpose: "maskable" },
] as const;
// `src/app/apple-icon.png` 은 Next 파일 규약으로 `/apple-icon.png` 에 서빙된다(`/icon.svg` 와 같은 규약).
const APPLE_ICON = "/apple-icon.png";

type Cookies = Parameters<BrowserContext["addCookies"]>[0];
type ShownNotification = { title: string; body: string; tag: string; data: unknown };

test.describe.configure({ timeout: 120_000 });

/** 인증 경로로 이동한다. `/sign-in` 으로 튕기면 AC 가 아니라 **인프라**(storageState) 실패다. */
async function gotoApp(page: Page, path: string): Promise<void> {
  await page.goto(path, { waitUntil: "load" });
  expect(
    new URL(page.url()).pathname,
    `[인프라] ${path} 가 ${page.url()} 로 갔다 — storageState 세션이 죽었다(AC 판정 아님)`,
  ).toBe(path);
}

/** `navigator.serviceWorker.ready` — 무한 대기 대신 시한 안에 못 오면 null(판정이 타임아웃으로 새지 않게). */
async function readyRegistration(
  page: Page,
): Promise<{ scope: string; scriptURL: string | null } | null> {
  return page.evaluate(async (ms) => {
    if (!("serviceWorker" in navigator)) return null;
    const timeout = new Promise<null>((done) => setTimeout(() => done(null), ms));
    const reg = await Promise.race([navigator.serviceWorker.ready, timeout]);
    return reg ? { scope: reg.scope, scriptURL: reg.active?.scriptURL ?? null } : null;
  }, SW_WAIT_MS);
}

/** CDP `ServiceWorker` 도메인에서 그 scope 의 registrationId 를 얻는다. */
async function registrationIdFor(cdp: CDPSession, scopeURL: string): Promise<string | null> {
  const found = new Promise<string>((done) => {
    cdp.on("ServiceWorker.workerRegistrationUpdated", ({ registrations }) => {
      const hit = registrations.find((r) => r.scopeURL === scopeURL && !r.isDeleted);
      if (hit) done(hit.registrationId);
    });
  });
  await cdp.send("ServiceWorker.enable");
  const timeout = new Promise<null>((done) => setTimeout(() => done(null), 5_000));
  return Promise.race([found, timeout]);
}

async function readNotifications(page: Page): Promise<ShownNotification[]> {
  return page.evaluate(async () => {
    const reg = await navigator.serviceWorker.getRegistration("/");
    if (!reg) return [];
    const shown = await reg.getNotifications();
    return shown.map((n) => ({
      title: n.title,
      body: n.body,
      tag: n.tag,
      data: n.data as unknown,
    }));
  });
}

test.describe("PWA AC — 인증", () => {
  test("AC-1 설치 가능 — Page.getInstallabilityErrors → []", async ({
    playwright,
    headless,
    baseURL,
  }, testInfo) => {
    // ⑵ 영속 컨텍스트 — 일반 컨텍스트는 `in-incognito` 가 항상 붙는다.
    const context = await playwright.chromium.launchPersistentContext(
      testInfo.outputPath("profile"),
      { channel: "chromium", headless, baseURL },
    );
    try {
      const state = JSON.parse(readFileSync(STORAGE_STATE, "utf8")) as { cookies: Cookies };
      await context.addCookies(state.cookies);
      const page = context.pages()[0] ?? (await context.newPage());
      const cdp = await context.newCDPSession(page);

      // ⑴ 자기검증 — 매니페스트 없는 페이지에서도 `[]` 면 이 브라우저는 검사를 구현하지 않는다.
      await page.goto("about:blank");
      const control = await cdp.send("Page.getInstallabilityErrors");
      expect(
        control.installabilityErrors.length,
        "[측정기] about:blank 에서 설치성 오류가 0건 — 이 브라우저는 설치성 검사를 안 한다(headless shell?)",
      ).toBeGreaterThan(0);

      await gotoApp(page, "/dashboard");
      const { installabilityErrors } = await cdp.send("Page.getInstallabilityErrors");
      expect(installabilityErrors, "설치성 오류(errorId 목록)").toEqual([]);
    } finally {
      await context.close();
    }
  });

  test("AC-2 manifest 정합 — 200·필수 필드·아이콘 200·링크 1개 ∧ use-credentials", async ({
    page,
  }) => {
    await gotoApp(page, "/dashboard");

    // §2.2 — 문서 안 `<link rel="manifest">` 는 정확히 1개, Cloudflare Access 대응 `use-credentials`.
    const links = page.locator('link[rel="manifest"]');
    await expect.soft(links, '<link rel="manifest"> 개수').toHaveCount(1);
    await expect.soft(links.first()).toHaveAttribute("href", "/manifest.webmanifest");
    await expect.soft(links.first()).toHaveAttribute("crossorigin", "use-credentials");

    const res = await page.request.get("/manifest.webmanifest", { maxRedirects: 0 });
    expect(res.status(), `GET /manifest.webmanifest → ${res.status()}`).toBe(200);
    const manifest = (await res.json()) as Record<string, unknown>;

    // §2.1 필드
    expect.soft(manifest).toMatchObject({
      name: "QuantBridge",
      short_name: "QuantBridge",
      id: "/",
      start_url: "/dashboard",
      scope: "/",
      display: "standalone",
      lang: "ko",
    });
    expect
      .soft(
        typeof manifest.description === "string" && manifest.description.length > 0,
        "description 비어 있음",
      )
      .toBe(true);
    const darkBg = BRAND_PALETTE.dark.bg.toLowerCase();
    expect.soft(String(manifest.background_color).toLowerCase(), "background_color").toBe(darkBg);
    expect.soft(String(manifest.theme_color).toLowerCase(), "theme_color").toBe(darkBg);

    const icons = Array.isArray(manifest.icons)
      ? (manifest.icons as Array<{ src?: string; sizes?: string; purpose?: string }>)
      : [];
    for (const want of MANIFEST_ICONS) {
      const hit = icons.find((icon) => icon.src === want.src);
      expect.soft(hit, `manifest icons 에 ${want.src} 없음`).toBeDefined();
      expect.soft(hit?.sizes, `${want.src} sizes`).toBe(want.sizes);
      // purpose 생략 = "any"(manifest 기본값).
      const purposes = (hit?.purpose ?? "any").split(/\s+/);
      expect.soft(purposes, `${want.src} purpose`).toContain(want.purpose);
    }

    // 아이콘 전부 200 · 리다이렉트 0 — manifest 의 모든 아이콘 + 문서의 apple-touch-icon.
    const appleHrefs = await page
      .locator('link[rel="apple-touch-icon"]')
      .evaluateAll((els) => els.map((el) => el.getAttribute("href") ?? ""));
    expect
      .soft(appleHrefs.length, '<link rel="apple-touch-icon"> 없음(§2.1 apple-icon 180)')
      .toBeGreaterThan(0);
    const iconUrls = [...icons.map((icon) => icon.src ?? ""), ...appleHrefs];
    for (const url of iconUrls) {
      expect.soft(url, `아이콘 ${url} 은 루트 경로여야 한다`).toMatch(/^\/[^/]+$/);
      const iconRes = await page.request.get(url, { maxRedirects: 0 });
      expect
        .soft(
          iconRes.status(),
          `GET ${url} → ${iconRes.status()} location=${iconRes.headers().location ?? "-"}`,
        )
        .toBe(200);
      expect
        .soft(iconRes.headers()["content-type"] ?? "", `${url} content-type`)
        .toContain("image/png");
    }
  });

  test("AC-3 SW 등록·헤더 — ready scope '/' · /sw.js Cache-Control no-store", async ({ page }) => {
    await gotoApp(page, "/dashboard");
    const origin = new URL(page.url()).origin;

    const reg = await readyRegistration(page);
    expect
      .soft(
        reg?.scope,
        `navigator.serviceWorker.ready 가 ${SW_WAIT_MS}ms 안에 안 왔다/scope 불일치`,
      )
      .toBe(`${origin}/`);
    expect.soft(reg?.scriptURL, "등록된 SW 스크립트").toBe(`${origin}/sw.js`);

    // §2.5
    const res = await page.request.get("/sw.js", { maxRedirects: 0 });
    expect(res.status(), `GET /sw.js → ${res.status()}`).toBe(200);
    expect.soft(res.headers()["cache-control"] ?? "", "/sw.js Cache-Control").toContain("no-store");
    expect
      .soft(res.headers()["content-type"] ?? "", "/sw.js Content-Type")
      .toContain("application/javascript");
  });

  test("AC-4 오프라인 안내 — SW 활성 후 오프라인 /dashboard → 「오프라인 상태입니다」", async ({
    page,
    context,
  }) => {
    await gotoApp(page, "/dashboard");
    const reg = await readyRegistration(page);
    expect(
      reg,
      `SW 가 ${SW_WAIT_MS}ms 안에 활성화되지 않았다 — 오프라인 안내를 낼 주체가 없다`,
    ).not.toBeNull();

    await context.setOffline(true);
    const navError = await page.goto("/dashboard").then(
      () => null,
      (error: Error) => error.message.split("\n")[0] ?? error.message,
    );
    expect(navError, "오프라인 내비게이션이 SW 응답 없이 네트워크 오류로 끝났다").toBeNull();
    await expect(page.getByRole("heading", { name: OFFLINE_HEADING, exact: true })).toBeVisible();
  });

  test("AC-5 API 무캐시 — caches 전수에서 /api/ URL 0건", async ({ page }) => {
    await gotoApp(page, "/dashboard");
    const reg = await readyRegistration(page);
    expect(
      reg,
      `SW 가 ${SW_WAIT_MS}ms 안에 활성화되지 않았다 — 무캐시 판정이 공허해진다`,
    ).not.toBeNull();

    // ⑶ 전제 — SW 제어 하에서 `/api/` 응답이 실제로 오가야 「캐시하지 않았다」가 의미를 갖는다.
    const apiResponses: string[] = [];
    page.on("response", (r) => {
      if (r.url().includes("/api/")) apiResponses.push(r.url());
    });
    await page.reload({ waitUntil: "load" });
    const controller = await page.evaluate(
      () => navigator.serviceWorker.controller?.scriptURL ?? null,
    );
    expect(controller, "리로드 뒤에도 페이지가 SW 제어를 받지 않는다").not.toBeNull();
    await expect
      .poll(() => apiResponses.length, {
        timeout: 30_000,
        message: "SW 제어 하에서 /api/ 응답이 0건 — 캐시될 기회 자체가 없었다(공허)",
      })
      .toBeGreaterThan(0);
    await page.waitForTimeout(1_500); // 비동기 cache.put 이 끝날 여유

    const cached = await page.evaluate(async () => {
      const urls: string[] = [];
      for (const name of await caches.keys()) {
        const cache = await caches.open(name);
        for (const request of await cache.keys()) urls.push(`${name} ${request.url}`);
      }
      return urls;
    });
    expect(
      cached.length,
      "[측정기] caches 전수가 0건 — §2.3 precache(/offline·아이콘)도 안 보이면 열거가 장님이다",
    ).toBeGreaterThan(0);
    expect(
      cached.filter((entry) => entry.includes("/api/")),
      "캐시에 들어간 /api/ URL",
    ).toEqual([]);
  });

  test("AC-6 푸시 표시 — deliverPushMessage → getNotifications 의 title·data.url", async ({
    page,
    context,
  }) => {
    await gotoApp(page, "/dashboard");
    const origin = new URL(page.url()).origin;
    await context.grantPermissions(["notifications"], { origin });

    const reg = await readyRegistration(page);
    expect(
      reg,
      `SW 가 ${SW_WAIT_MS}ms 안에 활성화되지 않았다 — 푸시를 받을 주체가 없다`,
    ).not.toBeNull();

    const cdp = await context.newCDPSession(page);
    const registrationId = await registrationIdFor(cdp, `${origin}/`);
    expect(registrationId, "CDP 에 scope '/' 등록이 없다").not.toBeNull();

    // §4.3 페이로드
    const payload = {
      title: "백테스트 완료",
      body: "EMA Crossover",
      url: "/backtests/pwa-ac6",
      tag: "backtest:pwa-ac6",
    };
    // ★최대 3회 전달한다 (2026-10-02 실측). headless Chromium 은 `showNotification` 이 resolve 된
    //   **직후** SW 자신의 `getNotifications()` 도 0 을 내는 경우가 있다 — 30회×6워커 스트레스에서
    //   1~5건(SW 계측: "push received" → "shown; now=0", 3초 내내 0). 플랫폼이 표시분을 떨어뜨린
    //   것이지 SW 결함이 아니다. 재전달은 같은 `tag` 라 화면에서 하나로 합쳐지고, push 처리기가
    //   없거나 제목·data 가 틀린 SW 는 몇 번을 보내도 red 다(판정 대상은 그대로).
    let shown: ShownNotification | undefined;
    for (let attempt = 1; attempt <= 3 && !shown; attempt += 1) {
      await cdp.send("ServiceWorker.deliverPushMessage", {
        origin,
        registrationId: registrationId ?? "",
        data: JSON.stringify(payload),
      });
      const deadline = Date.now() + 3_000;
      while (!shown && Date.now() < deadline) {
        shown = (await readNotifications(page)).find((n) => n.title === payload.title);
        if (!shown) await page.waitForTimeout(100);
      }
    }
    expect(shown, "push 이벤트를 3번 전달해도 제목이 일치하는 알림이 없다").toBeDefined();
    expect(shown?.data, "notification.data.url").toMatchObject({ url: payload.url });
    expect.soft(shown?.body, "notification.body").toBe(payload.body);
    expect.soft(shown?.tag, "notification.tag(§3.5 같은 tag 는 하나로 합쳐진다)").toBe(payload.tag);
  });
});

test.describe("PWA AC — 비인증", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test("AC-7 비인증 경로 — manifest·/sw.js·/offline·아이콘이 /sign-in 으로 안 간다", async ({
    page,
  }) => {
    // 자기검증 — 이 컨텍스트가 정말 비인증이고 게이트가 살아 있어야 「안 간다」가 의미를 갖는다.
    const gate = await page.request.get("/dashboard", { maxRedirects: 0, timeout: 60_000 });
    expect(
      gate.status(),
      "[측정기] 비인증 /dashboard 가 리다이렉트되지 않았다",
    ).toBeGreaterThanOrEqual(300);
    expect(gate.headers().location ?? "", "[측정기] 비인증 /dashboard 리다이렉트 목적지").toContain(
      "/sign-in",
    );

    const paths = [
      "/manifest.webmanifest",
      "/sw.js",
      "/offline",
      ...MANIFEST_ICONS.map((icon) => icon.src),
      APPLE_ICON,
    ];
    for (const path of paths) {
      const res = await page.request.get(path, { maxRedirects: 0, timeout: 60_000 });
      expect
        .soft(
          res.status(),
          `GET ${path} → ${res.status()} location=${res.headers().location ?? "-"}`,
        )
        .toBe(200);
    }
  });
});
