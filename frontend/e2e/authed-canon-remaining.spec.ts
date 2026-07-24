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
// ★왜 `authed-canon-*` 이름인가. 대상이 전부 Clerk authed 라 CI(무인증)에서 못 돈다.
// 파일명을 `design-canon-*` 로 하면 `chromium-design-canon`(CI) 이 매치해 sign-in 리다이렉트로
// 실패한다. 그래서 `authed-canon-remaining` 으로 두고 `chromium-authed`(storageState + setup
// 의존, 로컬 `pnpm e2e:authed` 전용)에 배선한다. config testMatch 열거에도 추가해야 발견된다.

import { existsSync } from "node:fs";
import { resolve } from "node:path";

import { expect, test } from "@playwright/test";

import { auditUrl, formatCanonResult, hardFailCount } from "./design-canon-audit";

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000";
const STORAGE_STATE = resolve(__dirname, ".auth/storageState.json");

// 백엔드 부재/개발키 콘솔 소음은 캐논 위반이 아니다 (authed-canon-p1 과 동일 필터).
const EXPECTED_CONSOLE = [
  /failed to fetch/i,
  /networkerror/i,
  /net::err_/i,
  /failed to load resource.*\b40[13]\b/i,
  // 리소스 로드 429(레이트리밋)만 무시한다 — 연속 4폭 감사가 백엔드를 치면 나는 스위트 환경
  // 아티팩트다. 이 필터는 pageerror 에도 적용되므로(design-canon-audit.ts), 렌더 예외 속 429 를
  // 삼키지 않도록 "Failed to load resource … 429" 콘솔 메시지에만 좁힌다.
  /failed to load resource.*429/i,
  /\b50[0-9]\b/,
  /clerk has been loaded/i,
  /development keys/i,
  /\[fast refresh\]/i,
  /access to fetch/i,
];
const ignoreConsole = (t: string) => EXPECTED_CONSOLE.some((re) => re.test(t));

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
      process.stdout.write(formatCanonResult(res) + "\n");
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
    await dpage.waitForTimeout(1500);
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
    process.stdout.write(formatCanonResult(res) + "\n");
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
    await dpage.waitForTimeout(1500);
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
    process.stdout.write(formatCanonResult(res) + "\n");
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
    process.stdout.write(formatCanonResult(res) + "\n");
    expect(
      hardFailCount(res),
      `/backtests/:id 하드 실패:\n${formatCanonResult(res)}`,
    ).toBeLessThanOrEqual(HARDFAIL_ALLOWLIST["/backtests/:id"] ?? 0);
  });
});
