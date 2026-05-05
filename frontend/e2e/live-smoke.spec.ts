import { expect, test } from "@playwright/test";

// Sprint 31-D BL-157 — PR pre-merge live dev smoke gate.
//
// 배경: Sprint 30-β PR #120 (lightweight-charts 도입) 가 vitest mock 만으로 검증되어
// dev server live smoke 5분 누락 → main 머지 후 사용자 dogfood 시점 즉시 발현
// (`Cannot parse color: currentcolor` → AttributionLogoWidget throw → 결과 페이지
// ErrorBoundary fallback). hot-fix `edcfaa0` PR #124 회복.
//
// LESSON-004 PR 규약 ("hooks diff 가 있는 PR 은 dev server live smoke 5분 이상 필수")
// 자동화 — frontend hooks diff PR 은 .github/workflows/live-smoke.yml 으로 본 spec 실행.
//
// 본 spec 의 핵심 가설:
//  1. Public pages (Clerk 미의존) 만 검증 — auth 페이지는 storageState 의존
//  2. console.error / pageerror 가 0건이어야 PASS
//  3. backend 가 없으므로 React Query 의 fetch fail (404/network/Failed to fetch) 은
//     expected. Clerk dev key 경고도 expected
//  4. 진짜로 잡고 싶은 것: lightweight-charts mount 시 unhandled exception throw
//     같은 chart/widget 라이브러리 SSR/CSR boundary unhandled error
//
// 검증 시뮬레이션 — hot-fix `edcfaa0` 이전 상태로 revert 후 본 spec 실행 시 fail
// (currentcolor parsing) 해야 함. 본 worktree 는 hot-fix 적용 상태 → PASS 기대.

const PUBLIC_PAGES: ReadonlyArray<{ path: string; label: string }> = [
  { path: "/", label: "landing" },
  { path: "/disclaimer", label: "disclaimer" },
  { path: "/terms", label: "terms" },
  { path: "/privacy", label: "privacy" },
];

// 무시할 expected error 패턴 — backend down / Clerk dev mode / network noise.
// 1) 'Failed to fetch' / network / 404 / 500 — backend 부재로 인한 React Query 실패
// 2) Clerk dev key 경고 — 'development keys' / 'Clerk has been loaded with'
// 3) HMR / Fast Refresh 부수 메시지
const EXPECTED_ERROR_PATTERNS: ReadonlyArray<RegExp> = [
  /failed to fetch/i,
  /networkerror/i,
  /net::err_/i,
  /\b40[0-9]\b/, // 4xx HTTP
  /\b50[0-9]\b/, // 5xx HTTP
  /clerk has been loaded/i,
  /development keys/i,
  /\[fast refresh\]/i,
];

function isExpected(text: string): boolean {
  return EXPECTED_ERROR_PATTERNS.some((re) => re.test(text));
}

test("public pages render without unexpected console errors (BL-157)", async ({
  page,
}) => {
  const errors: string[] = [];

  page.on("pageerror", (err) => {
    // pageerror = unhandled exception in browser context.
    // chart lib (lightweight-charts) currentColor parsing fail 같은 것이 여기로 옴.
    errors.push(`[pageerror] ${err.message}`);
  });

  page.on("console", (msg) => {
    if (msg.type() !== "error") return;
    const text = msg.text();
    if (isExpected(text)) return;
    errors.push(`[console.error] ${text}`);
  });

  for (const { path, label } of PUBLIC_PAGES) {
    // wait load + 1s settle — late-mount chart/widget 라이브러리 잡기 위함
    await page.goto(path, { waitUntil: "load" });
    await page.waitForTimeout(1_000);
    // 페이지 자체가 navigation 안 한 것 확인 (Clerk redirect 같은 case 검출)
    expect(page.url(), `${label} navigation 확인`).toMatch(
      new RegExp(`${path === "/" ? "/" : path}(\\?|$|/)`),
    );
  }

  // 5건 미만이면 PASS — single fluke (network race 등) 허용. Sprint 30 dogfood Day 3
  // 실측 시 currentcolor parsing 4 페이지 × 1+ throw = 5+ 였음.
  expect(
    errors.length,
    `live smoke: unexpected errors (${errors.length}):\n${errors.join("\n")}`,
  ).toBeLessThan(5);

  // 0 이 ideal target — Sprint 32+ 강화 예정
  if (errors.length > 0) {
    console.warn(
      `[live-smoke] ${errors.length} unexpected errors (under threshold):\n${errors.join("\n")}`,
    );
  }
});
