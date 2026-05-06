/**
 * Sprint 37 BL-187a — AssumptionsCard graceful upgrade (수수료/슬리피지 만).
 *
 * 이전 (Sprint 31 BL-162a): leverage / fees / slippage / include_funding 4 필드.
 * 현재 (BL-187a): 사용자 명시로 leverage / 펀딩비 row 제거 → fees + slippage 만 노출.
 * BE 응답에는 leverage / include_funding 보존 (graceful upgrade 응답 호환).
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AssumptionsCard } from "../assumptions-card";

describe("AssumptionsCard — Sprint 37 BL-187a graceful upgrade (fees/slippage)", () => {
  it("사용자 입력 fees+slippage set 시 (기본) 마크 제거 + 실제값 표시", () => {
    render(
      <AssumptionsCard
        initialCapital={10000}
        config={{
          fees: 0.0006,
          slippage: 0.0002,
        }}
      />,
    );

    // 실제값 — Bybit 표준이 아닌 사용자 입력값
    expect(screen.getByText("0.06%")).toBeInTheDocument();
    expect(screen.getByText("0.020%")).toBeInTheDocument();

    // (기본) 마크 전부 제거 — graceful upgrade 완성
    expect(
      screen.queryByTestId("assumptions-default-notice"),
    ).not.toBeInTheDocument();

    // fees / slippage row 모두 (기본) 마크 없음
    const labels = ["수수료", "슬리피지"];
    labels.forEach((label) => {
      const row = screen.getByText(label).parentElement;
      expect(row).not.toHaveTextContent("(기본)");
    });
  });

  it("부분 set — fees set + slippage null = fees 만 graceful upgrade", () => {
    render(
      <AssumptionsCard
        initialCapital={10000}
        config={{
          fees: 0.0006,
          slippage: null,
        }}
      />,
    );

    // fees 실제값
    expect(screen.getByText("0.06%")).toBeInTheDocument();
    // slippage default
    expect(screen.getByText("0.050%")).toBeInTheDocument();

    // 일부만 default 이므로 전체 default 안내 문구 없음
    expect(
      screen.queryByTestId("assumptions-default-notice"),
    ).not.toBeInTheDocument();

    // fees row 만 (기본) 마크 없음
    const feesRow = screen.getByText("수수료").parentElement;
    expect(feesRow).not.toHaveTextContent("(기본)");
    // slippage row 는 (기본) 마크 유지
    const slipRow = screen.getByText("슬리피지").parentElement;
    expect(slipRow).toHaveTextContent("(기본)");
  });

  it("BL-187a 회귀 — leverage/include_funding 응답에 있어도 FE row 미렌더", () => {
    render(
      <AssumptionsCard
        initialCapital={50000}
        config={{
          leverage: 10,
          fees: 0.0008,
          slippage: 0.0001,
          include_funding: false,
        }}
      />,
    );

    // 사용자 입력값 — fees / slippage 만 노출
    expect(screen.getByText("0.08%")).toBeInTheDocument();
    expect(screen.getByText("0.010%")).toBeInTheDocument();
    expect(screen.getByText("50,000 USDT")).toBeInTheDocument();

    // BL-187a: leverage / 펀딩비 row 자체 미렌더
    expect(screen.queryByText("레버리지")).toBeNull();
    expect(screen.queryByText(/10\.0x/)).toBeNull();
    expect(screen.queryByText("펀딩비 반영")).toBeNull();
    expect(screen.queryByText("OFF")).toBeNull();

    // 안내 문구 없음 (fees+slippage set)
    expect(
      screen.queryByTestId("assumptions-default-notice"),
    ).not.toBeInTheDocument();
  });

  it("legacy fallback — config undefined 시 fees+slippage 모두 (기본) + 안내", () => {
    render(<AssumptionsCard initialCapital={10000} />);

    // 표준 가정값 안내
    expect(
      screen.getByTestId("assumptions-default-notice"),
    ).toHaveTextContent(/표준 가정값/);
    // fees + slippage row 모두 (기본) 마크
    const labels = ["수수료", "슬리피지"];
    labels.forEach((label) => {
      const row = screen.getByText(label).parentElement;
      expect(row).toHaveTextContent("(기본)");
    });
  });
});
