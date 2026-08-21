// 레인 S4 — 필터 칩 관용구 검증 (① pill 반경 폐기 → 태그 반경 / ⑤ 장식 색 점 제거).

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { WaitlistFilterBar } from "../waitlist-filter-bar";

describe("WaitlistFilterBar", () => {
  it("필터 칩 — 태그 반경(radius-sm)을 쓰고 rounded-full 이 없다", () => {
    render(
      <WaitlistFilterBar
        status="pending"
        search=""
        onStatusChange={() => {}}
        onSearchChange={() => {}}
      />,
    );
    const chips = screen.getAllByRole("button");
    expect(chips).toHaveLength(5);
    expect(screen.getByRole("button", { name: "대기중" })).toHaveAttribute("aria-pressed", "true");
    for (const chip of chips) {
      expect(chip.className).toContain("rounded-[var(--radius-sm)]");
      expect(chip.className).not.toContain("rounded-full");
      // ⑤ 라벨이 이미 상태를 말한다 — 장식 색 점(span) 없음.
      expect(chip.querySelector("span[style]")).toBeNull();
    }
  });
});
