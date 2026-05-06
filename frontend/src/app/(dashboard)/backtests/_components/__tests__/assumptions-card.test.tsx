import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AssumptionsCard } from "../assumptions-card";

describe("AssumptionsCard (Sprint 37 BL-187a — 라벨 simplify + 레버리지/펀딩 row 제거)", () => {
  it("config 미제공 시 가정 default 표시 + 안내 문구 (수수료/슬리피지 만)", () => {
    render(<AssumptionsCard initialCapital={10000} />);
    // 초기 자본 (default 마크 없음)
    expect(screen.getByText("10,000 USDT")).toBeInTheDocument();
    // 포지션 모델 = "1x · 롱/숏" (BL-187a)
    expect(screen.getByText("1x · 롱/숏")).toBeInTheDocument();
    // 수수료/슬리피지 default
    expect(screen.getByText("0.10%")).toBeInTheDocument();
    expect(screen.getByText("0.050%")).toBeInTheDocument();
    // BL-187a: 레버리지 / 펀딩비 row 제거
    expect(screen.queryByText("레버리지")).toBeNull();
    expect(screen.queryByText("펀딩비 반영")).toBeNull();
    // BE config 미응답 안내 (수수료 + 슬리피지 둘 다 default)
    expect(
      screen.getByTestId("assumptions-default-notice"),
    ).toHaveTextContent(/표준 가정값/);
  });

  it("초기 자본은 천단위 콤마 + USDT 포맷 (소수점 없음)", () => {
    render(<AssumptionsCard initialCapital={50000} />);
    expect(screen.getByText("50,000 USDT")).toBeInTheDocument();
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

  it("aria-label '백테스트 가정' a11y 적용", () => {
    render(<AssumptionsCard initialCapital={10000} />);
    expect(screen.getByLabelText("백테스트 가정")).toBeInTheDocument();
  });

  // Sprint 37 BL-185 → BL-187a — 라벨 "Spot-equivalent" → "1x · 롱/숏".
  // 사용자 명시: "Spot" 단어 오해 회피 (롱/숏 모두 가능 명시).
  it("BL-187a: '포지션 모델' = '1x · 롱/숏' visible row", () => {
    render(<AssumptionsCard initialCapital={10000} />);
    expect(screen.getByText("포지션 모델")).toBeInTheDocument();
    expect(screen.getByText("1x · 롱/숏")).toBeInTheDocument();
    // 이전 라벨 "Spot-equivalent" 제거 검증
    expect(screen.queryByText("Spot-equivalent")).toBeNull();
  });

  it("BL-187a: '포지션 모델' tooltip 에 롱/숏 명시 + BL-186 후속 안내", () => {
    render(<AssumptionsCard initialCapital={10000} />);
    const modelDt = screen.getByText("포지션 모델").parentElement;
    // tooltip = title attribute
    expect(modelDt?.title ?? "").toMatch(/롱\s*\/\s*숏|롱과 숏/i);
    expect(modelDt?.title ?? "").toMatch(/BL-186|미반영|후속/i);
  });

  it("BL-187a: 레버리지 / 펀딩비 row 완전 제거 (사용자 명시)", () => {
    render(
      <AssumptionsCard
        initialCapital={10000}
        config={{ leverage: 5, include_funding: false }}
      />,
    );
    // config 에 명시되어도 row 자체 미렌더 (BL-187a)
    expect(screen.queryByText("레버리지")).toBeNull();
    expect(screen.queryByText("펀딩비 반영")).toBeNull();
    expect(screen.queryByText(/5\.0x/)).toBeNull();
    expect(screen.queryByText("OFF")).toBeNull();
  });
});
