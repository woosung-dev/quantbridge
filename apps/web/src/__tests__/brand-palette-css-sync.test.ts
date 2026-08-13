// brand-palette.ts ↔ globals.css `:root`/`.dark` 동기화 계약을 **집행하는** 검사
//
// 왜 필요한가. `brand-palette.ts:7-8` 이 "이 파일과 globals.css 의 :root/.dark 값은 항상
// 같은 커밋에서 함께 변경한다" 를 명문화하고 있는데, 2026-08-07 B2 팔레트 적용 시점까지
// **그 문장을 집행하는 테스트가 없었다**. 산문만 있고 게이트가 없으면 desync 는 조용히 통과한다.
//
// desync 가 만드는 결함은 런타임 에러가 아니라 색만 틀리는 종류다.
//   - chart-tokens.ts 의 SSR 폴백이 구팔레트를 그려 하이드레이션 직후 색이 튄다
//   - Monaco 에디터 테마(pine-language.ts)와 OG 이미지(opengraph-image.tsx)는
//     CSS 변수를 읽을 수 없어 **영구히** 구팔레트로 남는다
//
// 자매 검사와의 분업.
//   - `design-canon-tokens.test.ts` = 프로토타입 정본 ↔ globals.css `.dark`
//   - `chart-tokens-contract.test.ts` = chart-tokens.ts 가 읽는 변수의 **존재**
//   - 이 파일                        = brand-palette.ts ↔ globals.css 양쪽 테마의 **값**

import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

import { BRAND_PALETTE } from "@/lib/brand-palette";

const FRONTEND_ROOT = resolve(__dirname, "../..");
const GLOBALS_CSS = resolve(FRONTEND_ROOT, "src/styles/globals.css");

/**
 * BRAND_PALETTE 키 -> globals.css 커스텀 프로퍼티 이름.
 *
 * 코드에서 유도하지 않고 손으로 적는다 — 유도하면 양쪽이 같은 실수를 공유해
 * 테스트가 자기 구현의 거울이 된다. 키가 추가/삭제되면 아래 커버리지 검사가 빨개진다.
 */
const KEY_TO_VAR: ReadonlyArray<readonly [key: string, cssVar: string]> = [
  ["bg", "--bg"],
  ["bgAlt", "--bg-alt"],
  ["card", "--card"],
  ["cardRaised", "--card-raised"],
  ["border", "--border"],
  ["borderDark", "--border-dark"],
  ["textPrimary", "--text-primary"],
  ["textSecondary", "--text-secondary"],
  ["textMuted", "--text-muted"],
  ["primary", "--primary"],
  ["primaryHover", "--primary-hover"],
  ["bullish", "--bullish"],
  ["bearish", "--bearish"],
  ["success", "--success"],
  ["destructive", "--destructive"],
  ["warning", "--warning"],
  ["chartEquity", "--chart-equity"],
  ["chartBenchmark", "--chart-benchmark"],
  ["chartCompare", "--chart-compare"],
  // [BL-629] chartGrid 삭제 — `--chart-grid` 는 참조 0건이었고 chart-tokens.ts 는
  // 그리드 색으로 `--border` 를 읽는다. 팔레트 키와 CSS 토큰을 함께 지웠다.
  ["ddLine", "--chart-dd-line"],
  ["ddTop", "--chart-dd-top"],
  ["ddBottom", "--chart-dd-bottom"],
] as const;

/** 테마 -> globals.css 안에서 그 테마 값을 담는 블록. */
const THEME_BLOCK: ReadonlyArray<readonly [theme: "light" | "dark", pattern: RegExp]> = [
  ["light", /^:root\s*\{[\s\S]*?^\}/m],
  ["dark", /^\.dark\s*\{[\s\S]*?^\}/m],
] as const;

/** 지정 블록에서 커스텀 프로퍼티만 뽑는다. 값은 `;` 앞까지 — 뒤따르는 주석은 값이 아니다. */
function readTokenBlock(css: string, blockPattern: RegExp): Map<string, string> {
  const block = css.match(blockPattern);
  if (!block) throw new Error(`CSS 블록을 찾지 못했다: ${String(blockPattern)}`);
  const tokens = new Map<string, string>();
  for (const line of block[0].split("\n")) {
    const matched = line.match(/^\s*(--[a-z0-9-]+)\s*:\s*([^;]+);/i);
    const [, name, value] = matched ?? [];
    if (name && value) tokens.set(name, value.trim());
  }
  return tokens;
}

/** `#FFF` 대소문자와 `rgba(1, 2, 3, 0.10)` 공백/소수 표기를 흡수한다. */
function normalize(value: string): string {
  return value
    .replace(/\s+/g, "")
    .toLowerCase()
    .replace(/rgba?\(([^)]*)\)/, (_full, inner: string) => {
      const parts = inner.split(",").map((n) => String(parseFloat(n)));
      return `rgba(${parts.join(",")})`;
    });
}

const globalsCss = readFileSync(GLOBALS_CSS, "utf-8");
const cssTokens = new Map(
  THEME_BLOCK.map(([theme, pattern]) => [theme, readTokenBlock(globalsCss, pattern)] as const),
);

describe("brand-palette.ts ↔ globals.css 동기화 계약", () => {
  // ── 위생 메타테스트 — 아무것도 못 읽었는데 통과하는 사태를 막는다 ──
  it(":root 와 .dark 에서 토큰을 실제로 읽어냈다", () => {
    expect(cssTokens.get("light")!.size).toBeGreaterThan(40);
    expect(cssTokens.get("dark")!.size).toBeGreaterThan(40);
  });

  it("매핑표가 BRAND_PALETTE 의 키를 빠짐없이 덮는다", () => {
    const mapped = new Set(KEY_TO_VAR.map(([key]) => key));
    for (const theme of ["light", "dark"] as const) {
      const uncovered = Object.keys(BRAND_PALETTE[theme]).filter((k) => !mapped.has(k));
      expect(uncovered, `${theme} 에서 매핑표가 빠뜨린 키: ${uncovered.join(", ")}`).toEqual([]);
    }
  });

  it("매핑표의 CSS 변수가 양쪽 테마 블록에 실재한다", () => {
    const absent: string[] = [];
    for (const theme of ["light", "dark"] as const) {
      for (const [key, cssVar] of KEY_TO_VAR) {
        if (!cssTokens.get(theme)!.has(cssVar)) absent.push(`${theme}.${key} -> ${cssVar}`);
      }
    }
    expect(absent, `globals.css 에 없는 변수: ${absent.join(", ")}`).toEqual([]);
  });

  // ── 본 검사 — 값 일치 ──
  it.each(["light", "dark"] as const)("%s 팔레트 값이 globals.css 와 일치한다", (theme) => {
    const palette: Record<string, string> = BRAND_PALETTE[theme];
    const tokens = cssTokens.get(theme)!;
    const mismatches = KEY_TO_VAR.flatMap(([key, cssVar]) => {
      const tsValue = palette[key];
      const cssValue = tokens.get(cssVar);
      if (tsValue === undefined || cssValue === undefined) return [];
      if (normalize(tsValue) !== normalize(cssValue)) {
        return [`${cssVar}: brand-palette ${tsValue} / globals.css ${cssValue}`];
      }
      return [];
    });
    expect(
      mismatches,
      `동기화 계약 위반 (brand-palette.ts:7-8) — 같은 커밋에서 함께 고쳐라:\n${mismatches.join("\n")}`,
    ).toEqual([]);
  });
});
