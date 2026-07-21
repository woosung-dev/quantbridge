// LandingNav (C 이식) — 마케팅 헤더 브랜드 + 앵커 메뉴 + 로그인/시작 링크 + 햄버거 토글.
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { LandingNav } from "../landing-nav";

describe("LandingNav", () => {
  afterEach(() => {
    cleanup();
  });

  it("브랜드 + 앵커 메뉴(#features/#how/#support/#faq) + 로그인/시작 CTA", () => {
    const { container } = render(<LandingNav />);
    expect(screen.getAllByText("QuantBridge").length).toBeGreaterThanOrEqual(1);

    const nav = container.querySelector("nav.lp-nav");
    expect(nav).not.toBeNull();
    expect(nav?.querySelector('a[href="#features"]')).not.toBeNull();
    expect(nav?.querySelector('a[href="#how"]')).not.toBeNull();
    expect(nav?.querySelector('a[href="#support"]')).not.toBeNull();
    expect(nav?.querySelector('a[href="#faq"]')).not.toBeNull();

    const login = screen.getAllByRole("link", { name: "로그인" })[0];
    expect(login).toHaveAttribute("href", "/sign-in");
    const start = screen.getByRole("link", { name: "시작하기" });
    expect(start).toHaveAttribute("href", "/sign-up");
  });

  it("햄버거 클릭 시 lp-nav 가 open 되고 aria-expanded 토글", () => {
    const { container } = render(<LandingNav />);
    const burger = screen.getByRole("button", { name: "메뉴 열기" });
    expect(burger).toHaveAttribute("aria-expanded", "false");

    fireEvent.click(burger);
    expect(container.querySelector("nav.lp-nav.open")).not.toBeNull();
    expect(screen.getByRole("button", { name: "메뉴 닫기" })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
  });

  it("전역 카퍼 :focus-visible 소비 — outline:none 하드코딩 없음", () => {
    const { container } = render(<LandingNav />);
    const outlineNone = Array.from(container.querySelectorAll("*")).filter(
      (el) => (el as HTMLElement).style?.outline === "none",
    );
    expect(outlineNone.length).toBe(0);
  });
});
