// LandingPricing — 3 plan + Pro highlighted + sign-up CTA 검증
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { LandingPricing } from "../landing-pricing";

describe("LandingPricing", () => {
  afterEach(() => {
    cleanup();
  });

  it("section heading + id=pricing", () => {
    const { container } = render(<LandingPricing />);
    expect(
      screen.getByRole("heading", { level: 2, name: "심플한 요금제" }),
    ).toBeInTheDocument();
    expect(container.querySelector("#pricing")).not.toBeNull();
  });

  it("3 plan title + Pro 인기 배지", () => {
    render(<LandingPricing />);
    expect(
      screen.getByRole("heading", { level: 3, name: "Starter" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 3, name: "Pro" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 3, name: "Enterprise" }),
    ).toBeInTheDocument();
    expect(screen.getByText("인기")).toBeInTheDocument();
  });

  it("Starter 만 sign-up link 활성 / Pro·Enterprise 는 출시 예정 비활성", () => {
    render(<LandingPricing />);
    const starterCta = screen.getByRole("link", { name: "무료로 시작" });
    expect(starterCta).toHaveAttribute("href", "/sign-up");

    expect(screen.queryByRole("link", { name: /Pro 시작/ })).toBeNull();
    expect(screen.queryByRole("link", { name: /문의/ })).toBeNull();
    const placeholders = screen.getAllByText("출시 예정");
    expect(placeholders.length).toBe(2);
    for (const el of placeholders) {
      expect(el).toHaveAttribute("aria-disabled", "true");
    }
  });
});
