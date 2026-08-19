// LandingHowItWorks (C 이식) — 4 단계 카드 + section id=how.
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { LandingHowItWorks } from "../landing-how-it-works";

describe("LandingHowItWorks", () => {
  afterEach(() => {
    cleanup();
  });

  it("section id=how + 번호 아이브로우 없음 (BL-810)", () => {
    const { container } = render(<LandingHowItWorks />);
    expect(container.querySelector("#how")).not.toBeNull();
    expect(container.querySelector(".eyebrow .num")).toBeNull();
    expect(container.querySelector(".eyebrow")?.textContent).toBe("작동 방식");
  });

  it("4 단계 카드(.lp-step) — STEP 라벨 없음 (BL-810)", () => {
    const { container } = render(<LandingHowItWorks />);
    expect(container.querySelectorAll(".lp-step").length).toBe(4);
    expect(container.querySelector(".lp-step" + "-num")).toBeNull();
    expect(screen.queryByText(/^STEP /)).toBeNull();
    expect(screen.getByText("전략 등록")).toBeInTheDocument();
    expect(screen.getByText("데모 실행")).toBeInTheDocument();
  });
});
