// 표 손익 색의 **캐스케이드 승패**를 실측하는 계약 ([BL-630])
//
// 왜 e2e 인가. 이 결함은 규칙 문자열의 유무가 아니라 "누가 이기는가" 다. globals.css 에
// `.pos { color: var(--bull) }`(:990, 명시도 0,1,0)이 **있는데도** `@layer components` 안의
// `table.trades tbody td`(:1632, 0,1,3)에 져서 표 안에서 손익 색이 죽는다. 소스 문자열을
// 검사하는 vitest 는 그 사고를 그대로 통과시킨다 — 브라우저가 계산한 색만이 판정이다.
//
// 기법은 자매 검사 `design-canon-tailwind-utilities.spec.ts:32-52` 와 같다. 기대값을
// 하드코딩하지 않고 같은 페이지에서 `color: var(--bull)` 을 직접 해석해 대조한다
// (rgb/rgba 표기 정규화가 공짜로 따라온다).
//
// ★역방향 2건이 핵심이다. 정방향만 재면 「민짜 `.pos { color }` 로 전역 우선권을 넘기는」
// 잘못된 수리도 통과한다. `td.num`(손익 아님) 과 민짜 `td` 가 각각 `--ink` · `--ink-2` 로
// 남아 있는지 함께 봐야 폭발반경 누수를 잡는다.
//
// 공개 라우트(`/`)만 쓴다 — 무인증, 백엔드 무관, 소크 무결합([BL-597] 회피), CI 실행 가능.
// `table.trades` 규칙은 조상 셀렉터가 없으므로 body 직속 주입으로 충분하다.

import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

/** [td 의 class, 기대 색을 주는 CSS 변수, 이 조합을 왜 보는가]. */
const TONE_CASES: ReadonlyArray<readonly [string, string, string]> = [
  ["pos", "--bull", "★[BL-630] 그 구멍 — `.num` 없는 단독 `.pos`"],
  ["neg", "--bear", "★[BL-630] 그 구멍 — `.num` 없는 단독 `.neg`"],
  ["num pos", "--bull", "기존 수리(td.num.pos) 회귀 가드"],
  ["num neg", "--bear", "기존 수리(td.num.neg) 회귀 가드"],
  ["num", "--ink", "★역방향 — 손익 아닌 숫자 셀은 --ink 그대로여야 한다"],
  ["", "--ink-2", "★역방향 — 민짜 td 는 --ink-2 그대로여야 한다"],
];

interface ToneRow {
  cls: string;
  varName: string;
  why: string;
  got: string;
  want: string;
}

/** 주입한 `table.trades` 의 각 셀 computed color 와, 대응 변수의 직접 해석값을 함께 뽑는다. */
async function measure(page: Page): Promise<ToneRow[]> {
  return page.evaluate(
    (cases) => {
      const table = document.createElement("table");
      table.className = "trades";
      table.innerHTML =
        "<tbody><tr>" +
        cases.map(([cls]) => `<td class="${cls}">1.00</td>`).join("") +
        "</tr></tbody>";
      document.body.appendChild(table);
      const got = [...table.querySelectorAll("td")].map((td) => getComputedStyle(td).color);
      table.remove();

      const probe = document.createElement("div");
      document.body.appendChild(probe);
      const want = cases.map(([, varName]) => {
        probe.style.color = `var(${varName})`;
        return getComputedStyle(probe).color;
      });
      probe.remove();

      return cases.map(([cls, varName, why], i) => ({
        cls,
        varName,
        why,
        got: got[i]!,
        want: want[i]!,
      }));
    },
    TONE_CASES as Array<[string, string, string]>,
  );
}

function assertTone(rows: ToneRow[]): void {
  expect(rows, "주입한 td 개수가 케이스 수와 다르다").toHaveLength(TONE_CASES.length);
  for (const r of rows) {
    expect(r.want, `var(${r.varName}) 가 해석되지 않았다 — 캐논 별칭 토큰이 사라졌다`).not.toBe("");
    expect(
      r.got,
      `<td class="${r.cls || "(민짜)"}"> 의 색이 ${r.varName} 가 아니다 ` +
        `(got ${r.got} / want ${r.want}).\n  ${r.why}`,
    ).toBe(r.want);
  }
}

test.describe("표 손익 색 캐스케이드 계약 (BL-630, CI)", () => {
  test("다크 테마 — 6조합", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("body")).toBeVisible();
    assertTone(await measure(page));
  });

  test("라이트 테마 — 6조합", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("body")).toBeVisible();
    // next-themes 는 html 에 클래스를 얹는다. `.dark` 를 걷어내면 `:root` 값이 드러난다.
    await page.evaluate(() => document.documentElement.classList.remove("dark"));
    assertTone(await measure(page));
  });
});
