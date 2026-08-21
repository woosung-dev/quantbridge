// MetricTile 프리미티브 계약 — label/value/sub 렌더 + tone/size/variant 클래스 + testid.

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MetricTile } from "../metric-tile";

describe("MetricTile", () => {
  it("label/value/sub 를 렌더하고 valueTestId 를 값 요소에 부여", () => {
    render(<MetricTile label="총 거래" value="42" sub="지난 30일" valueTestId="stat-총 거래" />);
    expect(screen.getByText("총 거래")).toBeInTheDocument();
    expect(screen.getByTestId("stat-총 거래")).toHaveTextContent("42");
    expect(screen.getByText("지난 30일")).toBeInTheDocument();
  });

  it("tone=pos → bullish 토큰, tone=neg → bearish 토큰", () => {
    render(
      <>
        <MetricTile label="수익" value="+1" tone="pos" valueTestId="v-pos" />
        <MetricTile label="손실" value="-1" tone="neg" valueTestId="v-neg" />
      </>,
    );
    expect(screen.getByTestId("v-pos").className).toContain("text-bullish");
    expect(screen.getByTestId("v-neg").className).toContain("text-bearish");
  });

  it("variant=card 는 테두리 카드, bare 는 컨테이너 스타일 없음", () => {
    const { container } = render(
      <>
        <MetricTile label="a" value="1" className="probe-card" />
        <MetricTile label="b" value="2" variant="bare" className="probe-bare" />
      </>,
    );
    expect(container.querySelector(".probe-card")?.className).toContain("border");
    expect(container.querySelector(".probe-bare")?.className).not.toContain("bg-card");
  });
});
