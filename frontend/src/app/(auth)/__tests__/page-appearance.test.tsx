// Clerk SignIn/SignUp 페이지에 전달되는 appearance prop 토큰 매핑 검증
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render } from "@testing-library/react";

// Clerk SignIn / SignUp 을 mock 으로 대체하여 appearance prop 캡처
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

describe("(auth) Clerk appearance prop", () => {
  afterEach(() => {
    cleanup();
    captured.signInProps = null;
    captured.signUpProps = null;
  });

  it("SignIn 페이지 — formButtonPrimary 에 --primary 토큰 매핑", () => {
    render(<SignInPage />);
    const appearance = captured.signInProps?.appearance as
      | AppearanceShape
      | undefined;
    expect(appearance).toBeDefined();
    expect(appearance?.elements?.formButtonPrimary).toContain(
      "var(--primary)",
    );
    expect(appearance?.elements?.formButtonPrimary).toContain(
      "var(--radius-md)",
    );
    // Precision Instrument radius-md=6px 정합 (구 10px)
    expect(appearance?.variables?.borderRadius).toBe("6px");
    // colorPrimary 는 ClerkThemeBridge 가 테마별 주입 — 페이지 재정의(하드코딩) 금지
    expect(appearance?.variables).not.toHaveProperty("colorPrimary");
    // Precision Instrument: hover 는 색 변화만 — 그림자 승격(lift) 금지
    expect(appearance?.elements?.formButtonPrimary).not.toContain(
      "hover:shadow",
    );
  });

  it("SignUp 페이지 — formFieldInput 에 --border 토큰 + radius-sm 토큰 (Precision Instrument)", () => {
    render(<SignUpPage />);
    const appearance = captured.signUpProps?.appearance as
      | AppearanceShape
      | undefined;
    expect(appearance).toBeDefined();
    expect(appearance?.elements?.formFieldInput).toContain("var(--border)");
    // 인풋 radius = --radius-sm 토큰 (구 rounded-[8px] 리터럴 폐기, DESIGN.md §5)
    expect(appearance?.elements?.formFieldInput).toContain(
      "rounded-[var(--radius-sm)]",
    );
    // input height=48px 터치 타겟 유지
    expect(appearance?.elements?.formFieldInput).toContain("h-12");
  });
});
