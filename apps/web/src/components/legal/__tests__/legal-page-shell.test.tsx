// LegalPageShell — Sprint 43 W14 통일 layout 검증.

import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { LegalPageShell } from "../legal-page-shell";

afterEach(() => {
  cleanup();
});

describe("LegalPageShell", () => {
  it("title + breadcrumb + badge + footnote 모두 렌더 (default layout)", () => {
    render(
      <LegalPageShell
        title="Privacy Policy / 개인정보 처리방침"
        breadcrumbLabel="Privacy"
        badgeLabel="Beta 임시본"
        footnote="최종 개정: 2026-04-25"
      >
        <p>본문</p>
      </LegalPageShell>,
    );

    expect(screen.getByTestId("legal-page-shell")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 1, name: /Privacy Policy/ }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("legal-page-breadcrumb")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Home" }),
    ).toHaveAttribute("href", "/");
    expect(screen.getByTestId("legal-page-badge")).toHaveTextContent("Beta 임시본");
    expect(screen.getByText("최종 개정: 2026-04-25")).toBeInTheDocument();
    expect(screen.getByText("본문")).toBeInTheDocument();
  });

  it("centered=true 면 breadcrumb 미렌더 + hero layout", () => {
    render(
      <LegalPageShell title="Region blocked" centered breadcrumbLabel="NA">
        <p>안내</p>
      </LegalPageShell>,
    );

    expect(screen.getByRole("heading", { level: 1, name: "Region blocked" })).toBeInTheDocument();
    expect(screen.queryByTestId("legal-page-breadcrumb")).not.toBeInTheDocument();
    expect(screen.getByText("안내")).toBeInTheDocument();
  });

  it("badgeLabel · footnote 미지정 시 미렌더", () => {
    render(
      <LegalPageShell title="Bare">
        <p>x</p>
      </LegalPageShell>,
    );

    expect(screen.queryByTestId("legal-page-badge")).not.toBeInTheDocument();
    expect(screen.queryByTestId("legal-page-breadcrumb")).not.toBeInTheDocument();
  });
});
