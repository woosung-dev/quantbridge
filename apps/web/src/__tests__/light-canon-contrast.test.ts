// 라이트 팔레트의 **캐논 대비(5.82)** 를 커밋된 토큰값으로 집행하는 래칫 ([BL-628])
//
// 왜 필요한가 — ★런타임 캐논 감사는 라이트를 한 번도 재지 않는다 (2026-08-08 실측).
// `e2e/design-canon-audit.ts:300` 의 `browser.newContext` 는 테마를 강제하지 않고,
// `components/providers/app-providers.tsx:21` 이 `defaultTheme="dark"` 라 4폭 감사가
// **전부 다크에서** 돈다. 그래서 [BL-628](라이트 `--warning` 이 `--warning-subtle` 위에서
// 5.66) 은 등재만 되고 **어떤 게이트도 물지 않은 채** 배포돼 있었다. 같은 계열이 이미
// 한 번 있었다 — 라이트 테마 WCAG AA 하드 실패 116건(2026-08-07 backtest-fidelity).
//
// 브라우저 없이 순수 계산으로 같은 것을 잰다. 결정적이고 밀리초 단위이며 `pnpm test` 가
// 이미 게이트한다. 알파가 섞인 표면(다크 `--warning-subtle` 등)은 합성이 필요해 못 재므로
// **라이트 전용**이다 — 다크 런타임 합성은 `design-canon-audit.ts` 몫으로 남긴다.
//
// 자매 검사와의 분업.
//   - `design-canon-tokens.test.ts`    = 프로토타입 정본 ↔ globals.css `.dark` (다크 값)
//   - `brand-palette-css-sync.test.ts` = brand-palette.ts ↔ globals.css (양쪽 테마의 값)
//   - 이 파일                          = globals.css `:root` 조합의 **대비비** (라이트)

import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

const FRONTEND_ROOT = resolve(__dirname, "../..");
const GLOBALS_CSS = resolve(FRONTEND_ROOT, "src/styles/globals.css");

/**
 * 캐논 임계. `e2e/design-canon-audit.ts:174` 의 `canonNeed` 와 같은 값이어야 한다.
 * 정의 = 다크 정본의 최약 텍스트 `--ink-3`(#8b939c)가 `--card`(#141619) 위에서 갖는
 * 5.8274…의 하한. 5.83 으로 두면 캐논을 정의하는 토큰 자신이 걸린다.
 */
const CANON = 5.82;

/**
 * [텍스트 토큰, 그 위에 실제로 얹히는 표면 토큰들].
 *
 * 마크업이 만드는 조합만 적는다 — 전수 조합은 존재하지 않는 짝까지 잡아 통과 불가능한
 * 래칫이 된다. `--warning` × `--warning-subtle` 이 [BL-628] 그 자리다
 * (`components/legal-notice-banner.tsx:15` — layout.tsx 가 전 라우트에 마운트).
 */
const PAIRS: ReadonlyArray<readonly [fg: string, surfaces: readonly string[]]> = [
  ["--warning", ["--warning-subtle", "--card", "--bg", "--bg-alt"]],
  ["--text-primary", ["--card", "--bg", "--bg-alt"]],
  ["--text-secondary", ["--card", "--bg", "--bg-alt"]],
  ["--text-muted", ["--card", "--bg"]],
  ["--primary", ["--card", "--bg"]],
  ["--bullish", ["--card", "--bg"]],
  ["--bearish", ["--card", "--bg"]],
  ["--success", ["--card", "--bg"]],
  ["--destructive", ["--card", "--bg"]],
  // 솔리드 배경 위의 전경색 — 방향이 반대다(표면이 fg 토큰).
  ["--warning-foreground", ["--warning"]],
];

const css = readFileSync(GLOBALS_CSS, "utf-8");

/** `:root { ... }` 블록 안의 커스텀 프로퍼티. 파서는 brand-palette-css-sync 와 같은 형태다. */
function rootTokens(): Map<string, string> {
  const block = css.match(/^:root\s*\{[\s\S]*?^\}/m);
  if (!block) throw new Error("globals.css 에서 :root 블록을 찾지 못했다");
  const out = new Map<string, string>();
  for (const m of block[0].matchAll(/^\s*(--[a-z0-9-]+)\s*:\s*([^;]+);/gim)) {
    out.set(m[1]!, m[2]!.trim());
  }
  return out;
}

/** WCAG 2.x sRGB 상대휘도. `design-canon-audit.ts:101-105` 와 같은 식이다. */
function luminance(hex: string): number {
  const h = hex.replace("#", "");
  const full =
    h.length === 3
      ? h
          .split("")
          .map((c) => c + c)
          .join("")
      : h;
  const lin = (v: number): number => {
    const s = v / 255;
    return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  const r = lin(Number.parseInt(full.slice(0, 2), 16));
  const g = lin(Number.parseInt(full.slice(2, 4), 16));
  const b = lin(Number.parseInt(full.slice(4, 6), 16));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function ratio(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((p, q) => q - p) as [number, number];
  return (hi + 0.05) / (lo + 0.05);
}

const tokens = rootTokens();
const HEX = /^#[0-9a-f]{3}(?:[0-9a-f]{3})?$/i;

const CASES = PAIRS.flatMap(([fg, surfaces]) => surfaces.map((bg) => [fg, bg] as const));

describe("라이트 팔레트 캐논 대비 래칫 (BL-628)", () => {
  // ── 위생 — 아무것도 못 읽었는데 통과하는 사태 차단 ──
  it(":root 에서 토큰을 실제로 읽어냈다", () => {
    expect(tokens.size).toBeGreaterThan(40);
  });

  it("검사 대상 토큰이 전부 :root 에 있고 불투명 hex 다", () => {
    const bad: string[] = [];
    for (const name of new Set(CASES.flat())) {
      const v = tokens.get(name);
      if (v === undefined) bad.push(`${name} (:root 에 없다)`);
      else if (!HEX.test(v)) bad.push(`${name} = ${v} (hex 가 아니다)`);
    }
    expect(
      bad,
      `대비를 계산할 수 없는 토큰이 있다. 알파/함수 값은 합성이 필요해 이 검사로 못 잰다:\n  ${bad.join("\n  ")}`,
    ).toEqual([]);
  });

  // ── 본 검사 ──
  it.each(CASES)("%s on %s >= 5.82", (fg, bg) => {
    const fgv = tokens.get(fg)!;
    const bgv = tokens.get(bg)!;
    const r = ratio(fgv, bgv);
    expect(
      Number(r.toFixed(3)),
      `${fg}(${fgv}) on ${bg}(${bgv}) = ${r.toFixed(3)} < ${CANON}. ` +
        `AA(4.5)는 통과해도 캐논은 미달이다 — 토큰을 어둡게/밝게 옮겨라.`,
    ).toBeGreaterThanOrEqual(CANON);
  });
});
