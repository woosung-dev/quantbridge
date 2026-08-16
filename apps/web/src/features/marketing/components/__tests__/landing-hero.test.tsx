// LandingHero (C 이식) — 히어로 카피 + 시작 CTA + 화면 예시 목업 + 샘플 disclaimer.
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { LandingHero } from "../landing-hero";

describe("LandingHero", () => {
  afterEach(() => {
    cleanup();
  });

  it("h1 — TradingView 전략 검증 카피 + 로컬 도구/공개 전 칩", () => {
    const { container } = render(<LandingHero />);
    const heading = screen.getByRole("heading", { level: 1 });
    expect(heading.textContent).toContain("TradingView 전략을");
    expect(heading.textContent).toContain("검증합니다");
    expect(container.querySelector(".lp-hero-meta .chip")).not.toBeNull();
    expect(screen.getByText("로컬 도구")).toBeInTheDocument();
    expect(screen.getByText("공개 전")).toBeInTheDocument();
  });

  it("CTA — 시작하기 → /sign-up · 지원 현황 확인 → #support", () => {
    render(<LandingHero />);
    expect(screen.getByRole("link", { name: "시작하기" })).toHaveAttribute("href", "/sign-up");
    expect(screen.getByRole("link", { name: "지원 현황 확인" })).toHaveAttribute(
      "href",
      "#support",
    );
  });

  it("화면 예시 목업 — 라벨 칩 + 무데이터 아닌 샘플 stat + 프로토타입 disclaimer", () => {
    const { container } = render(<LandingHero />);
    expect(screen.getByText("화면 예시")).toBeInTheDocument();
    expect(container.querySelectorAll(".mock-stat").length).toBe(3);
    expect(screen.getByText(/프로토타입용 샘플 데이터입니다/)).toBeInTheDocument();
  });

  it("가짜 라이브 신호·가공 인물 없음 — pulse/avatar 클래스 미사용", () => {
    const { container } = render(<LandingHero />);
    expect(container.querySelector("[class*='avatar']")).toBeNull();
    expect(container.querySelector("[class*='pulse']")).toBeNull();
  });
});
