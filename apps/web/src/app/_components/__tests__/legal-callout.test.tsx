// LegalCallout — Sprint 43 W14 amber/info tone + label 분기 검증.

import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { LegalCallout } from "../legal-callout";

afterEach(() => {
  cleanup();
});

describe("LegalCallout", () => {
  it("default tone=amber + label + body 렌더", () => {
    render(
      <LegalCallout label="[법무 임시 — 법적 효력 제한적]">
        본 방침은 H2 Beta 단계 임시 템플릿입니다.
      </LegalCallout>,
    );

    const box = screen.getByTestId("legal-callout");
    expect(box).toHaveAttribute("data-tone", "amber");
    expect(box).toHaveAttribute("role", "note");
    expect(screen.getByText("[법무 임시 — 법적 효력 제한적]")).toBeInTheDocument();
    expect(box).toHaveTextContent("본 방침은 H2 Beta 단계 임시 템플릿입니다.");
  });

  it("tone=info + label 미지정 시 strong 라벨 미렌더", () => {
    render(
      <LegalCallout tone="info">
        <span>info body</span>
      </LegalCallout>,
    );

    const box = screen.getByTestId("legal-callout");
    expect(box).toHaveAttribute("data-tone", "info");
    expect(box.querySelector("strong")).toBeNull();
    expect(screen.getByText("info body")).toBeInTheDocument();
  });
});
