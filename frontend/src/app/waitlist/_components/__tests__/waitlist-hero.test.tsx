// WaitlistHero (C 이식) — 소개 카피 + 칩 + 사실 카드(미정 무데이터). AI-slop(OKX 지원·7초) 제거 검증.
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { WaitlistHero } from "../waitlist-hero";

describe("WaitlistHero", () => {
  afterEach(() => {
    cleanup();
  });

  it("h1 카피 + 엔진 / Bybit 칩", () => {
    render(<WaitlistHero />);
    const heading = screen.getByRole("heading", { level: 1 });
    expect(heading.textContent).toContain("TradingView Pine 전략을 백테스트");
    expect(screen.getByText("바 단위 이벤트 루프 자체 인터프리터")).toBeInTheDocument();
    expect(screen.getByText("Bybit 데모 · 메인넷")).toBeInTheDocument();
  });

  it("사실 카드 — 공개 시점/가격 미정(무데이터 + title)", () => {
    const { container } = render(<WaitlistHero />);
    const dims = container.querySelectorAll(".trust-val.dim");
    expect(dims.length).toBe(2);
    dims.forEach((el) => expect(el.textContent).toBe("미정"));
  });

  it("AI-slop 제거 — OKX 지원/7초 속도/가짜 배지 없음", () => {
    render(<WaitlistHero />);
    expect(screen.queryByText(/OKX/)).not.toBeInTheDocument();
    expect(screen.queryByText(/7초/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Invite Only/)).not.toBeInTheDocument();
  });
});
