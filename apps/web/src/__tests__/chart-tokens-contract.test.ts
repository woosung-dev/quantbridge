// chart-tokens.ts 가 읽는 CSS 변수가 globals.css 에 실재하는지 검사하는 이식 안전망
//
// 왜 필요한가. resolveChartTokens() 는 read(name, fallback) 으로 변수를 읽고,
// 이름이 어긋나면 getPropertyValue 가 빈 문자열을 반환해 조용히 폴백으로 떨어진다.
// 타입 에러도 런타임 에러도 없고 차트 색만 틀린다. S1a 의 토큰 리네임이 정확히
// 이 상황을 만들 수 있어서, 리네임 전에 세워 둔다.
//
// 이 검사는 소스 텍스트 seam 이다. 브라우저에서 실제로 해석되는지는 자매 검사인
// `e2e/design-canon-runtime.spec.ts` 가 본다 (jsdom 은 커스텀 프로퍼티를 해석하지 못한다).

import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

const FRONTEND_ROOT = resolve(__dirname, "../..");
const CHART_TOKENS_TS = resolve(FRONTEND_ROOT, "src/lib/chart-tokens.ts");
const GLOBALS_CSS = resolve(FRONTEND_ROOT, "src/styles/globals.css");

/**
 * 차트 팔레트 계약. resolveChartTokens() 가 읽어야 하는 변수 전체.
 * 코드에서 뽑아낸 값이 아니라 별도로 적은 기대값이다 — 계약이 소리 없이
 * 바뀌면 (변수 추가/삭제) 이 목록과 어긋나 빨개진다.
 */
const CHART_TOKEN_CONTRACT: readonly string[] = [
  "--bullish",
  "--bearish",
  "--chart-equity",
  "--chart-benchmark",
  "--chart-compare",
  "--text-muted",
  "--border",
  "--chart-dd-line",
  "--chart-dd-top",
  "--chart-dd-bottom",
];

const chartTokensSource = readFileSync(CHART_TOKENS_TS, "utf-8");
const globalsCss = readFileSync(GLOBALS_CSS, "utf-8");

/** `read("--foo", ...)` 호출에서 변수 이름만 뽑는다. */
function readVariableNames(source: string): string[] {
  return [...source.matchAll(/\bread\(\s*"(--[a-z0-9-]+)"/gi)].map((m) => m[1]!);
}

/** 지정한 셀렉터 블록 안에 정의된 커스텀 프로퍼티 이름 집합. */
function definedIn(css: string, blockPattern: RegExp): Set<string> {
  const block = css.match(blockPattern);
  if (!block) throw new Error(`CSS 블록을 찾지 못했다: ${String(blockPattern)}`);
  return new Set([...block[0].matchAll(/^\s*(--[a-z0-9-]+)\s*:/gim)].map((m) => m[1]!));
}

const readNames = readVariableNames(chartTokensSource);
const rootTokens = definedIn(globalsCss, /^:root\s*\{[\s\S]*?^\}/m);
const darkTokens = definedIn(globalsCss, /^\.dark\s*\{[\s\S]*?^\}/m);

describe("chart-tokens.ts CSS 변수 계약 (이식 S1a 안전망)", () => {
  // ── 위생 — 아무것도 못 읽었는데 통과하는 사태 차단 ──
  it("chart-tokens.ts 에서 read() 호출을 실제로 찾아냈다", () => {
    expect(readNames.length).toBe(CHART_TOKEN_CONTRACT.length);
  });

  it("globals.css 의 :root 와 .dark 를 실제로 읽어냈다", () => {
    expect(rootTokens.size).toBeGreaterThan(40);
    expect(darkTokens.size).toBeGreaterThan(40);
  });

  // ── 본 검사 ──
  it("read() 가 읽는 변수 집합이 계약과 정확히 같다", () => {
    expect([...readNames].sort()).toEqual([...CHART_TOKEN_CONTRACT].sort());
  });

  it.each(CHART_TOKEN_CONTRACT)("%s 가 :root(라이트)에 정의돼 있다", (token) => {
    expect(rootTokens.has(token), `${token} 이 :root 에 없다. 폴백으로 조용히 떨어진다`).toBe(true);
  });

  it.each(CHART_TOKEN_CONTRACT)("%s 가 .dark 에 정의돼 있다", (token) => {
    expect(darkTokens.has(token), `${token} 이 .dark 에 없다. 폴백으로 조용히 떨어진다`).toBe(true);
  });

  // ── 역방향 래칫 [BL-629] ──
  //
  // 위 검사는 「있어야 할 것이 있는가」만 본다. 그래서 정의만 있고 아무도 안 읽는
  // 토큰이 7종(axis · grid · bullish · bearish · line · area-top · area-bottom) 쌓여
  // 있었고, 그중 다크 `--chart-axis` 는 캐논 교정에서 `--text-muted` 가 #8b939c 로
  // 올라갈 때 따라오지 못해 구값 #7a828c 에 남았다 — **아무 검사도 그것을 못 봤다.**
  // 7종을 지웠으니 이제 반대 방향을 잠근다: 정의 집합 자체를 동결한다.
  //
  // 늘리려면 먼저 답해라 — **이 토큰을 읽는 코드가 어디 있는가.** 읽는 코드가 있으면
  // CHART_TOKEN_CONTRACT 에도 들어가야 하고, 없으면 애초에 정의하지 마라.
  //
  // [BL-649] 2026-08-08 — 여기 있던 shadcn 카테고리 팔레트 `--chart-1..5` 를 지웠다.
  // `--color-chart-N` 유틸 소비가 실측 0건이었고, `--chart-4`(#875206)는 [BL-628] 이전
  // `--warning` 의 사본이라 이미 드리프트해 있었다 — 위 [BL-629] 와 같은 사고다.
  const CHART_VARS_FROZEN: readonly string[] = [
    // chart-tokens.ts 가 실제로 read() 하는 것
    "--chart-benchmark",
    "--chart-compare",
    "--chart-dd-bottom",
    "--chart-dd-line",
    "--chart-dd-top",
    "--chart-equity",
  ];

  it.each(["라이트 :root", "다크 .dark"] as const)(
    "%s 의 --chart-* 정의 집합이 동결값과 같다",
    (label) => {
      const source = label.startsWith("라이트") ? rootTokens : darkTokens;
      const defined = [...source].filter((n) => n.startsWith("--chart-")).sort();
      expect(
        defined,
        `${label} 의 --chart-* 가 동결 목록과 다르다. 데드 토큰이 되살아났거나 ` +
          `읽는 코드 없이 새 --chart-* 가 늘었다`,
      ).toEqual([...CHART_VARS_FROZEN].sort());
    },
  );
});
