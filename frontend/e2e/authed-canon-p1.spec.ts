// P1 4라우트의 디자인 캐논 baseline 측정 + 래칫 (이식 seam #1, 로컬 전용)
//
// `design-canon-audit.ts` 를 React 앱에 조준한다. 캘리브레이션(`design-canon-calibration`)이
// 같은 코어를 프로토타입 17벌에서 17/17 재현했으므로, 여기서 잡히는 것은 감사 코어의 흠이
// 아니라 앱의 현재 상태다.
//
// ★왜 `chromium-authed` 인가 (그리고 왜 이름이 design-canon-* 이 아닌가).
// P1 4라우트는 전부 Clerk authed 라 CI 에서 못 돈다. 파일명을 `design-canon-*` 로 하면
// `chromium-design-canon`(CI·무인증) 프로젝트가 매치해 sign-in 리다이렉트로 실패한다.
// 그래서 `authed-canon-p1` 로 두고 `chromium-authed`(storageState + setup 의존, 로컬
// `pnpm e2e:authed` 전용)에 배선한다.
//
// baseline 은 이식 전(pre-C) UI 의 상태다. S5~S8 이 라우트를 하나씩 다시 그리며 아래
// allowlist 를 줄인다. canon 은 하드 실패가 아니라 지표다 (audit 코어 주석 참조).
//
// ★측정 조건 (2026-07-20). 백엔드 8000(DB 5436) 기동 + 데이터 있음:
//   /backtests 6건(완료 3·실패 3) · /backtests/{id}/trades 최대 585 체결 · /trading 거래소 1.
//   /dashboard 는 활성 세션 0(라이브 세션 데이터 없음)이라 빈 코크핏이다 — 채워지면 재측정 요.

import { existsSync } from "node:fs";
import { resolve } from "node:path";

import { expect, test } from "@playwright/test";

import { auditUrl, formatCanonResult, hardFailCount } from "./design-canon-audit";

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000";
const STORAGE_STATE = resolve(__dirname, ".auth/storageState.json");

/**
 * 백엔드 부재/개발키에서 나오는 콘솔 소음은 캐논 위반이 아니다. `live-smoke.spec.ts` 와
 * 같은 필터. 측정 시엔 백엔드가 떠 있어 0이지만, 기동 안 한 채 돌려도 앱 결함만 남게 한다.
 */
const EXPECTED_CONSOLE = [
  /failed to fetch/i,
  /networkerror/i,
  /net::err_/i,
  /\b40[0-9]\b/,
  /\b50[0-9]\b/,
  /clerk has been loaded/i,
  /development keys/i,
  /\[fast refresh\]/i,
  /access to fetch/i, // CORS 차단 (백엔드 origin 미일치 시)
];
const ignoreConsole = (t: string) => EXPECTED_CONSOLE.some((re) => re.test(t));

/**
 * P1 4라우트 하드 실패 allowlist (2026-07-20 실측 baseline). S5~S8 이 줄인다.
 * nextjs-portal(dev 오버레이) 제외 후 남은 실제 앱 결함만이다.
 *   - /dashboard 0 — 깨끗.
 *   - /backtests 1 — 375px 가로 오버플로(scrollWidth 436 > 375). S5 가 고친다.
 *   - /backtests/:id/trades 3 — 검색·기간 시작·기간 종료 입력이 포커스링 없음. S6.
 *   - /trading 1 — outline-none 인 포커스가능 div("Kill Switch…"). S8.
 */
const HARDFAIL_ALLOWLIST: Readonly<Record<string, number>> = {
  "/dashboard": 0,
  "/backtests": 1,
  "/backtests/:id/trades": 3,
  "/trading": 1,
};

const auditOptions = {
  contextOptions: { storageState: STORAGE_STATE },
  ignoreConsole,
} as const;

test.describe("P1 4라우트 디자인 캐논 baseline (이식 seam #1, 로컬 전용)", () => {
  test.skip(!existsSync(STORAGE_STATE), "storageState 없음 — setup 프로젝트 먼저 실행");

  for (const path of ["/dashboard", "/backtests", "/trading"] as const) {
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

  test("/backtests/:id/trades — 하드 실패 ≤ allowlist", async ({ browser }) => {
    test.setTimeout(180_000);

    // backtest id 를 하드코딩하지 않는다 (환경마다 다르다). /backtests 에서 런타임 발견.
    const discovery = await browser.newContext({ storageState: STORAGE_STATE });
    const dpage = await discovery.newPage();
    await dpage.goto(`${BASE_URL}/backtests`, { waitUntil: "load" });
    await dpage.waitForTimeout(1500);
    const href = await dpage
      .locator('a[href^="/backtests/"]')
      .evaluateAll((els) => {
        const re = /^\/backtests\/[0-9a-f-]{36}$/;
        const found = (els as HTMLAnchorElement[]).find((a) =>
          re.test(new URL(a.href).pathname),
        );
        return found ? new URL(found.href).pathname : null;
      });
    await discovery.close();

    test.skip(!href, "완료된 백테스트 상세 링크를 찾지 못했다 (데이터 없음)");

    const res = await auditUrl(browser, `${BASE_URL}${href}/trades`, {
      label: `${href}/trades`,
      ...auditOptions,
    });
    process.stdout.write(formatCanonResult(res) + "\n");
    expect(
      hardFailCount(res),
      `/trades 하드 실패:\n${formatCanonResult(res)}`,
    ).toBeLessThanOrEqual(HARDFAIL_ALLOWLIST["/backtests/:id/trades"] ?? 0);
  });
});
