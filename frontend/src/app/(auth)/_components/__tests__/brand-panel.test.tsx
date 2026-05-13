// BrandPanel mode 분기 (sign-in vs sign-up heading) 검증
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { BrandPanel } from "../brand-panel";

describe("BrandPanel", () => {
  afterEach(() => {
    cleanup();
  });

  it("sign-in 모드 — 환영 카피 + Beta sub copy 노출 (Sprint 60 S2 BL-270)", () => {
    render(<BrandPanel mode="sign-in" />);
    expect(
      screen.getByRole("heading", { level: 1, name: /Pine Script 전략을/ }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/만드는 퀀트 트레이딩 플랫폼/),
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

  it("로고와 인용문 author 항상 표시 (Beta dogfooder, Sprint 60 S2 BL-271)", () => {
    render(<BrandPanel mode="sign-in" />);
    expect(screen.getByText("QuantBridge")).toBeInTheDocument();
    expect(
      screen.getByLabelText("QuantBridge 홈으로 이동"),
    ).toBeInTheDocument();
    expect(screen.getByText("초기 사용자")).toBeInTheDocument();
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

  it("live indicator + Beta 정직 표시 노출 (Sprint 60 S2 BL-270)", () => {
    render(<BrandPanel mode="sign-in" />);
    expect(screen.getByText(/초기 사용자와 함께 검증 중/)).toBeInTheDocument();
  });

  it("STATS grid — 4개 stat (Beta/Dev/Demo/Open 정직 표시, Sprint 60 S2 BL-270)", () => {
    render(<BrandPanel mode="sign-in" />);
    expect(screen.getByText("Beta")).toBeInTheDocument();
    expect(screen.getByText("Dev")).toBeInTheDocument();
    expect(screen.getByText("Demo")).toBeInTheDocument();
    expect(screen.getByText("Open")).toBeInTheDocument();
  });

  it("fadeInUp 애니메이션 class — 3 그룹 (logo / middle / testimonial)", () => {
    const { container } = render(<BrandPanel mode="sign-in" />);
    const html = container.innerHTML;
    expect(html).toContain("auth-fade-in-1");
    expect(html).toContain("auth-fade-in-2");
    expect(html).toContain("auth-fade-in-3");
  });
});
