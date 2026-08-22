// 잔여 authed 라우트(P1 밖)의 디자인 캐논 게이트 — 이식 seam #1 확장 (로컬 전용)
//
// `authed-canon-p1.spec.ts` 와 같은 감사 코어(`design-canon-audit.ts`)를 소비한다. P1 4라우트가
// baseline 이었다면, 이 파일은 이식으로 새로 그린 잔여 authed 라우트를 하나씩 편입한다.
// W2 = `/backtests/[id]` 리포트 상세. 이후 W3 워커가 자기 라우트를 이 allowlist 에 추가한다.
//
// ★/backtests/[id] 는 id 가 환경마다 다르므로 목록에서 **완료 상태 행만** 런타임 발견한다.
// 완료 대상이 없으면 test.skip 이 아니라 expect 로 FAIL 시킨다 (조용한 통과 방지 — coverage 단조성).
// 리포트 셸 핵심 요소(backtest-report-shell)가 렌더된 뒤에 4폭 감사를 돌린다.
//
// ★왜 `authed-canon-*` 이름인가. 대상이 전부 로그인 뒤 화면이라 CI(무인증)에서 못 돈다.
// 파일명을 `design-canon-*` 로 하면 `chromium-design-canon`(CI) 이 매치해 sign-in 리다이렉트로
// 실패한다. 그래서 `authed-canon-remaining` 으로 두고 `chromium-authed`(storageState + setup
// 의존, 로컬 `pnpm e2e:authed` 전용)에 배선한다. config testMatch 열거에도 추가해야 발견된다.

import { existsSync } from "node:fs";
import { resolve } from "node:path";

import { expect, test } from "@playwright/test";

import { getBaseURL } from "./_base-url";
import { assertAuthedReachability } from "./authed-reachability-assert";
import { auditUrl, formatCanonResult, hardFailCount } from "./design-canon-audit";

const BASE_URL = getBaseURL();
const STORAGE_STATE = resolve(__dirname, ".auth/storageState.json");

// 백엔드 부재/개발키 콘솔 소음은 캐논 위반이 아니다 (authed-canon-p1 과 동일 필터).
const EXPECTED_CONSOLE = [
  /failed to fetch/i,
  /networkerror/i,
  /failed to load resource.*\b40[13]\b/i,
  // 리소스 로드 429(레이트리밋)만 무시한다 — 연속 4폭 감사가 백엔드를 치면 나는 스위트 환경
  // 아티팩트다. 이 필터는 pageerror 에도 적용되므로(design-canon-audit.ts), 렌더 예외 속 429 를
  // 삼키지 않도록 "Failed to load resource … 429" 콘솔 메시지에만 좁힌다.
  /failed to load resource.*429/i,
  // ★★**그 밖의 5xx 는 더 이상 무시하지 않는다** ([BL-807], 2026-08-18). 종전의 맨 `/\b50[0-9]\b/` 는
  //   ⑴ 앵커가 없어 **본문의 아무 세 자리 50x 숫자**까지 삼켰고 ⑵ 바로 위 4xx 필터가
  //   `failed to load resource.*` 로 좁혀져 있는 것과 **비대칭**이었으며 ⑶ 무엇보다 BE 500 은
  //   「백엔드 부재 소음」이 아니라 **앱 결함**이다. 부재는 위의 `failed to fetch`·`networkerror`
  //   가 이미 덮는다. 이 필터 때문에 「행은 DB 에 있는데 화면이 빈다」가 세 케이스에서
  //   **원인이 안 보인 채** 반복됐다 — 실제 원인은 상세 API 의 500 이었다.
  /development keys/i,
  /\[fast refresh\]/i,
  /access to fetch/i,
];
/**
 * 거래소 **포지션 조회의 503 만** 좁게 면제한다 (2026-08-19 CI 실측, [BL-807]).
 *
 * CI 러너에는 실제 거래소 연결이 없어 `GET /api/v1/exchange-accounts/{id}/positions` 가 CCXT
 * 실패로 503 을 낸다 — BE 의 **정직한 동작**이고 앱 결함이 아니다. 하드 실패로 세면 `/trading`
 * 캐논은 거래소 없이 영영 CI 에서 못 돈다.
 *
 * ★★**첫 판은 발화조차 못 했다.** 콘솔 원문 하나만 보는 정규식에 URL 조각을 적어 넣었는데,
 *   `ignoreConsole` 이 받는 것은 **브라우저 원문**이고 리포트의 `<- <url>` 은 그 뒤에 붙는다.
 *   내 국소 검사는 리포트 문자열을 먹여 true 였다 — **실제 경로가 지나지 않는 검사**였다.
 *   ⇒ 출처 URL 을 **둘째 인자로** 받아 판정한다. 텍스트의 503 과 URL 의 엔드포인트가
 *   **둘 다** 맞을 때만 면제되므로 사거리가 원문 밖으로 새지 않는다.
 */
