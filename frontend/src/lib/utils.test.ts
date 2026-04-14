import { describe, expect, it } from "vitest";
import { cn, formatDecimal, formatPercent } from "./utils";

describe("cn", () => {
  it("Tailwind 클래스 충돌을 해결한다", () => {
    expect(cn("px-2 py-1", "px-4")).toBe("py-1 px-4");
  });
});

describe("formatDecimal", () => {
  it("기본 2자리로 포맷팅", () => {
    expect(formatDecimal(1234.567)).toBe("1,234.57");
  });
  it("양수에 부호를 붙일 수 있다", () => {
    expect(formatDecimal(1.5, { sign: true })).toBe("+1.50");
  });
  it("숫자가 아니면 '-' 반환", () => {
    expect(formatDecimal(Number.NaN)).toBe("-");
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
