// LandingFooter — 5 컬럼 헤더 + Legal 라우트 활성 + copyright 검증
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { LandingFooter } from "../landing-footer";

describe("LandingFooter", () => {
  afterEach(() => {
    cleanup();
  });

  it("Brand 로고 + 4개 컬럼 헤더 노출", () => {
    render(<LandingFooter />);
    expect(screen.getByText("QuantBridge")).toBeInTheDocument();

    for (const heading of ["Product", "Resources", "Company", "Legal"]) {
      expect(
        screen.getByRole("heading", { level: 3, name: heading }),
      ).toBeInTheDocument();
    }
  });

  it("Legal 컬럼 — terms/privacy/disclaimer 실제 라우트 링크", () => {
    render(<LandingFooter />);
    expect(screen.getByRole("link", { name: "이용약관" })).toHaveAttribute(
      "href",
      "/terms",
    );
    expect(
      screen.getByRole("link", { name: "개인정보처리방침" }),
    ).toHaveAttribute("href", "/privacy");
    expect(screen.getByRole("link", { name: "면책조항" })).toHaveAttribute(
      "href",
      "/disclaimer",
    );
  });

  it("Resources/Company 미존재 페이지는 비활성 (link 아님)", () => {
    render(<LandingFooter />);
    expect(screen.queryByRole("link", { name: /문서/ })).toBeNull();
    expect(screen.queryByRole("link", { name: /API 레퍼런스/ })).toBeNull();
    expect(screen.queryByRole("link", { name: /^소개/ })).toBeNull();
  });

  it("copyright + 면책 디스클레이머 노출", () => {
    render(<LandingFooter />);
    expect(screen.getByText(/© 2026 QuantBridge/)).toBeInTheDocument();
    expect(
      screen.getByText(/투자 자문이 아니며/),
    ).toBeInTheDocument();
  });
});
