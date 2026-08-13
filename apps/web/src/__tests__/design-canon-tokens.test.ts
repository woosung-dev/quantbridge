// C 디자인 언어 캐논 토큰 22종이 앱 globals.css `.dark` 와 일치하는지 검사하는 이식 안전망
//
// 왜 필요한가. S1a 가 토큰 13건을 리네임하는데, `chart-tokens.ts` 의 read(name, fallback) 은
// 이름이 어긋나면 에러 없이 폴백을 반환한다. 런타임 에러 없이 색만 틀리는, 가장 탐지하기
// 어려운 회귀다. 이 테스트가 그 회귀를 리네임과 같은 슬라이스에서 빨갛게 만든다.
//
// 기대값의 출처는 프로토타입 정본 `docs/reference/design/prototypes/shotgun-2026-07/variant-c.html` 이다.
// 코드에서 재계산하지 않고 별도 진실원에서 읽는다 (tautological test 회피).
//
// allowlist 는 래칫이다. 알려진 불일치를 고정해 두고 슬라이스마다 줄인다.
// 고쳤는데 allowlist 를 안 줄이면 stale 검사가 빨개져서 래칫이 강제로 조여진다.

import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

const REPO_ROOT = resolve(__dirname, "../../..");
const CANON_HTML = resolve(
  REPO_ROOT,
  "docs/reference/design/prototypes/shotgun-2026-07/variant-c.html",
);
const GLOBALS_CSS = resolve(
  REPO_ROOT,
  "frontend/src/styles/globals.css",
);

/**
 * 캐논 토큰 -> 앱 토큰 매핑.
 *
 * 대부분은 이름이 달라도 역할이 1:1 이다. `--card-3` -> `--accent` 는 [가정] —
 * 이식 계획 문서에 명시된 매핑이 아니라 값(#1e2226)이 유일하게 일치해서 추론했다.
 * S1a 에서 리네임할 때 이 매핑이 의도와 다르면 여기를 함께 고쳐야 한다.
 */
const TOKEN_MAP: ReadonlyArray<readonly [canon: string, app: string]> = [
  ["--bg", "--bg"],
  ["--bg-alt", "--bg-alt"],
  ["--card", "--card"],
  ["--card-2", "--card-raised"],
  ["--card-3", "--accent"],
  ["--line", "--border"],
  ["--line-2", "--border-dark"],
  ["--ink", "--text-primary"],
  ["--ink-2", "--text-secondary"],
  ["--ink-3", "--text-muted"],
  ["--copper", "--primary"],
  ["--copper-hover", "--primary-hover"],
  ["--copper-ink", "--primary-foreground"],
  ["--copper-soft", "--primary-light"],
  ["--copper-line", "--primary-100"],
  ["--bull", "--bullish"],
  ["--bull-soft", "--success-subtle"],
  ["--bear", "--bearish"],
  ["--bear-soft", "--destructive-subtle"],
  ["--warn", "--warning"],
  ["--warn-soft", "--warning-subtle"],
  ["--benchmark", "--chart-benchmark"],
] as const;

/**
 * 알려진 불일치 래칫. S1a 가 5건 전부 `.dark` 값 교정으로 해소하고 비웠다 (2026-07-20).
 * 근거는 `git:0ddf2b53 docs/archive/sprints/c-language-port/context-notes.md` §1 (프로토타입 22종 대조).
 * 이제 22종 전부 값이 일치한다 — 새 불일치가 생기면 allowlist 가 비어 있어 즉시 빨개진다.
 */
const KNOWN_MISMATCHES: ReadonlyArray<{ canon: string; fixedBy: string }> = [];

/**
 * 캐논 비색상 상수. 색 매핑표(TOKEN_MAP)와 달리 이름이 캐논과 동일하고 테마 무관이라
 * 앱 `:root` 에 직접 정의된다(`.dark` 오버라이드 없음). S2 공용 CSS 가 소비하므로
 * 값이 어긋나면 런타임 에러 없이 그림자/모션/치수/폰트만 틀린다 — 색 회귀와 같은 종류의
 * 조용한 회귀다. 아래 검사가 캐논 `:root` ↔ 앱 `:root` 값 일치를 강제한다.
 */
const NON_COLOR_TOKENS = [
  "--r",
  "--shadow",
  "--shadow-hi",
  "--ease",
  "--dur",
  "--sidebar-w",
  "--topbar-h",
  "--f-body",
  "--f-display",
  "--f-mono",
] as const;
const NON_COLOR_SET: ReadonlySet<string> = new Set(NON_COLOR_TOKENS);

/** `:root { ... }` / `.dark { ... }` 블록에서 커스텀 프로퍼티만 뽑는다. */
function readTokenBlock(source: string, blockPattern: RegExp): Map<string, string> {
  const block = source.match(blockPattern);
  if (!block) {
    throw new Error(`토큰 블록을 찾지 못했다: ${String(blockPattern)}`);
  }
  const tokens = new Map<string, string>();
  for (const line of block[0].split("\n")) {
    const matched = line.match(/^\s*(--[a-z0-9-]+)\s*:\s*([^;]+);/i);
    const [, name, value] = matched ?? [];
    if (name && value) tokens.set(name, value.trim());
  }
  return tokens;
}

