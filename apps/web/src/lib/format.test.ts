import { describe, expect, it } from "vitest";

import { EMPTY_CELL } from "@/lib/labels";

import { formatDateTime } from "./format";

describe("formatDateTime", () => {
  it("UTC 로 YYYY-MM-DD HH:mm 을 찍는다", () => {
    expect(formatDateTime("2026-11-16T09:05:07Z")).toBe("2026-11-16 09:05");
    expect(formatDateTime("2026-11-16T09:05:07+09:00")).toBe("2026-11-16 00:05");
  });

  it("epoch ms 숫자를 받는다", () => {
    expect(formatDateTime(1_700_000_000_000)).toBe("2023-11-14 22:13");
  });

  it.each([null, undefined, "", "garbage", 0])("빈값·파싱 불가 %s → EMPTY_CELL", (v) => {
    expect(formatDateTime(v)).toBe(EMPTY_CELL);
  });
});