const EXCHANGE_POSITIONS_PATH = /\/exchange-accounts\/[^/]+\/positions(?:\?|$)/;
const isExchangePositions503 = (text: string, originUrl?: string) =>
  /\b503\b/.test(text) && originUrl !== undefined && EXCHANGE_POSITIONS_PATH.test(originUrl);

const ignoreConsole = (t: string, originUrl?: string) =>
  EXPECTED_CONSOLE.some((re) => re.test(t)) || isExchangePositions503(t, originUrl);

/**
 * 잔여 authed 라우트 하드 실패 allowlist. 신규 화면은 0 으로 진입한다.
 *   - /backtests/:id 0 — W2 C 이식 완료. variant-c 번호 섹션 IA 단일 스크롤.
 */
const HARDFAIL_ALLOWLIST: Readonly<Record<string, number>> = {
  "/backtests/:id": 0,
  "/backtests/new": 0,
  "/strategies": 0,
  "/strategies/new": 0,
  "/strategies/:id/edit": 0,
  "/optimizer": 0,
  "/optimizer/:id": 0,
  "/orders": 0,
  "/onboarding": 0,
};

// 정적 라우트 — 워커 슬라이스가 늘어날 때마다 오케스트레이터가 union 으로 추가한다.
// W3-A: /backtests/new. W3-D: /orders. W3-E: /onboarding.
const STATIC_ROUTES = [
  "/strategies",
  "/strategies/new",
  "/optimizer",
  "/backtests/new",
  "/orders",
  "/onboarding",
] as const;

const auditOptions = {
  contextOptions: { storageState: STORAGE_STATE },
  ignoreConsole,
} as const;

const DETAIL_HREF_RE = /^\/backtests\/[0-9a-f-]{36}$/;

