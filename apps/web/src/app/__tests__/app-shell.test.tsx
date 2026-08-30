// 앱 셸 조립 계약 — root metadata·viewport·접근성 및 dashboard SSR identity 전달을 고정한다.
// root는 html/body를 정적 마크업으로, dashboard는 ServerIdentityProvider prop을 엘리먼트 트리로 검사한다.

import { Children, type ReactElement, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/styles/globals.css", () => ({}));

vi.mock("@/components/legal-notice-banner", () => ({
  LegalNoticeBanner: () => <div data-testid="legal-notice" />,
}));

vi.mock("@/components/providers/app-providers", () => ({
  AppProviders: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

vi.mock("@/components/ui/sonner", () => ({
  Toaster: () => <div data-testid="toaster" />,
}));

vi.mock("@/features/dashboard/components/dashboard-shell", () => ({
  DashboardShell: ({ children }: { children: ReactNode }) => (
    <div data-testid="dashboard-shell">{children}</div>
  ),
}));

vi.mock("@/components/providers/server-identity-provider", () => ({
  ServerIdentityProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

vi.mock("@/components/shortcut-help-dialog", () => ({
  ShortcutHelpDialog: () => <div data-testid="shortcut-help-dialog" />,
}));

vi.mock("@/lib/auth-server", () => ({
  getServerAuth: vi.fn(),
}));

import DashboardLayout from "../(dashboard)/layout";
import RootLayout, { metadata, viewport } from "../layout";
import { DashboardShell } from "@/features/dashboard/components/dashboard-shell";
import { ServerIdentityProvider } from "@/components/providers/server-identity-provider";
import { ShortcutHelpDialog } from "@/components/shortcut-help-dialog";
import { getServerAuth } from "@/lib/auth-server";
import { BRAND_PALETTE } from "@/lib/brand-palette";

const mockedGetServerAuth = vi.mocked(getServerAuth);

type ServerIdentityElement = ReactElement<{
  children: ReactNode;
  userId: string | null;
}>;

function renderRoot(children: ReactNode = <span>root-child-marker</span>): string {
  return renderToStaticMarkup(RootLayout({ children }));
}

function dashboardNodes(element: ServerIdentityElement): {
  shell: ReactElement<{ children: ReactNode }>;
  shortcut: ReactElement;
} {
  const wrapper = element.props.children as ReactElement<{ children: ReactNode }>;
  const [shell, shortcut] = Children.toArray(wrapper.props.children) as [
    ReactElement<{ children: ReactNode }>,
    ReactElement,
  ];
  return { shell, shortcut };
}

afterEach(() => vi.clearAllMocks());

describe("app shell contracts", () => {
  it("root metadata.title은 default와 브랜드 template을 함께 둔다", () => {
    expect(metadata.title).toEqual({
      default: "QuantBridge",
      template: "%s · QuantBridge",
    });
  });

  it("root metadata.description은 비어 있지 않다", () => {
    expect(metadata.description).toBeTruthy();
  });

  it("viewport dark themeColor는 BRAND_PALETTE.dark.bg와 동기다", () => {
    expect(viewport.themeColor).toContainEqual({
      media: "(prefers-color-scheme: dark)",
      color: BRAND_PALETTE.dark.bg,
    });
  });

  it("viewport light themeColor는 BRAND_PALETTE.light.bg와 동기다", () => {
    expect(viewport.themeColor).toContainEqual({
      media: "(prefers-color-scheme: light)",
      color: BRAND_PALETTE.light.bg,
    });
  });

  it("viewport의 dark와 light media 쿼리는 서로 다른 색을 쓴다", () => {
    expect(viewport.themeColor).toEqual([
      { media: "(prefers-color-scheme: dark)", color: BRAND_PALETTE.dark.bg },
      { media: "(prefers-color-scheme: light)", color: BRAND_PALETTE.light.bg },
    ]);
  });

  it("root layout은 html lang을 ko로 렌더한다", () => {
    const document = new DOMParser().parseFromString(renderRoot(), "text/html");
    expect(document.documentElement.getAttribute("lang")).toBe("ko");
  });

  it("skip link는 main-content를 가리키고 포커스 때만 보인다", () => {
    const document = new DOMParser().parseFromString(renderRoot(), "text/html");
    const skipLink = document.querySelector('a[href="#main-content"]');

    expect(skipLink).not.toBeNull();
    expect(skipLink?.className.startsWith("sr-only")).toBe(true);
    expect(skipLink?.classList.contains("focus:not-sr-only")).toBe(true);
  });

  it("root layout은 전달받은 children을 렌더한다", () => {
    expect(renderRoot(<span>root-child-marker</span>)).toContain("root-child-marker");
  });

  it("dashboard layout은 SSR userId를 ServerIdentityProvider에 그대로 넘긴다", async () => {
    mockedGetServerAuth.mockResolvedValue({ userId: "u-42", token: "t" });

    const element = (await DashboardLayout({
      children: <span>dashboard-child</span>,
    })) as ServerIdentityElement;

    expect(mockedGetServerAuth).toHaveBeenCalledOnce();
    expect(element.type).toBe(ServerIdentityProvider);
    expect(element.props.userId).toBe("u-42");
  });

  it("dashboard layout은 null userId도 바꾸지 않고 ServerIdentityProvider에 넘긴다", async () => {
    mockedGetServerAuth.mockResolvedValue({ userId: null, token: "t" });
    const element = (await DashboardLayout({
      children: <span>dashboard-child</span>,
    })) as ServerIdentityElement;

    expect(element.props.userId).toBeNull();
  });

  it("dashboard layout은 children을 DashboardShell 안에 넣는다", async () => {
    mockedGetServerAuth.mockResolvedValue({ userId: "u-42", token: "t" });
    const child = <span>dashboard-child-marker</span>;
    const element = (await DashboardLayout({ children: child })) as ServerIdentityElement;
    const { shell } = dashboardNodes(element);

    expect(shell.type).toBe(DashboardShell);
    expect(shell.props.children).toBe(child);
  });

  it("dashboard layout은 ShortcutHelpDialog도 함께 조립한다", async () => {
    mockedGetServerAuth.mockResolvedValue({ userId: "u-42", token: "t" });
    const element = (await DashboardLayout({
      children: <span>dashboard-child</span>,
    })) as ServerIdentityElement;
    const { shortcut } = dashboardNodes(element);

    expect(shortcut.type).toBe(ShortcutHelpDialog);
  });
});
