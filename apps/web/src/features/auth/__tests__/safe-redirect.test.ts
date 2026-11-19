import { describe, expect, it } from "vitest";

import { safeRedirectPath } from "../safe-redirect";

const FALLBACK = "/strategies";

describe("safeRedirectPath", () => {
  it.each([
    ["/strategies/abc?tab=1#x", "/strategies/abc?tab=1#x"],
    ["/backtests", "/backtests"],
  ])("keeps in-app path %s", (raw, expected) => {
    expect(safeRedirectPath(raw, FALLBACK)).toBe(expected);
  });

  // 종전 접두 검사를 통과하던 외부 이동 — 보안 감사 2026-11-19.
  it.each([
    "/\\evil.example",
    "/\t/evil.example",
    "/\n/evil.example",
    "//evil.example",
    "https://evil.example",
    "javascript:alert(1)",
    "",
    undefined,
  ])("falls back for %j", (raw) => {
    expect(safeRedirectPath(raw, FALLBACK)).toBe(FALLBACK);
  });
});
