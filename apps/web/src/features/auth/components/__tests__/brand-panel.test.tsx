// BrandPanel (C 이식) — 확인 가능한 사실 4가지 좌 패널. 가공 인물·후기·가짜 라이브 점 제거 검증.
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { BrandPanel } from "../brand-panel";

describe("BrandPanel", () => {
  afterEach(() => {
    cleanup();
  });

  it("auth-h1 카피 + eyebrow 01 확인 가능한 사실", () => {
    const { container } = render(<BrandPanel />);
    expect(
      screen.getByRole("heading", {
        level: 1,
        name: /Pine Script 전략을 검증하고/,
      }),
    ).toBeInTheDocument();
    expect(container.querySelector(".eyebrow .num")?.textContent).toBe("01");
  });

  it("사실 4가지(.fact) + pine_v2 정책 문구", () => {
    const { container } = render(<BrandPanel />);
    expect(container.querySelectorAll(".fact").length).toBe(4);
    const idx = Array.from(container.querySelectorAll(".fact-idx")).map((el) => el.textContent);
    expect(idx).toEqual(["01", "02", "03", "04"]);
    expect(screen.getByText(/자체 인터프리터입니다/)).toBeInTheDocument();
  });

  it("거짓 카피 없음 — 소셜 로그인은 배선이 없으므로 언급하지 않는다", () => {
    const { container } = render(<BrandPanel />);
    expect(container.textContent).not.toContain("소셜");
    expect(container.textContent).not.toContain("Google");
    expect(container.textContent).not.toContain("GitHub");
  });

  it("AI-slop 제거 — 아바타 군집·후기·가짜 라이브 점 없음", () => {
    const { container } = render(<BrandPanel />);
    expect(screen.queryByTestId("brand-avatars")).not.toBeInTheDocument();
    expect(screen.queryByText("초기 사용자")).not.toBeInTheDocument();
    expect(container.querySelector("[class*='pulse']")).toBeNull();
    expect(container.querySelector("blockquote")).toBeNull();
  });
});
