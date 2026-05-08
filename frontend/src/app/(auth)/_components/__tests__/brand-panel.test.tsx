// BrandPanel mode 분기 (sign-in vs sign-up heading) 검증
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { BrandPanel } from "../brand-panel";

describe("BrandPanel", () => {
  afterEach(() => {
    cleanup();
  });

  it("sign-in 모드 — 환영 카피 + sub copy 노출", () => {
    render(<BrandPanel mode="sign-in" />);
    expect(
      screen.getByRole("heading", { level: 1, name: /Pine Script 전략을/ }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/10,000\+ 트레이더가 선택한/),
    ).toBeInTheDocument();
  });

  it("sign-up 모드 — 가입 카피 + 무료 데모 sub copy 노출", () => {
    render(<BrandPanel mode="sign-up" />);
    expect(
      screen.getByRole("heading", { level: 1, name: /지금 시작하세요/ }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Bybit Demo 환경에서 전략을 검증/),
    ).toBeInTheDocument();
  });

  it("로고와 인용문 author 항상 표시", () => {
    render(<BrandPanel mode="sign-in" />);
    expect(screen.getByText("QuantBridge")).toBeInTheDocument();
    expect(
      screen.getByLabelText("QuantBridge 홈으로 이동"),
    ).toBeInTheDocument();
    expect(screen.getByText("김지훈")).toBeInTheDocument();
  });
});
