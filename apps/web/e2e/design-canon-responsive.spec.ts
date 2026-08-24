// 앱 셸 반응형 **경계**의 실측 집행 ([BL-618])
//
// 왜 필요한가 (2026-08-08 실측). e2e 전체에서 `sidebar` grep 이 **0건**이었다 — 어떤 spec 도
// `--sidebar-w` · `.sidebar` 폭 · `.page` max-width 를 재지 않았다. 유일한 인접 검사인
// `src/__tests__/design-canon-tokens.test.ts` 는 `_kit.html` `:root` 의 **기본값(232px)** 만
// 문자열로 대조하고 미디어쿼리 사다리(1024→64 / 768→0)는 아무도 보지 않는다. 그래서
// `DESIGN.md` §10.2 가 「220px / 60px / 1200px↓ 축소」라고 적고 있어도 게이트가 조용했다.
//
// ★공개 라우트에는 `.sidebar` 가 렌더되지 않는다(앱 셸은 인증 뒤에 있고, 인증 e2e 는 소크
// 상태에 결합된다 — [BL-597]). 그래서 3층으로 나눠 잰다:
//   ① 토큰 사다리   — `:root` 의 `--sidebar-w`. 미디어쿼리 자체를 집행한다.
//   ② 주입 `.sidebar` — `--sidebar-w` → `.sidebar { width: var(--sidebar-w) }` 사슬과
//                       `@media (max-width: 768px)`의 `.sidebar { display: none }`.
//                       ①만 재면 이 사슬이 끊겨도 green 이다. `.sidebar` 는 `position:fixed`
//                       에 조상 셀렉터가 없어 body 직속 주입으로 정확히 잰다.
//   ③ 실물 `.page`   — 주입이 아니라 진짜 렌더 요소. `/maintenance` 는 화면 스코프 래퍼가
//                       없어 `.page { max-width: 1240px }`, `/` 는 `.lp-page .page { max-width: 1120px }`.
//
// 인증 셸에서 **실제로 렌더된** `.sidebar` 실측은 이 회차 범위 밖이다 — [BL-648].

import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

/** [CSS 유효 폭, 기대 `--sidebar-w`, 근거]. 경계 **양쪽**을 다 재야 off-by-one 을 잡는다. */
const SIDEBAR_LADDER: ReadonlyArray<readonly [number, string, string]> = [
  [1025, "232px", "기본 `:root`의 `--sidebar-w: 232px` — 1024 초과"],
  [1024, "64px", "`@media (max-width: 1024px)`의 `--sidebar-w: 64px` (경계 포함)"],
  [769, "64px", "768 초과이므로 레일 유지"],
  [768, "0px", "`@media (max-width: 768px)`의 `--sidebar-w: 0px` (경계 포함) + 모바일 drawer"],
];

/**
 * CSS 유효 폭을 정확히 `target` 으로 맞춘다.
 *
 * ★`max-width` 미디어는 스크롤바를 **뺀** `documentElement.clientWidth` 로 매칭한다.
 * 보정 없이 1025 를 요청하면 고전 스크롤바 15px 때문에 유효 폭이 1010 이 되어 `≤1024` 가
 * 발화하고 232 대신 64 가 나온다 — **코드 결함이 아니라 측정 결함**이다. 여기서 흡수하고,
 * 못 맞추면 그 사실을 명시해 실패한다(다음 사람이 셸을 의심하지 않도록).
 */
async function setCssWidth(page: Page, target: number): Promise<void> {
  await page.setViewportSize({ width: target, height: 1000 });
  const gap = await page.evaluate(() => window.innerWidth - document.documentElement.clientWidth);
  if (gap > 0) {
    await page.setViewportSize({ width: target + gap, height: 1000 });
  }
  const effective = await page.evaluate(() => document.documentElement.clientWidth);
  expect(
    effective,
    `CSS 유효 폭 보정 실패 (요청 ${target} / 실측 ${effective} / 스크롤바 ${gap}px). ` +
      `★이 실패는 측정 문제이지 셸 코드 문제가 아니다.`,
  ).toBe(target);
}

