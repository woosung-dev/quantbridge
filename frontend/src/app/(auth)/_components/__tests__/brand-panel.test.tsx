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

  it("avatars row — prototype 04 의 5 사용자 (JK/MH/YS/DW/SJ) initials 노출", () => {
    render(<BrandPanel mode="sign-in" />);
    const avatars = screen.getByTestId("brand-avatars");
    expect(avatars).toBeInTheDocument();
    // 5명의 initials 자식 텍스트 검증
    expect(avatars.textContent).toContain("JK");
    expect(avatars.textContent).toContain("MH");
    expect(avatars.textContent).toContain("YS");
    expect(avatars.textContent).toContain("DW");
    expect(avatars.textContent).toContain("SJ");
  });

  it("live indicator + 7,234명 dynamic count 노출", () => {
    render(<BrandPanel mode="sign-in" />);
    expect(screen.getByText(/7,234명/)).toBeInTheDocument();
    expect(screen.getByText(/실전 매매 중/)).toBeInTheDocument();
  });

  it("STATS grid — 4개 stat (업타임 / 체결 / 거래소 / 거래량) 노출", () => {
    render(<BrandPanel mode="sign-in" />);
    expect(screen.getByText("99.97%")).toBeInTheDocument();
    expect(screen.getByText("<35ms")).toBeInTheDocument();
    expect(screen.getByText("거래소")).toBeInTheDocument();
    expect(screen.getByText("2.4B")).toBeInTheDocument();
  });

  it("fadeInUp 애니메이션 class — 3 그룹 (logo / middle / testimonial)", () => {
    const { container } = render(<BrandPanel mode="sign-in" />);
    const html = container.innerHTML;
    expect(html).toContain("auth-fade-in-1");
    expect(html).toContain("auth-fade-in-2");
    expect(html).toContain("auth-fade-in-3");
  });
});
