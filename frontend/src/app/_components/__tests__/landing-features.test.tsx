// LandingFeatures (C 이식) — 6 기능 카드 + 섹션 헤더 + note 노출.
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { LandingFeatures } from "../landing-features";

describe("LandingFeatures", () => {
  afterEach(() => {
    cleanup();
  });

  it("section id=features + eyebrow 01", () => {
    const { container } = render(<LandingFeatures />);
    expect(container.querySelector("#features")).not.toBeNull();
    expect(container.querySelector(".eyebrow .num")?.textContent).toBe("01");
  });

  it("6개 기능 카드(.lp-feat) + 대표 타이틀 노출", () => {
    const { container } = render(<LandingFeatures />);
    expect(container.querySelectorAll(".lp-feat").length).toBe(6);
    expect(screen.getByText("Pine Script 파싱")).toBeInTheDocument();
    expect(screen.getByText("데모 트레이딩")).toBeInTheDocument();
    expect(screen.getByText("리스크 가드와 Kill Switch")).toBeInTheDocument();
  });

  it("Pine 전체 거부 정책 문구 노출 (ADR-003)", () => {
    render(<LandingFeatures />);
    expect(
      screen.getByText(/미지원 함수가 하나라도 있으면 전체를 지원되지 않음/),
    ).toBeInTheDocument();
  });
});
