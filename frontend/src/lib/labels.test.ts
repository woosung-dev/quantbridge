// 용어 SSOT 공용 헬퍼(labelOf · statusLabelOf · orEmptyCell) 폴백 동작 검증.

import { afterEach, describe, expect, it, vi } from "vitest";

import {
  EMPTY_CELL,
  labelOf,
  orEmptyCell,
  statusLabelOf,
  type StatusLabelWithIcon,
} from "./labels";

const STATUS_TABLE: Record<"queued" | "done", StatusLabelWithIcon> = {
  queued: { label: "대기", tone: "neutral" },
  done: { label: "완료", tone: "done", showCheckIcon: true },
};

const STR_TABLE: Record<"buy" | "sell", string> = {
  buy: "매수",
  sell: "매도",
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe("statusLabelOf", () => {
  it("known key → 매핑된 라벨+톤", () => {
    expect(statusLabelOf(STATUS_TABLE, "done")).toEqual({
      label: "완료",
      tone: "done",
      showCheckIcon: true,
    });
  });

  it("미지 key → 원문 라벨 + neutral 톤 (성공·실패 색 오염 방지)", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    expect(statusLabelOf(STATUS_TABLE, "unknown_status", "test")).toEqual({
      label: "unknown_status",
      tone: "neutral",
    });
    expect(warn).toHaveBeenCalledOnce();
  });
});

describe("labelOf", () => {
  it("known key → 라벨", () => {
    expect(labelOf(STR_TABLE, "buy")).toBe("매수");
  });

  it("미지 key → 원문 반환 + 경고", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    expect(labelOf(STR_TABLE, "hold", "test")).toBe("hold");
    expect(warn).toHaveBeenCalledOnce();
  });
});

// BL-571 (c) — 폴백은 fail-loud 로 남기되, 폴링 재렌더마다 같은 경고가 다시 찍혀
// 콘솔을 덮는 것만 막는다(/trading 에서 40초에 67건).
describe("미지 key 경고 중복 차단", () => {
  it("같은 (scope, key) 반복 → 경고 1회", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    expect(labelOf(STR_TABLE, "flat", "dedupe")).toBe("flat");
    expect(labelOf(STR_TABLE, "flat", "dedupe")).toBe("flat");
    expect(labelOf(STR_TABLE, "flat", "dedupe")).toBe("flat");
    expect(warn).toHaveBeenCalledOnce();
  });

  it("key 나 scope 가 다르면 각각 경고 (fail-loud 유지)", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    labelOf(STR_TABLE, "close", "dedupe");
    statusLabelOf(STATUS_TABLE, "flat", "dedupe-other");
    expect(warn).toHaveBeenCalledTimes(2);
  });
});

describe("orEmptyCell", () => {
  it("null/undefined → EMPTY_CELL", () => {
    expect(orEmptyCell(null)).toBe(EMPTY_CELL);
    expect(orEmptyCell(undefined)).toBe(EMPTY_CELL);
  });

  it("값 존재 → 문자열화", () => {
    expect(orEmptyCell(0)).toBe("0");
    expect(orEmptyCell("x")).toBe("x");
  });
});
