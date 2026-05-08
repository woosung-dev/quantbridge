// ErrorIllustration variant 분기 검증 — Sprint 43 W8

import { describe, expect, it, afterEach } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { ErrorIllustration } from "../error-illustration";

afterEach(() => cleanup());

describe("ErrorIllustration — variant 분기", () => {
  it("variant 404 — backdrop 텍스트 '404' + bg data-variant", () => {
    render(<ErrorIllustration variant="404" />);
    expect(screen.getByTestId("error-illustration-backdrop")).toHaveTextContent("404");
    expect(screen.getByTestId("error-illustration-bg")).toHaveAttribute("data-variant", "404");
    expect(screen.getByTestId("error-illustration-icon")).toBeInTheDocument();
  });

  it("variant 500 — backdrop 텍스트 '500'", () => {
    render(<ErrorIllustration variant="500" />);
    expect(screen.getByTestId("error-illustration-backdrop")).toHaveTextContent("500");
    expect(screen.getByTestId("error-illustration-bg")).toHaveAttribute("data-variant", "500");
  });

  it("variant 503 — backdrop 텍스트 '503'", () => {
    render(<ErrorIllustration variant="503" />);
    expect(screen.getByTestId("error-illustration-backdrop")).toHaveTextContent("503");
    expect(screen.getByTestId("error-illustration-bg")).toHaveAttribute("data-variant", "503");
  });
});
