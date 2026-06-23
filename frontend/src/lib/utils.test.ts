import { describe, expect, it } from "vitest";
import { cn, formatPercent } from "./utils";

describe("cn", () => {
  it("Tailwind 클래스 충돌을 해결한다", () => {
    expect(cn("px-2 py-1", "px-4")).toBe("py-1 px-4");
  });
});

describe("formatPercent", () => {
  it("양수에 + 부호", () => {
    expect(formatPercent(12.345)).toBe("+12.35%");
  });
  it("음수 그대로", () => {
    expect(formatPercent(-3.2)).toBe("-3.20%");
  });
});
