// SplitScreenShell — mobile (md 이하) 에서 BrandPanel 미노출 (hidden md:flex)
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { SplitScreenShell } from "../split-screen-shell";

describe("SplitScreenShell", () => {
  afterEach(() => {
    cleanup();
  });

  it("BrandPanel 에 hidden md:flex 클래스 적용 (mobile 미노출)", () => {
    render(
      <SplitScreenShell mode="sign-in">
        <div data-testid="form-child">child content</div>
      </SplitScreenShell>,
    );

    // BrandPanel 의 aside (aria-label="QuantBridge 소개") 가 hidden md:flex 클래스 보유
    const aside = screen.getByLabelText("QuantBridge 소개");
    expect(aside.className).toContain("hidden");
    expect(aside.className).toContain("md:flex");
  });

  it("children 이 우측 main wrapper 안에 렌더된다 + 흰색 배경 (prototype 04 정합)", () => {
    render(
      <SplitScreenShell mode="sign-up">
        <div data-testid="form-child">Clerk form</div>
      </SplitScreenShell>,
    );

    const child = screen.getByTestId("form-child");
    expect(child).toBeInTheDocument();
    // main wrapper 가 부모 chain 에 존재
    const main = child.closest("main");
    expect(main).not.toBeNull();
    expect(main?.className).toContain("min-h-dvh");
    // prototype 04 의 .form-panel { background: #fff } — bg-white class
    expect(main?.className).toContain("bg-white");
  });

  it("form wrapper — prototype max-w 400px 정합", () => {
    render(
      <SplitScreenShell mode="sign-in">
        <div data-testid="form-child">x</div>
      </SplitScreenShell>,
    );
    const child = screen.getByTestId("form-child");
    const wrapper = child.parentElement;
    expect(wrapper?.className).toContain("max-w-[400px]");
  });

  it("desktop grid 50/50 = grid-cols-1 md:grid-cols-2", () => {
    const { container } = render(
      <SplitScreenShell mode="sign-in">
        <div>x</div>
      </SplitScreenShell>,
    );
    const root = container.firstChild as HTMLElement;
    expect(root.className).toContain("grid-cols-1");
    expect(root.className).toContain("md:grid-cols-2");
  });
});