interface SidebarProbe {
  token: string;
  width: number;
  display: string;
  boxSizing: string;
}

/** `:root` 토큰과, 주입한 `.sidebar` 의 실제 박스를 한 번에 읽는다. */
async function probeSidebar(page: Page): Promise<SidebarProbe> {
  return page.evaluate(() => {
    const token = getComputedStyle(document.documentElement).getPropertyValue("--sidebar-w").trim();
    const el = document.createElement("aside");
    el.className = "sidebar";
    document.body.appendChild(el);
    const cs = getComputedStyle(el);
    const out = {
      token,
      width: Math.round(el.getBoundingClientRect().width),
      display: cs.display,
      boxSizing: cs.boxSizing,
    };
    el.remove();
    return out;
  });
}

test.describe("앱 셸 반응형 경계 실측 (BL-618, CI)", () => {
  test("--sidebar-w 사다리 4점 + .sidebar 실폭", async ({ page }) => {
    await page.goto("/maintenance");
    await expect(page.locator("main.page")).toBeVisible();

    for (const [cssWidth, want, why] of SIDEBAR_LADDER) {
      await setCssWidth(page, cssWidth);
      const got = await probeSidebar(page);

      expect(
        got.token,
        `${cssWidth}px: --sidebar-w 가 ${want} 가 아니다 (got ${got.token}) — ${why}`,
      ).toBe(want);

      const wantPx = Number.parseInt(want, 10);
      if (wantPx === 0) {
        // 토큰만 0 이면 반쪽이다. `@media (max-width: 768px)`의 `.sidebar { display: none }`이 살아 있어야 한다.
        expect(
          got.display,
          `${cssWidth}px: .sidebar 가 display:none 이어야 한다 (@media (max-width: 768px)의 .sidebar 규칙)`,
        ).toBe("none");
      } else {
        expect(
          got.display,
          `${cssWidth}px: .sidebar 가 보여야 한다 (got display:${got.display})`,
        ).not.toBe("none");
        expect(
          got.width,
          `${cssWidth}px: .sidebar 실폭이 --sidebar-w(${want})와 다르다 — ` +
            `토큰→width 사슬(.sidebar { width: var(--sidebar-w) })이 끊겼다. box-sizing=${got.boxSizing}`,
        ).toBe(wantPx);
      }
    }
  });

  test("768px 데드심 — KITPORT(≤768)와 Tailwind 셸 변형이 같은 쪽에 선다", async ({ page }) => {
    // KITPORT `max-width:768` 은 경계 **포함**(햄버거 노출·사이드바 숨김)인데, 종전 셸은
    // Tailwind `md:`(min-width:768)를 써서 **정확히 768px** 에서 햄버거는 보이는데 drawer 와
    // 상단바 계정 버튼이 함께 숨었다(데드심). 수리 후 셸의 삼분할:
    //   drawer 콘텐츠 = `min-[769px]:hidden`(모바일 전용) ·
    //   상단바 계정 = `min-[1025px]:hidden`(모바일 + 아이콘 레일 — 레일에서 사이드바 액션이
    //     숨는 동안 로그아웃/삭제 경로를 상단바가 잇는다, codex P2 2026-08-18) ·
    //   사이드바 계정 액션 = globals 의 `.sidebar .qb-acct-action` 스코프 규칙(769~1024 양끝
    //     포함 raw 미디어 — 스택 max-[1024px]: 은 `width < 1024` 라 경계 1024px 를 놓친다).
    // 각 유틸이 KITPORT 미디어와 같은 경계에 서는지 주입으로 실측한다(①②와 같은 이유로 공개 라우트 + 주입).
    await page.goto("/maintenance");
    await expect(page.locator("main.page")).toBeVisible();

    const probe = () =>
      page.evaluate(() => {
        const displayOf = (cls: string, parentCls?: string) => {
          const host = document.createElement("div");
          if (parentCls) host.className = parentCls;
          const el = document.createElement("div");
          el.className = cls;
          host.appendChild(el);
          document.body.appendChild(host);
          const d = getComputedStyle(el).display;
          host.remove();
          return d;
        };
        return {
          hamburger: displayOf("hamburger"),
          mobileOnly: displayOf("min-[769px]:hidden"),
          headerAccount: displayOf("min-[1025px]:hidden"),
          railHidden: displayOf("qb-acct-action", "sidebar"),
        };
      });

    // [CSS 유효 폭, 햄버거 display, 모바일 전용 보임?, 상단바 계정 보임?, 사이드바 액션 숨김?]
    const LADDER: ReadonlyArray<readonly [number, string, boolean, boolean, boolean]> = [
      [768, "grid", true, true, false], // 경계 자체 — 햄버거·drawer·상단바 계정이 **함께** 살아야 한다
      [769, "none", false, true, true], // 레일 시작 — 사이드바 액션 숨김, 상단바 계정이 경로 담당
      [1024, "none", false, true, true], // 레일 끝(경계 포함)
      [1025, "none", false, false, false], // 풀 사이드바 — 사이드바 액션 복귀, 상단바 계정 숨김
    ];
    for (const [
      cssWidth,
      wantHamburger,
      wantMobileVisible,
      wantHeaderAccount,
      wantRailHidden,
    ] of LADDER) {
      await setCssWidth(page, cssWidth);
      const got = await probe();
      expect(
        got.hamburger,
        `${cssWidth}px: .hamburger display 가 ${wantHamburger} 여야 한다 (got ${got.hamburger})`,
      ).toBe(wantHamburger);
      expect(
        got.mobileOnly !== "none",
        `${cssWidth}px: min-[769px]:hidden 요소 보임 여부가 KITPORT 햄버거와 어긋난다 ` +
          `(display=${got.mobileOnly}) — 768px 데드심 회귀`,
      ).toBe(wantMobileVisible);
      expect(
        got.headerAccount !== "none",
        `${cssWidth}px: 상단바 계정(min-[1025px]:hidden) 보임 여부가 어긋난다 ` +
          `(display=${got.headerAccount}) — 레일 구간 로그아웃 경로 소실 회귀 (codex P2)`,
      ).toBe(wantHeaderAccount);
      expect(
        got.railHidden === "none",
        `${cssWidth}px: 사이드바 계정 액션(.sidebar .qb-acct-action) 숨김 발화가 레일 구간` +
          `(769~1024 양끝 포함)과 어긋난다 (display=${got.railHidden})`,
      ).toBe(wantRailHidden);
    }
  });

  test(".page max-width — 앱 셸 공용 1240 / 랜딩 1120", async ({ page }) => {
    // 어느 미디어도 발화하지 않는 폭. `.page` 의 max-width 는 폭에 따라 바뀌지 않는다
    // (≤768 에서 바뀌는 것은 `@media (max-width: 768px)`의 `.page` padding 뿐).
    await page.goto("/maintenance");
    await setCssWidth(page, 1440);
    await expect(page.locator("main.page")).toBeVisible();
    expect(
      await page.locator("main.page").evaluate((el) => getComputedStyle(el).maxWidth),
      "공용 .page 는 1240px 이어야 한다 (.page { max-width: 1240px }). " +
        "/maintenance 는 화면 스코프 래퍼가 없어 base 규칙이 그대로 걸린다",
    ).toBe("1240px");

    await page.goto("/");
    const landing = page.locator(".lp-page .page").first();
    await expect(landing).toBeVisible();
    expect(
      await landing.evaluate((el) => getComputedStyle(el).maxWidth),
      "랜딩 `.lp-page .page` 는 1120px 이어야 한다 (.lp-page .page { max-width: 1120px })",
    ).toBe("1120px");
  });
});
