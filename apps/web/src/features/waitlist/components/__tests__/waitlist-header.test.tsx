// WaitlistHeader — 로그인 이전 waitlist 화면의 브랜드·내부 링크·테마 토글 배선을 검증한다.

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

vi.mock("@/components/ui/theme-toggle", () => ({
  ThemeToggle: () => <button data-testid="theme-toggle">테마 전환</button>,
}));

import { WaitlistHeader } from "../waitlist-header";

describe("WaitlistHeader", () => {
  afterEach(() => {
    cleanup();
  });

  it("양성 대조 — 던지지 않고 비어 있지 않은 텍스트를 렌더한다", () => {
    const { container } = render(<WaitlistHeader />);

    expect(container.textContent?.trim()).not.toBe("");
  });

  it("브랜드 링크 — 앱 내부 경로를 가리킨다", () => {
    render(<WaitlistHeader />);

    const brandLink = screen.getByRole("link", { name: "QuantBridge 홈으로" });
    expect(brandLink).toHaveAttribute("href", "/");
    expect(brandLink.getAttribute("href")?.startsWith("/")).toBe(true);
  });

  it("시맨틱 — header landmark를 제공한다", () => {
    render(<WaitlistHeader />);

    expect(screen.getByRole("banner")).toBeInTheDocument();
  });

  it("ThemeToggle — 헤더에 배선된다", () => {
    render(<WaitlistHeader />);

    expect(screen.getByTestId("theme-toggle")).toBeInTheDocument();
  });

  it("링크 — 같은 href를 중복 렌더하지 않는다", () => {
    const { container } = render(<WaitlistHeader />);
    const hrefs = Array.from(container.querySelectorAll("a[href]"), (link) =>
      link.getAttribute("href"),
    );

    expect(new Set(hrefs).size).toBe(hrefs.length);
  });

  it("음성 대조 — 인증 전용 링크가 없다", () => {
    const { container } = render(<WaitlistHeader />);
    const hrefs = Array.from(container.querySelectorAll("a[href]"), (link) =>
      link.getAttribute("href"),
    );

    expect(hrefs).not.toContain("/dashboard");
    expect(hrefs).not.toContain("/logout");
    expect(screen.queryByRole("link", { name: /로그아웃|대시보드/ })).not.toBeInTheDocument();
  });
});
