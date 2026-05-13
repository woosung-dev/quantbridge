// LandingHero — 핵심 카피 / CTA / 신뢰 카운트 노출 검증
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { LandingHero } from "../landing-hero";

describe("LandingHero", () => {
  afterEach(() => {
    cleanup();
  });

  it("h1 — Pine Script 카피 + 자동 트레이딩 underline 노출", () => {
    render(<LandingHero />);
    const heading = screen.getByRole("heading", { level: 1 });
    expect(heading).toBeInTheDocument();
    expect(heading.textContent).toContain("Pine Script 전략을");
    expect(heading.textContent).toContain("자동 트레이딩으로");
  });

  it("v2.0 출시 pill + Beta 정직 표시 노출 (Sprint 60 S2 BL-270)", () => {
    render(<LandingHero />);
    expect(
      screen.getByText(/v2\.0 출시 — Monte Carlo/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Beta · 초기 dogfooder · feedback 환영/),
    ).toBeInTheDocument();
  });

  it("CTA 2개 — 무료로 시작하기 → /sign-up (Sprint 60 S3 BL-260) / 라이브 데모 → /sign-in", () => {
    render(<LandingHero />);
    const primary = screen.getByText(/무료로 시작하기/).closest("a");
    expect(primary).toHaveAttribute("href", "/sign-up");
    const secondary = screen.getByText(/라이브 데모/).closest("a");
    expect(secondary).toHaveAttribute("href", "/sign-in");
  });
});
