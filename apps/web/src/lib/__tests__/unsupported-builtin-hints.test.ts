// Sprint 21 BL-095 — unsupported builtin hint 변환 계약 테스트.

import { describe, expect, it } from "vitest";

import {
  getUnsupportedBuiltinHint,
  getUnsupportedBuiltinHints,
} from "@/lib/unsupported-builtin-hints";

const FALLBACK_MARKER = "— 미지원 빌트인";
const VALID_CATEGORIES = ["corruption", "noop", "alternative"] as const;
const CATEGORY_REPRESENTATIVES = [
  ["heikinashi", "corruption"],
  ["barcolor", "noop"],
  ["ta.wma", "alternative"],
] as const;
const CORRUPTION_BUILTINS = [
  "heikinashi",
  "security",
  "request.security",
  "request.security_lower_tf",
] as const;
const KNOWN_CATALOG_BUILTINS = [
  "heikinashi",
  "security",
  "request.security",
  "request.security_lower_tf",
  "request.dividends",
  "timeframe.period",
  "barcolor",
  "array.new_float",
  "array.new_color",
  "matrix.new",
  "syminfo.ticker",
  "ta.alma",
  "ta.wma",
] as const;
const NON_EXACT_BUILTIN_NAMES = [
  "Heikinashi",
  "heikinashi ",
  "request.securit",
  "request.security2",
] as const;

function expectFallback(name: string): void {
  const hint = getUnsupportedBuiltinHint(name);

  expect(hint).toMatchObject({ name, category: "noop" });
  expect(hint.hint.startsWith(`${name} —`)).toBe(true);
  expect(hint.hint).toContain(FALLBACK_MARKER);
}

function expectMappedCategory(
  name: string,
  category: "corruption" | "noop" | "alternative",
): void {
  const hint = getUnsupportedBuiltinHint(name);

  expect(hint).toMatchObject({ name, category });
  expect(hint.hint).not.toContain(FALLBACK_MARKER);
  expect(hint.hint).not.toHaveLength(0);
}

// [BL-814] 종결 (2026-08-21) — 종전 이 헬퍼는 `{ name }` 만 나오는 **결함 동작을 고정**하고
// 있었다(`Object.prototype` 상속 키가 truthy 로 잡혀 hint·category 가 사라졌다).
// 수리 후에는 상속 키도 **일반 미적중과 똑같이 fallback** 을 받아야 한다.
function expectInheritedPrototypeLookup(name: string): void {
  expectFallback(name);
}

describe("unsupported builtin hints", () => {
  it.each(CATEGORY_REPRESENTATIVES)(
    "maps %s to the %s category",
    (name, category) => {
      expectMappedCategory(name, category);
    },
  );

  // Trust Layer: 이 네 호출은 조용한 데이터 오염 위험 때문에 unsupported로 남긴다.
  // noop으로 강등되면 사용자가 부정확한 backtest 결과를 신뢰하게 된다.
  it.each(CORRUPTION_BUILTINS)(
    "keeps %s in the corruption category",
    (name) => {
      expectMappedCategory(name, "corruption");
    },
  );

  it.each(KNOWN_CATALOG_BUILTINS)(
    "returns a non-fallback catalog hint for %s",
    (name) => {
      const hint = getUnsupportedBuiltinHint(name);

      expect(hint.hint).not.toHaveLength(0);
      expect(hint.hint).not.toContain(FALLBACK_MARKER);
      expect(VALID_CATEGORIES).toContain(hint.category);
      expect(hint.name).toBe(name);
    },
  );

  it.each(NON_EXACT_BUILTIN_NAMES)(
    "returns a fallback for the non-exact builtin name %s",
    (name) => {
      expectFallback(name);
    },
  );

  it("returns distinct hints for the category representatives", () => {
    const hints = CATEGORY_REPRESENTATIVES.map(([name]) =>
      getUnsupportedBuiltinHint(name).hint,
    );

    expect(new Set(hints)).toHaveLength(CATEGORY_REPRESENTATIVES.length);
  });

  it("returns the corruption hint with the caller-provided name", () => {
    expect(typeof getUnsupportedBuiltinHint).toBe("function");
    expect(typeof getUnsupportedBuiltinHints).toBe("function");

    expectMappedCategory("heikinashi", "corruption");
  });

  it("returns the noop hint for a supported catalog entry", () => {
    expectMappedCategory("barcolor", "noop");
  });

  it("returns the alternative hint for a supported catalog entry", () => {
    expectMappedCategory("ta.wma", "alternative");
  });

  it("returns a noop fallback for an unknown builtin", () => {
    expectFallback("currency.USDXYZ123");
  });

  // [BL-814] 수리 확인 — 상속 키도 일반 미적중과 같은 fallback 을 받는다.
  it.each(["toString", "__proto__", "constructor", "valueOf", "hasOwnProperty"])(
    "returns a fallback for the inherited prototype property name %s",
    (name) => {
      expectInheritedPrototypeLookup(name);
    },
  );

  it("returns a fallback for an empty name", () => {
    expectFallback("");
  });

  it("maps catalog hits and fallbacks in the supplied order", () => {
    const hints = getUnsupportedBuiltinHints(["heikinashi", "nope1"]);
    const [knownHint, unknownHint] = hints;

    expect(hints).toHaveLength(2);
    if (!knownHint || !unknownHint) {
      throw new Error("two input names must produce two hints");
    }
    expect(knownHint).toMatchObject({ name: "heikinashi", category: "corruption" });
    expect(knownHint.hint).not.toContain(FALLBACK_MARKER);
    expect(unknownHint).toMatchObject({ name: "nope1", category: "noop" });
    expect(unknownHint.hint.startsWith("nope1 —")).toBe(true);
  });

  it("ignores Array.map callback index and array arguments", () => {
    const hints = getUnsupportedBuiltinHints(["a", "b", "c"]);

    expect(hints.map((hint) => hint.name)).toEqual(["a", "b", "c"]);
    for (const hint of hints) {
      expect(hint.category).toBe("noop");
      expect(hint.hint.startsWith(`${hint.name} —`)).toBe(true);
    }
  });

  it("returns an empty list for no builtin names", () => {
    expect(getUnsupportedBuiltinHints([])).toEqual([]);
  });
});
