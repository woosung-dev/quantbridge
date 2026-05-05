/**
 * Sprint 31 BL-162a — AssumptionsCard graceful upgrade 검증.
 *
 * 사용자가 BacktestForm 에서 비용/마진을 입력하면 BE 가 그 값을 그대로 응답.
 * → AssumptionsCard 가 (기본) 마크 자동 제거 + 실제값 표시.
 * legacy (BE config 미응답 / null) 시 default fallback 유지 (Sprint 30-α).
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AssumptionsCard } from "../assumptions-card";

describe("AssumptionsCard — Sprint 31 graceful upgrade", () => {
  it("사용자 입력 4 필드 모두 set 시 (기본) 마크 전부 제거 + 실제값 표시", () => {
    render(
      <AssumptionsCard
        initialCapital={10000}
        config={{
          leverage: 10,
          fees: 0.0006,
          slippage: 0.0002,
          include_funding: false,
        }}
      />,
    );

    // 실제값 — Bybit 표준이 아닌 사용자 입력값
    expect(screen.getByText(/10\.0x/)).toBeInTheDocument();
    expect(screen.getByText("0.06%")).toBeInTheDocument();
    expect(screen.getByText("0.020%")).toBeInTheDocument();
    expect(screen.getByText("OFF")).toBeInTheDocument();

    // (기본) 마크 전부 제거 — graceful upgrade 완성
    expect(
      screen.queryByTestId("assumptions-default-notice"),
    ).not.toBeInTheDocument();
    // 4 가정 row 어디에도 (기본) text 없음
    const rows = screen.getAllByText(/레버리지|수수료|슬리피지|펀딩비 반영/);
    rows.forEach((row) => {
      const parent = row.parentElement;
      expect(parent).not.toHaveTextContent("(기본)");
    });
  });

  it("부분 set — leverage=2 + 나머지 null = leverage 만 graceful upgrade", () => {
    render(
      <AssumptionsCard
        initialCapital={10000}
        config={{
          leverage: 2,
          fees: null,
          slippage: null,
          include_funding: null,
        }}
      />,
    );

    // leverage 실제값
    expect(screen.getByText(/2\.0x/)).toBeInTheDocument();
    // 나머지 default
    expect(screen.getByText("0.10%")).toBeInTheDocument();
    expect(screen.getByText("0.050%")).toBeInTheDocument();
    expect(screen.getByText("ON")).toBeInTheDocument();

    // 일부만 default 이므로 전체 default 안내 문구 없음
    expect(
      screen.queryByTestId("assumptions-default-notice"),
    ).not.toBeInTheDocument();

    // leverage row 만 (기본) 마크 없음
    const leverageRow = screen.getByText("레버리지").parentElement;
    expect(leverageRow).not.toHaveTextContent("(기본)");
    // fees row 는 (기본) 마크 유지
    const feesRow = screen.getByText("수수료").parentElement;
    expect(feesRow).toHaveTextContent("(기본)");
  });

  it("BL-162a payload — config={leverage:5, fees:0.0008, slippage:0.0001, include_funding:true} 정합", () => {
    render(
      <AssumptionsCard
        initialCapital={50000}
        config={{
          leverage: 5,
          fees: 0.0008,
          slippage: 0.0001,
          include_funding: true,
        }}
      />,
    );

    // 사용자 입력값 그대로 노출 (graceful upgrade)
    expect(screen.getByText(/5\.0x/)).toBeInTheDocument();
    expect(screen.getByText("0.08%")).toBeInTheDocument();
    expect(screen.getByText("0.010%")).toBeInTheDocument();
    expect(screen.getByText("ON")).toBeInTheDocument();
    expect(screen.getByText("50,000 USDT")).toBeInTheDocument();
    // 안내 문구 없음
    expect(
      screen.queryByTestId("assumptions-default-notice"),
    ).not.toBeInTheDocument();
  });

  it("legacy fallback — config undefined 시 4 가정 모두 (기본) + 안내 문구", () => {
    render(<AssumptionsCard initialCapital={10000} />);

    // 표준 가정값 안내
    expect(
      screen.getByTestId("assumptions-default-notice"),
    ).toHaveTextContent(/표준 가정값/);
    // 4 row 모두 (기본) 마크
    const labels = ["레버리지", "수수료", "슬리피지", "펀딩비 반영"];
    labels.forEach((label) => {
      const row = screen.getByText(label).parentElement;
      expect(row).toHaveTextContent("(기본)");
    });
  });
});
