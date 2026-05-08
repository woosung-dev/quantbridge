// WaitlistHero — 가치제안 / Beta 통계 / 로그인 링크 노출 검증
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { WaitlistHero } from "../waitlist-hero";

describe("WaitlistHero", () => {
  afterEach(() => {
    cleanup();
  });

  it("h1 — 'Pine Script 전략을' + '실전 자동매매' 카피 노출", () => {
    render(<WaitlistHero />);
    const heading = screen.getByRole("heading", { level: 1 });
    expect(heading.textContent).toContain("Pine Script 전략을");
    expect(heading.textContent).toContain("실전 자동매매");
  });

  it("Beta · Invite Only 배지 + 3개 가치제안 + Beta 통계 3건 노출", () => {
    render(<WaitlistHero />);
    expect(screen.getByText(/Beta · Invite Only/)).toBeInTheDocument();
    expect(screen.getByText(/Pine Script 그대로 자동매매/)).toBeInTheDocument();
    expect(screen.getByText(/백테스트는 7초/)).toBeInTheDocument();
    expect(screen.getByText(/Beta 신청자에게만 공개/)).toBeInTheDocument();
    expect(screen.getByText("1-2주")).toBeInTheDocument();
    expect(screen.getByText("Bybit + OKX")).toBeInTheDocument();
  });

  it("로그인 링크 → /sign-in", () => {
    render(<WaitlistHero />);
    const link = screen.getByText("로그인").closest("a");
    expect(link).toHaveAttribute("href", "/sign-in");
  });
});
