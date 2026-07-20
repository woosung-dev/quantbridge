// 공개 라우트의 디자인 캐논 baseline + 래칫 (이식 seam #1, CI 실행 가능)
//
// 병행안(HANDOFF §2 확정) = "프로토타입+공개라우트는 CI, authed 는 로컬".
// 캘리브레이션이 감사 코어를 프로토타입에 고정하고, 이 파일이 그 코어를 **실행 중인 앱의
// 공개 라우트**에 조준한다. 파일명이 design-canon-* 라 chromium-design-canon 프로젝트가
// 매치 → 인증 없이 CI 에서 돈다 (webServer 자동 기동). authed P1 은 authed-canon-p1 의 몫.
//
// 이게 없으면 CI 의 캐논 게이트는 정적 프로토타입만 보고 실행 중인 앱은 한 번도 감사하지
// 않는다. 랜딩(`/`)은 차트 쇼케이스·bento 로 P1 밖에서 가장 회귀가 잦은 공개 표면이다.
//
// canon 은 하드 실패가 아니라 지표다 (audit 코어 주석). 공개 마케팅 페이지는 C 카드 표면
// 캐논의 대상이 아니므로 canon 수치는 크게 나오지만 게이트하지 않는다. 게이트는
// overflow · 대비 AA · 포커스링 · 콘솔 · reduced-motion 이라는 보편 기준뿐이다.

import { expect, test } from "@playwright/test";

import { auditUrl, formatCanonResult, hardFailCount } from "./design-canon-audit";

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000";

/** 백엔드 부재/개발키 콘솔 소음 필터. `live-smoke.spec.ts` 와 같은 목록. */
const EXPECTED_CONSOLE = [
  /failed to fetch/i,
  /networkerror/i,
  /net::err_/i,
  /\b40[0-9]\b/,
  /\b50[0-9]\b/,
  /clerk has been loaded/i,
  /development keys/i,
  /\[fast refresh\]/i,
  /access to fetch/i,
];
const ignoreConsole = (t: string) => EXPECTED_CONSOLE.some((re) => re.test(t));

/**
 * 공개 라우트 하드 실패 allowlist (2026-07-20 실측 baseline). 슬라이스가 줄인다.
 *   - `/` 2 — "Bybit Demo 연동 (Beta)" 가 rgb(122,130,140)=#7a828c 로 4.3:1 (AA 4.5 미달).
 *     1440·375 두 폭에서 같은 결함이 잡혀 2다. ★이 색은 토큰 감사가 잡은 --text-muted 와
 *     같다 (context-notes §2, 카드 위 4.66 미달). **S1a 의 --text-muted→#8b939c 교정이
 *     이 랜딩 결함도 함께 고친다** — 그때 이 항목이 0으로 내려간다.
 *   - `/waitlist` 0 — 깨끗.
 * /pricing 은 현재 `/` 로 리다이렉트해 같은 결함이 중복 잡히므로 대상에서 뺐다.
 */
const HARDFAIL_ALLOWLIST: Readonly<Record<string, number>> = {
  "/": 2,
  "/waitlist": 0,
};

test.describe("공개 라우트 디자인 캐논 baseline (이식 seam #1, CI)", () => {
  for (const path of Object.keys(HARDFAIL_ALLOWLIST)) {
    test(`${path} — 하드 실패 ≤ allowlist`, async ({ browser }) => {
      test.setTimeout(120_000);
      const res = await auditUrl(browser, `${BASE_URL}${path}`, {
        label: path,
        ignoreConsole,
      });
      process.stdout.write(formatCanonResult(res) + "\n");
      expect(
        hardFailCount(res),
        `${path} 하드 실패:\n${formatCanonResult(res)}`,
      ).toBeLessThanOrEqual(HARDFAIL_ALLOWLIST[path] ?? 0);
    });
  }
});
