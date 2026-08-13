// Tailwind @theme inline 유틸리티 경로가 기대 토큰값으로 해석되는지 검사하는 이식 안전망
//
// chart-tokens.ts 가 읽는 10개 CSS 변수는 자매 검사 design-canon-runtime.spec.ts 가 덮는다.
// 그러나 앱의 색 대부분은 Tailwind 유틸리티(bg-primary·text-muted-foreground 등)로 소비되고,
// 그 경로는 @theme inline 매핑(--color-primary: var(--primary))에 달려 있다. 이 매핑이 끊기면
// 유틸리티가 런타임 에러 없이 기본값(투명/상속)으로 조용히 떨어진다 — 차트 10변수 밖의,
// getComputedStyle 로만 보이는 회귀다. S1a 가 @theme inline 중복 키를 제거하므로 여기서 동결한다.
//
// 검사법: 각 유틸리티를 붙인 요소의 computed style 이, 그 유틸리티가 참조해야 하는 CSS 변수를
// 직접 해석한 값과 정확히 일치하는지 본다 (기대값을 하드코딩하지 않고 변수에서 읽어 대조).
// 다크·라이트 양쪽에서 확인한다. 공개 라우트(`/`)만 쓴다 — CI 무인증 실행 가능.

import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

/** [유틸리티 클래스, 검사할 CSS 속성, 그 유틸리티가 참조해야 하는 CSS 변수]. */
const UTILITY_TOKEN_MAP: ReadonlyArray<readonly [string, string, string]> = [
  ["bg-primary", "background-color", "--primary"],
  ["text-primary-foreground", "color", "--primary-foreground"],
  ["bg-accent", "background-color", "--accent"],
  ["text-muted-foreground", "color", "--muted-foreground"],
];

interface UtilityRow {
  cls: string;
  prop: string;
  varName: string;
  got: string;
  want: string;
}

/** 각 유틸리티의 computed 값과, 참조 변수를 직접 해석한 값을 같은 정규화(rgb/rgba)로 뽑는다. */
async function measure(page: Page): Promise<UtilityRow[]> {
  return page.evaluate((entries) => {
    return entries.map(([cls, prop, varName]) => {
      const el = document.createElement("div");
      el.className = cls;
      document.body.appendChild(el);
      const got = getComputedStyle(el).getPropertyValue(prop).trim();
      el.remove();

      // 같은 속성에 var() 를 직접 걸어 해석 — 유틸리티와 동일한 색 표기로 정규화된다.
      const probe = document.createElement("div");
      probe.style.setProperty(prop, `var(${varName})`);
      document.body.appendChild(probe);
      const want = getComputedStyle(probe).getPropertyValue(prop).trim();
      probe.remove();

      return { cls, prop, varName, got, want };
    });
  }, UTILITY_TOKEN_MAP as Array<[string, string, string]>);
}

function assertLinked(rows: UtilityRow[]): void {
  for (const r of rows) {
    expect(
      r.got,
      `${r.cls}(${r.prop}) 이 비었다 — @theme inline 매핑이 끊겼다`,
    ).not.toBe("");
    expect(
      r.got,
      `${r.cls} → ${r.varName} 링크 끊김: got ${r.got} / want ${r.want}`,
    ).toBe(r.want);
  }
}

test.describe("Tailwind @theme inline 유틸리티 경로 (이식 S1a 안전망, CI)", () => {
  test("다크 테마 — 4개 유틸리티가 기대 토큰값으로 해석된다", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("body")).toBeVisible();
    assertLinked(await measure(page));
  });

  test("라이트 테마 — 4개 유틸리티가 기대 토큰값으로 해석된다", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("body")).toBeVisible();
    // next-themes 는 html 에 클래스를 얹는다. `.dark` 를 걷어내면 `:root` 값이 드러난다.
    await page.evaluate(() => document.documentElement.classList.remove("dark"));
    assertLinked(await measure(page));
  });
});
