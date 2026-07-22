// Clerk SignIn/SignUp 에 전달되는 C 디자인 언어 appearance prop 검증 (공유 clerk-appearance.ts).
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render } from "@testing-library/react";

const captured = vi.hoisted(() => ({
  signInProps: null as Record<string, unknown> | null,
  signUpProps: null as Record<string, unknown> | null,
}));

vi.mock("@clerk/nextjs", () => ({
  SignIn: (props: Record<string, unknown>) => {
    captured.signInProps = props;
    return <div data-testid="clerk-sign-in" />;
  },
  SignUp: (props: Record<string, unknown>) => {
    captured.signUpProps = props;
    return <div data-testid="clerk-sign-up" />;
  },
}));

import SignInPage from "../sign-in/[[...sign-in]]/page";
import SignUpPage from "../sign-up/[[...sign-up]]/page";

interface AppearanceShape {
  elements?: Record<string, string>;
  variables?: Record<string, string>;
}

describe("(auth) Clerk appearance prop (C 디자인 언어)", () => {
  afterEach(() => {
    cleanup();
    captured.signInProps = null;
    captured.signUpProps = null;
  });

  it("SignIn — formButtonPrimary 코퍼 + var(--r) 반경 + 자체 focus ring 없음", () => {
    render(<SignInPage />);
    const appearance = captured.signInProps?.appearance as
      | AppearanceShape
      | undefined;
    expect(appearance?.elements?.formButtonPrimary).toContain("var(--copper)");
    expect(appearance?.elements?.formButtonPrimary).toContain(
      "rounded-[var(--r)]",
    );
    // 전역 카퍼 :focus-visible 소비 — 자체 ring 금지
    expect(appearance?.elements?.formFieldInput).not.toContain("focus:ring");
  });

  it("SignIn — colorPrimary 페이지 재정의 금지(브릿지 SSOT) + Clerk 헤더 숨김", () => {
    render(<SignInPage />);
    const appearance = captured.signInProps?.appearance as
      | AppearanceShape
      | undefined;
    expect(appearance?.variables).not.toHaveProperty("colorPrimary");
    expect(appearance?.elements?.header).toContain("hidden");
  });

  it("SignUp — formFieldInput 이 C 라인/카드 토큰 + var(--r) 반경", () => {
    render(<SignUpPage />);
    const appearance = captured.signUpProps?.appearance as
      | AppearanceShape
      | undefined;
    expect(appearance?.elements?.formFieldInput).toContain("var(--line)");
    expect(appearance?.elements?.formFieldInput).toContain(
      "rounded-[var(--r)]",
    );
  });
});
