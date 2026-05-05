import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AssumptionsCard } from "../assumptions-card";

describe("AssumptionsCard (Sprint 30-α)", () => {
  it("config 미제공 시 5개 가정 모두 default 표시 + 안내 문구", () => {
    render(<AssumptionsCard initialCapital={10000} />);
    // 초기 자본 (default 마크 없음)
    expect(screen.getByText("10,000 USDT")).toBeInTheDocument();
    // 4 가정 default
    expect(screen.getByText(/1x · 현물/)).toBeInTheDocument();
    expect(screen.getByText("0.10%")).toBeInTheDocument();
    expect(screen.getByText("0.050%")).toBeInTheDocument();
    expect(screen.getByText("ON")).toBeInTheDocument();
    // BE config 미응답 안내
    expect(
      screen.getByTestId("assumptions-default-notice"),
    ).toHaveTextContent(/표준 가정값/);
  });

  it("초기 자본은 천단위 콤마 + USDT 포맷 (소수점 없음)", () => {
    render(<AssumptionsCard initialCapital={50000} />);
    expect(screen.getByText("50,000 USDT")).toBeInTheDocument();
  });

  it("config.leverage=2 시 '2.0x' 표시 + (기본) 마크 없음", () => {
    render(
      <AssumptionsCard initialCapital={10000} config={{ leverage: 2 }} />,
    );
    expect(screen.getByText(/2\.0x/)).toBeInTheDocument();
    // 레버리지 dt 안에 (기본) 마크 없어야 함
    const leverageRow = screen.getByText("레버리지").parentElement;
    expect(leverageRow).not.toHaveTextContent("(기본)");
  });

  it("config 일부 set 시 graceful upgrade — 나머지는 default", () => {
    render(
      <AssumptionsCard
        initialCapital={10000}
        config={{ fees: 0.0006, slippage: null }}
      />,
    );
    // fees set → 0.06%
    expect(screen.getByText("0.06%")).toBeInTheDocument();
    // slippage null → default 0.050%
    expect(screen.getByText("0.050%")).toBeInTheDocument();
    // 일부만 default 이므로 안내 문구 없음
    expect(
      screen.queryByTestId("assumptions-default-notice"),
    ).not.toBeInTheDocument();
  });

  it("config.include_funding=false 시 OFF 표시", () => {
    render(
      <AssumptionsCard
        initialCapital={10000}
        config={{ include_funding: false }}
      />,
    );
    expect(screen.getByText("OFF")).toBeInTheDocument();
  });

  it("aria-label '백테스트 가정' a11y 적용", () => {
    render(<AssumptionsCard initialCapital={10000} />);
    expect(screen.getByLabelText("백테스트 가정")).toBeInTheDocument();
  });
});
