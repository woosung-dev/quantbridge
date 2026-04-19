import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import { EditorView } from "../editor-view";

const strategyId = "11111111-2222-4333-8444-555555555555";

const fixtureStrategy = {
  id: strategyId,
  name: "BTC swing",
  pine_source: "//@version=5\nstrategy('x')",
  pine_version: "v5",
  parse_status: "ok",
  symbol: "BTC/USDT",
  timeframe: "1h",
  is_archived: false,
  entry_count: 1,
  exit_count: 1,
  functions_used: [],
  warnings: [],
  errors: [],
};

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    refresh: vi.fn(),
  }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/features/strategy/hooks", () => ({
  useStrategy: () => ({
    data: fixtureStrategy,
    isLoading: false,
    isError: false,
  }),
  useUpdateStrategy: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
}));

vi.mock("../tab-code", () => ({ TabCode: () => <div data-testid="tab-code" /> }));
vi.mock("../tab-parse", () => ({ TabParse: () => <div data-testid="tab-parse" /> }));
vi.mock("../tab-metadata", () => ({
  TabMetadata: () => <div data-testid="tab-metadata" />,
}));
vi.mock("../delete-dialog", () => ({
  DeleteDialog: () => <div data-testid="delete-dialog" />,
}));

describe("EditorView — 백테스트 실행 CTA", () => {
  it("헤더에 '백테스트 실행' 링크가 /backtests/new?strategy_id=<id> 로 이동", () => {
    const { container } = render(<EditorView id={strategyId} />);

    const link = container.querySelector<HTMLAnchorElement>(
      'a[aria-label="백테스트 실행"]',
    );
    expect(link).not.toBeNull();
    expect(link?.getAttribute("href")).toBe(
      `/backtests/new?strategy_id=${strategyId}`,
    );
    expect(link?.textContent).toMatch(/백테스트 실행/);
  });

  it("CTA 는 disabled 상태가 아니다", () => {
    const { container } = render(<EditorView id={strategyId} />);
    const link = container.querySelector<HTMLAnchorElement>(
      'a[aria-label="백테스트 실행"]',
    );
    expect(link).not.toBeNull();
    expect(link?.getAttribute("aria-disabled")).not.toBe("true");
    expect(link?.hasAttribute("disabled")).toBe(false);
    // Link 내부 텍스트 노드 및 사용되는 이미지·라벨 검증 — screen 도 합쳐 추가 확인.
    expect(screen.getByText(/백테스트 실행/)).toBeInTheDocument();
  });
});