/** 공백과 rgba 소수 표기를 정규화해 `0.1` 과 `0.10` 을 같게 본다. */
function normalize(value: string): string {
  return value
    .replace(/\s+/g, "")
    .toLowerCase()
    .replace(/rgba?\(([^)]*)\)/, (_full, inner: string) => {
      const parts = inner.split(",").map((n) => String(parseFloat(n)));
      return `rgba(${parts.join(",")})`;
    });
}

const canonTokens = readTokenBlock(
  readFileSync(CANON_HTML, "utf-8"),
  /^ {2}:root \{[\s\S]*?^ {2}\}/m,
);
const appDarkTokens = readTokenBlock(
  readFileSync(GLOBALS_CSS, "utf-8"),
  /^\.dark\s*\{[\s\S]*?^\}/m,
);
// 비색상 상수는 테마 무관이라 `.dark` 가 아니라 `:root` 에 산다.
const appRootTokens = readTokenBlock(
  readFileSync(GLOBALS_CSS, "utf-8"),
  /^:root\s*\{[\s\S]*?^\}/m,
);

function findMismatches(): { canon: string; app: string; canonValue: string; appValue: string }[] {
  const mismatches: { canon: string; app: string; canonValue: string; appValue: string }[] = [];
  for (const [canon, app] of TOKEN_MAP) {
    const canonValue = canonTokens.get(canon);
    const appValue = appDarkTokens.get(app);
    if (canonValue === undefined || appValue === undefined) continue;
    if (normalize(canonValue) !== normalize(appValue)) {
      mismatches.push({ canon, app, canonValue, appValue });
    }
  }
  return mismatches;
}

describe("C 디자인 언어 캐논 토큰 정합 (이식 S1a 안전망)", () => {
  // ── 위생 메타테스트 — 검사기가 아무것도 스캔하지 않는데 통과하는 사태를 막는다 ──
  it("캐논 정본에서 토큰을 실제로 읽어냈다", () => {
    expect(canonTokens.size).toBeGreaterThan(25);
  });

  it("앱 .dark 블록에서 토큰을 실제로 읽어냈다", () => {
    expect(appDarkTokens.size).toBeGreaterThan(40);
  });

  it("매핑표가 캐논의 색·표면 토큰을 빠짐없이 덮는다", () => {
    const mapped = new Set(TOKEN_MAP.map(([canon]) => canon));
    const uncovered = [...canonTokens.keys()].filter((token) => {
      // 색·표면 토큰만 대상. 비색상 상수(NON_COLOR_TOKENS)는 아래 별도 검사가 값까지 대조한다.
      return !NON_COLOR_SET.has(token) && !mapped.has(token);
    });
    expect(uncovered, `매핑표에서 빠진 캐논 토큰: ${uncovered.join(", ")}`).toEqual([]);
  });

  it("비색상 캐논 상수가 앱 :root 값과 일치한다", () => {
    const mismatches = NON_COLOR_TOKENS.flatMap((token) => {
      const canonValue = canonTokens.get(token);
      const appValue = appRootTokens.get(token);
      if (canonValue === undefined) return [`${token}: 캐논 정본에 없음`];
      if (appValue === undefined) return [`${token}: 앱 :root 에 없음`];
      if (normalize(canonValue) !== normalize(appValue)) {
        return [`${token}: 캐논 ${canonValue} / 앱 ${appValue}`];
      }
      return [];
    });
    expect(
      mismatches,
      `캐논과 어긋난 비색상 상수:\n${mismatches.join("\n")}`,
    ).toEqual([]);
  });

  it("매핑표의 앱 토큰이 전부 .dark 에 실재한다", () => {
    const absent = TOKEN_MAP.filter(([, app]) => !appDarkTokens.has(app)).map(
      ([canon, app]) => `${canon} -> ${app}`,
    );
    expect(absent, `앱에 없는 토큰: ${absent.join(", ")}`).toEqual([]);
  });

  // ── 본 검사 ──
  it("allowlist 밖의 캐논 불일치가 없다", () => {
    const allowed = new Set(KNOWN_MISMATCHES.map((m) => m.canon));
    const unexpected = findMismatches().filter((m) => !allowed.has(m.canon));
    expect(
      unexpected,
      `캐논과 어긋난 토큰:\n${unexpected
        .map((m) => `  ${m.canon} -> ${m.app}  캐논 ${m.canonValue} / 앱 ${m.appValue}`)
        .join("\n")}`,
    ).toEqual([]);
  });

  // ── 래칫 — 고쳤으면 allowlist 도 줄여야 한다 ──
  it("allowlist 에 이미 해소된 항목이 남아 있지 않다", () => {
    const stillMismatched = new Set(findMismatches().map((m) => m.canon));
    const stale = KNOWN_MISMATCHES.filter((m) => !stillMismatched.has(m.canon)).map(
      (m) => m.canon,
    );
    expect(
      stale,
      `해소됐으니 KNOWN_MISMATCHES 에서 지워라: ${stale.join(", ")}`,
    ).toEqual([]);
  });
});
