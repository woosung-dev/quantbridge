// LandingFooter (C 이식) — 개인 프로젝트 표기 + 앵커 링크 4종.
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { LandingFooter } from "../landing-footer";

describe("LandingFooter", () => {
  afterEach(() => {
    cleanup();
  });

  it("개인 프로젝트 표기 + 워크스페이스 표기", () => {
    render(<LandingFooter />);
    expect(screen.getByText("2026 QuantBridge. 개인 프로젝트입니다.")).toBeInTheDocument();
    expect(screen.getByText("woosung · 로컬 워크스페이스")).toBeInTheDocument();
  });

  it("앵커 링크 4종(.lp-foot-links)", () => {
    const { container } = render(<LandingFooter />);
    const links = container.querySelectorAll(".lp-foot-links a");
    expect(links.length).toBe(4);
    expect(container.querySelector('.lp-foot-links a[href="#support"]')).not.toBeNull();
  });
});