test.describe("잔여 authed 라우트 디자인 캐논 (이식 seam #1 확장, 로컬 전용)", () => {
  // storageState 부재 시 조용한 skip 이 아니라 시끄럽게 실패시킨다(운영계약 §3ⓒ — skip 침묵 통과 방지).
  test("사전조건 — storageState 존재", () => {
    expect(
      existsSync(STORAGE_STATE),
      `storageState 없음 (${STORAGE_STATE}) — chromium-authed-setup 프로젝트를 먼저 실행하라 (pnpm e2e:authed).`,
    ).toBe(true);
  });

  test("위생 — 커버할 잔여 라우트 배열이 비어있지 않다", () => {
    const routes = Object.keys(HARDFAIL_ALLOWLIST);
    expect(
      routes.length,
      "HARDFAIL_ALLOWLIST 가 비었다 — 이 spec 은 아무 라우트도 감사하지 않고 조용히 통과 중이다",
    ).toBeGreaterThan(0);
  });

  for (const path of STATIC_ROUTES) {
    test(`${path} — 하드 실패 ≤ allowlist`, async ({ browser }) => {
      test.setTimeout(180_000);
      const res = await auditUrl(browser, `${BASE_URL}${path}`, { label: path, ...auditOptions });
      process.stdout.write(`${formatCanonResult(res)}\n`);
      assertAuthedReachability(res);
      expect(
        hardFailCount(res),
        `${path} 하드 실패:\n${formatCanonResult(res)}`,
      ).toBeLessThanOrEqual(HARDFAIL_ALLOWLIST[path] ?? 0);
    });
  }

  test("/strategies/:id/edit — 하드 실패 ≤ allowlist", async ({ browser }) => {
    test.setTimeout(180_000);

    // 편집 라우트 id 는 환경마다 다르다. /strategies 목록에서 실존 전략 편집 링크를 런타임 발견.
    const discovery = await browser.newContext({ storageState: STORAGE_STATE });
    const dpage = await discovery.newPage();
    await dpage.goto(`${BASE_URL}/strategies`, { waitUntil: "load" });
    // ★고정 1.5초였다 ([BL-807]). 이 파일이 CI 로 올라가면 그 대기는 러너 속도에 걸린다 —
    //   부재 판정은 아래 `expect(editHref).toBeTruthy()` 가 진다.
    // ★★기다릴 것은 **편집 링크**다 (codex 적대 리뷰 P2, 2026-08-19). 초판은 `a[href*="/strategies/"]`
    //   를 기다렸는데 그것은 목록에 **항상 있는** `/strategies/new` 에 즉시 매치한다 — 목록 API 가
    //   아직 로딩 중이어도 대기가 그 자리에서 끝나고, 아래 UUID `/edit` 탐색은 빈손으로 돌아온다.
    //   고정 대기를 걷어낸 그 회차가 **같은 결함을 다른 모양으로** 다시 만든 셈이었다.
    await dpage.waitForSelector('a[href$="/edit"]', { timeout: 25_000 }).catch(() => {});
    const editHref = await dpage.locator('a[href*="/strategies/"]').evaluateAll((els) => {
      const re = /^\/strategies\/[0-9a-f-]{36}\/edit$/;
      const found = (els as HTMLAnchorElement[]).find((a) => re.test(new URL(a.href).pathname));
      return found ? new URL(found.href).pathname : null;
    });
    await discovery.close();

    // 부재 시 skip 이 아니라 실패 — 편집 라우트 커버리지 공백을 드러낸다(운영 계약 §3 ⓒ).
    expect(
      editHref,
      "목록에서 실존 전략 편집 링크를 찾지 못했습니다 (데이터 시딩 필요)",
    ).toBeTruthy();

    const res = await auditUrl(browser, `${BASE_URL}${editHref}`, {
      label: editHref ?? "/strategies/:id/edit",
      ...auditOptions,
    });
    process.stdout.write(`${formatCanonResult(res)}\n`);
    assertAuthedReachability(res);
    expect(
      hardFailCount(res),
      `${editHref} 하드 실패:\n${formatCanonResult(res)}`,
    ).toBeLessThanOrEqual(HARDFAIL_ALLOWLIST["/strategies/:id/edit"] ?? 0);
  });

  test("/optimizer/:id — 하드 실패 ≤ allowlist (완료 run 상세)", async ({ browser }) => {
    test.setTimeout(180_000);

    // optimizer run id 를 하드코딩하지 않는다 (환경마다 다르다). /optimizer 에서 완료 run 링크 발견.
    const discovery = await browser.newContext({ storageState: STORAGE_STATE });
    const dpage = await discovery.newPage();
    await dpage.goto(`${BASE_URL}/optimizer`, { waitUntil: "load" });
    // ★고정 1.5초였다 ([BL-807]). 같은 파일의 `/backtests` 발견은 이미 25초 `waitForSelector` 를
    //   쓰는데 여기만 안 썼다 — 부재 판정은 아래 `expect(optHref).toBeTruthy()` 가 진다.
    await dpage.waitForSelector('a[href^="/optimizer/"]', { timeout: 25_000 }).catch(() => {});
    const optHref = await dpage
      .locator('tr[data-status="completed"] a[href^="/optimizer/"], a[href^="/optimizer/"]')
      .evaluateAll((els) => {
        const re = /^\/optimizer\/[0-9a-f-]{36}$/;
        const found = (els as HTMLAnchorElement[]).find((a) => re.test(new URL(a.href).pathname));
        return found ? new URL(found.href).pathname : null;
      });
    await discovery.close();

    // ★부재 시 skip 이 아니라 실패 — 완료 optimizer run 시딩(fixture 47ab18b7...)을 강제한다.
    expect(optHref, "완료 optimizer run 상세 링크를 찾지 못했다 — 완료 run 시딩 필요").toBeTruthy();

    const res = await auditUrl(browser, `${BASE_URL}${optHref}`, {
      label: `${optHref}`,
      ...auditOptions,
    });
    process.stdout.write(`${formatCanonResult(res)}\n`);
    assertAuthedReachability(res);
    expect(
      hardFailCount(res),
      `/optimizer/:id 하드 실패:\n${formatCanonResult(res)}`,
    ).toBeLessThanOrEqual(HARDFAIL_ALLOWLIST["/optimizer/:id"] ?? 0);
  });

  test("/backtests/:id — 완료 백테스트 리포트 상세 하드 실패 ≤ allowlist", async ({ browser }) => {
    test.setTimeout(180_000);

    // 목록에서 상태 칩이 "완료"(data-status="completed") 인 행의 상세 링크를 런타임 발견한다.
    const discovery = await browser.newContext({ storageState: STORAGE_STATE });
    const dpage = await discovery.newPage();
    await dpage.goto(`${BASE_URL}/backtests`, { waitUntil: "load" });
    // 목록 행이 client fetch 로 렌더될 때까지 기다린 뒤 완료 행을 찾는다 (dev 콜드 로드 대비).
    await dpage
      .waitForSelector('[data-testid^="backtest-row-"]', { timeout: 25_000 })
      .catch(() => {});
    const href = await dpage
      .locator('tr[data-status="completed"] a[href^="/backtests/"]')
      .evaluateAll((els) => {
        const found = (els as HTMLAnchorElement[]).find((a) =>
          /^\/backtests\/[0-9a-f-]{36}$/.test(new URL(a.href).pathname),
        );
        return found ? new URL(found.href).pathname : null;
      })
      .catch(() => null);
    await discovery.close();

    // 완료 대상 부재 시 skip 이 아니라 FAIL — 백엔드 8000 에 완료 백테스트가 있어야 한다.
    expect(
      href && DETAIL_HREF_RE.test(href),
      "완료 상태 백테스트를 목록에서 찾지 못했다 (백엔드 8000 에 완료 백테스트 시딩 필요)",
    ).toBe(true);

    const res = await auditUrl(browser, `${BASE_URL}${href}`, {
      label: "/backtests/:id",
      ...auditOptions,
      // 리포트 셸 핵심 요소가 렌더된 뒤에 감사한다 (데이터 로딩 완료 대기).
      prepare: async (page) => {
        await page.waitForSelector('[data-testid="backtest-report-shell"]', {
          timeout: 20_000,
        });
      },
    });
    process.stdout.write(`${formatCanonResult(res)}\n`);
    assertAuthedReachability(res);
    expect(
      hardFailCount(res),
      `/backtests/:id 하드 실패:\n${formatCanonResult(res)}`,
    ).toBeLessThanOrEqual(HARDFAIL_ALLOWLIST["/backtests/:id"] ?? 0);
  });

  // perf-surface: 목록 성과 표면의 구조 불변식(캐논 screen-03 11열 + 서버 정렬 aria-sort).
  // 캐논 hex/em-dash 감사는 source ratchet + /backtests/:id 가 이미 커버하므로 여기선 구조만 본다.
  test("/backtests — 성과 목록 11열 + 서버 정렬(aria-sort + order_by URL)", async ({ browser }) => {
    test.setTimeout(180_000);
    const ctx = await browser.newContext({ storageState: STORAGE_STATE });
    const page = await ctx.newPage();
    await page.goto(`${BASE_URL}/backtests`, { waitUntil: "load" });
    await page.waitForSelector('[data-testid^="backtest-row-"]', { timeout: 25_000 });

    const headerCount = await page.locator("table.runs-table thead th").count();
    expect(headerCount, "백테스트 목록은 캐논 11열이어야 한다").toBe(11);

    // 수익률 헤더 클릭 → 서버 정렬(URL order_by) + 활성 헤더 단일 aria-sort.
    await page
      .locator("table.runs-table thead th", { hasText: "수익률" })
      .locator("button")
      .click();
    await page.waitForTimeout(1500);
    expect(page.url(), "수익률 정렬은 order_by=total_return 을 URL 에 반영해야 한다").toMatch(
      /order_by=total_return/,
    );
    const activeSort = await page.locator("table.runs-table thead th[aria-sort]").count();
    expect(activeSort, "정렬 활성 헤더는 정확히 1개(aria-sort)여야 한다").toBe(1);

    await ctx.close();
  });
});
