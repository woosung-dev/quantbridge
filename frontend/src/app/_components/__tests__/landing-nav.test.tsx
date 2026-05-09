// LandingNav — 로고/메뉴/CTA + 모바일 햄버거 토글 검증
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { LandingNav } from "../landing-nav";

describe("LandingNav", () => {
  afterEach(() => {
    cleanup();
    document.body.style.overflow = "";
  });

  it("로고 + 데스크톱 앵커 메뉴 + 로그인/CTA 링크 노출", () => {
    render(<LandingNav />);
    expect(
      screen.getAllByText("QuantBridge").length,
    ).toBeGreaterThanOrEqual(1);

    const featuresLinks = screen.getAllByRole("link", { name: "기능" });
    expect(featuresLinks.length).toBeGreaterThanOrEqual(1);
    expect(featuresLinks[0]).toHaveAttribute("href", "#features");

    const howLinks = screen.getAllByRole("link", { name: "사용법" });
    expect(howLinks[0]).toHaveAttribute("href", "#how-it-works");

    const pricingLinks = screen.getAllByRole("link", { name: "요금제" });
    expect(pricingLinks[0]).toHaveAttribute("href", "#pricing");

    const faqLinks = screen.getAllByRole("link", { name: "FAQ" });
    expect(faqLinks[0]).toHaveAttribute("href", "#faq");

    const signIn = screen.getAllByRole("link", { name: "로그인" })[0];
    expect(signIn).toHaveAttribute("href", "/sign-in");

    const signUp = screen.getAllByRole("link", { name: "무료로 시작하기" })[0];
    expect(signUp).toHaveAttribute("href", "/sign-up");
  });

  it("햄버거 클릭 시 모바일 메뉴 dialog open + 닫기 버튼으로 close", () => {
    render(<LandingNav />);
    const hamburger = screen.getByRole("button", { name: "메뉴 열기" });
    expect(hamburger).toHaveAttribute("aria-expanded", "false");

    fireEvent.click(hamburger);
    expect(screen.getByRole("dialog", { name: "모바일 메뉴" })).toBeInTheDocument();

    const closeBtn = screen.getByRole("button", { name: "메뉴 닫기" });
    fireEvent.click(closeBtn);
    expect(screen.queryByRole("dialog", { name: "모바일 메뉴" })).not.toBeInTheDocument();
  });
});
