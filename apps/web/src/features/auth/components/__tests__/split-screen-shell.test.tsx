// SplitScreenShell (C 이식) — 자체 헤더/2분할/푸터 + 좌 BrandPanel + 우 form-col(모드 제목) + 폼 children.
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { SplitScreenShell } from "../split-screen-shell";

describe("SplitScreenShell", () => {
  afterEach(() => {
    cleanup();
  });

  it("자체 헤더 로고 → / + 좌 BrandPanel + 우 form-col + children 이 auth-form-slot 안", () => {
    const { container } = render(
      <SplitScreenShell mode="sign-in">
        <div data-testid="form-child">form</div>
      </SplitScreenShell>,
    );
    expect(container.querySelector(".auth-top .auth-logo")).not.toBeNull();
    // 좌 패널
    expect(container.querySelector(".auth-brand")).not.toBeNull();
    // children 이 .auth-form-slot 카드 안에 렌더
    const child = screen.getByTestId("form-child");
    expect(child.closest(".auth-form-slot")).not.toBeNull();
  });

  it("sign-in 모드 — form-col 제목 로그인", () => {
    render(
      <SplitScreenShell mode="sign-in">
        <div>x</div>
      </SplitScreenShell>,
    );
    expect(
      screen.getByRole("heading", { level: 2, name: "로그인" }),
    ).toBeInTheDocument();
  });

  it("sign-up 모드 — form-col 제목 회원가입", () => {
    render(
      <SplitScreenShell mode="sign-up">
        <div>x</div>
      </SplitScreenShell>,
    );
    expect(
      screen.getByRole("heading", { level: 2, name: "회원가입" }),
    ).toBeInTheDocument();
  });

  it("거짓 카피 없음 — 소셜(Google·GitHub) 로그인은 배선이 없으므로 언급하지 않는다", () => {
    const { container } = render(
      <SplitScreenShell mode="sign-in">
        <div>x</div>
      </SplitScreenShell>,
    );
    expect(container.textContent).not.toContain("소셜");
    expect(container.textContent).not.toContain("Google");
    expect(container.textContent).not.toContain("GitHub");
  });

  it("sign-in 모드 — 우상단에 회원가입 상호 링크 → /sign-up", () => {
    render(
      <SplitScreenShell mode="sign-in">
        <div>x</div>
      </SplitScreenShell>,
    );
    expect(screen.getByRole("link", { name: "회원가입" })).toHaveAttribute(
      "href",
      "/sign-up",
    );
  });

  it("sign-up 모드 — 우상단에 로그인 상호 링크 → /sign-in", () => {
    render(
      <SplitScreenShell mode="sign-up">
        <div>x</div>
      </SplitScreenShell>,
    );
    expect(screen.getByRole("link", { name: "로그인" })).toHaveAttribute(
      "href",
      "/sign-in",
    );
  });

  it("자체 푸터 노출 (계정 관리 주체 명시)", () => {
    const { container } = render(
      <SplitScreenShell mode="sign-in">
        <div>x</div>
      </SplitScreenShell>,
    );
    const foot = container.querySelector("footer.auth-foot");
    expect(foot?.textContent).toContain("계정은 QuantBridge 가 직접 관리합니다");
  });
});
