import { describe, expect, it } from "vitest";
import { cn } from "./utils";

describe("cn", () => {
  it("Tailwind 클래스 충돌을 해결한다", () => {
    expect(cn("px-2 py-1", "px-4")).toBe("py-1 px-4");
  });
});
