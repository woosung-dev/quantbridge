// 목록 loading 스켈레톤은 최종 레이아웃 shape 를 따라야 한다 (스킬 §4.5) —
// 실화면(BacktestList)의 .page 헤더 카드 + 실행 목록 표 골격을 그리고,
// 목록 화면에 없는 KPI 그리드는 그리지 않는다.

import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import BacktestsLoading from "../loading";

describe("BacktestsLoading — C 골격 스켈레톤", () => {
  it(".page 래퍼 + 헤더 카드(.report) + 표 골격(.sk-cell)을 그린다", () => {
    const { container } = render(<BacktestsLoading />);
    const main = container.querySelector("main.page");
    expect(main).not.toBeNull();
    expect(main?.getAttribute("aria-busy")).toBe("true");
    expect(container.querySelector(".card .report")).not.toBeNull();
    expect(container.querySelectorAll(".report-meta .sk").length).toBeGreaterThan(0);
    expect(
      container.querySelectorAll("table.runs-table td .sk-cell").length,
    ).toBeGreaterThan(0);
  });

  it("실화면에 없는 KPI 그리드·구세대 컨테이너를 그리지 않는다", () => {
    const { container } = render(<BacktestsLoading />);
    expect(container.querySelector(".kpi-row")).toBeNull();
    expect(container.querySelector(".kpi")).toBeNull();
    // 구세대 shadcn 세대의 `container mx-auto` 래퍼 회귀 방지
    expect(container.querySelector(".container")).toBeNull();
  });
});
