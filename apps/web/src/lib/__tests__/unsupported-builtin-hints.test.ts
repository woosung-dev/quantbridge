// Sprint 21 BL-095 — unsupported builtin hint 변환 계약 테스트.

import { describe, expect, it } from "vitest";

import {
  getUnsupportedBuiltinHint,
  getUnsupportedBuiltinHints,
} from "@/lib/unsupported-builtin-hints";

const FALLBACK_MARKER = "— 미지원 빌트인";

function expectFallback(name: string): void {
  const hint = getUnsupportedBuiltinHint(name);

  expect(hint).toMatchObject({ name, category: "noop" });
  expect(hint.hint.startsWith(`${name} —`)).toBe(true);
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

function expectInheritedPrototypeLookup(name: string): void {
  const result = getUnsupportedBuiltinHint(name);

  expect(Object.keys(result)).toEqual(["name"]);
  expect(result.hint).toBeUndefined();
  expect(result.category).toBeUndefined();
}

describe("unsupported builtin hints", () => {
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

  // 이것은 결함이다 — 대상 무변경이 이 lane 의 계약이라 지금 동작을 고정만 한다.
  it.each(["toString", "__proto__", "constructor", "valueOf", "hasOwnProperty"])(
    "returns only the name for the inherited prototype property name %s",
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
