// 대시보드와 초대 route error boundary의 공통 Next.js 계약을 검증한다.

import type { ComponentType } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import DashboardError from "../error";
import BacktestsError from "../backtests/error";
import DashboardRouteError from "../dashboard/error";
import OrdersError from "../orders/error";
import StrategiesError from "../strategies/error";
import TradingError from "../trading/error";
import InviteError from "../../invite/[token]/error";

type ErrorBoundaryProps = {
  error: Error & { digest?: string };
  reset: () => void;
};

type ErrorBoundaryCase = {
  name: string;
  ErrorBoundary: ComponentType<ErrorBoundaryProps>;
  hasHeading: boolean;
  rendersDigest: boolean;
};

const DIGEST = "ref-xyz-123";
const ERROR_BOUNDARIES: ErrorBoundaryCase[] = [
  {
    name: "dashboard group",
    ErrorBoundary: DashboardError,
    hasHeading: true,
    rendersDigest: true,
  },
  {
    name: "backtests",
    ErrorBoundary: BacktestsError,
    hasHeading: false,
    rendersDigest: true,
  },
  {
    name: "dashboard",
    ErrorBoundary: DashboardRouteError,
    hasHeading: false,
    rendersDigest: true,
  },
  {
    name: "orders",
    ErrorBoundary: OrdersError,
    hasHeading: false,
    rendersDigest: true,
  },
  {
    name: "strategies",
    ErrorBoundary: StrategiesError,
    hasHeading: false,
    rendersDigest: true,
  },
  {
    name: "trading",
    ErrorBoundary: TradingError,
    hasHeading: false,
    rendersDigest: true,
  },
  {
    name: "invite token",
    ErrorBoundary: InviteError,
    hasHeading: true,
    rendersDigest: false,
  },
];

let consoleErrorSpy: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
});

afterEach(() => {
  cleanup();
  consoleErrorSpy.mockRestore();
});

describe("dashboard route error boundaries", () => {
  it.each(ERROR_BOUNDARIES)("%s renders without throwing", ({ ErrorBoundary }) => {
    const { container } = render(
      <ErrorBoundary error={new Error("Network failed")} reset={vi.fn()} />,
    );

    expect(container.textContent).not.toBe("");
  });

  it.each(ERROR_BOUNDARIES)("%s wires retry to reset", ({ ErrorBoundary }) => {
    const reset = vi.fn();
    render(<ErrorBoundary error={new Error("Transient")} reset={reset} />);

    fireEvent.click(screen.getByRole("button", { name: "다시 시도" }));

    expect(reset).toHaveBeenCalledTimes(1);
  });

  it.each(ERROR_BOUNDARIES)(
    "%s records whether it has a readable heading",
    ({ ErrorBoundary, hasHeading }) => {
      render(<ErrorBoundary error={new Error("Network failed")} reset={vi.fn()} />);

      const headings = screen.queryAllByRole("heading");
      if (hasHeading) {
        expect(headings.length).toBeGreaterThanOrEqual(1);
        expect(headings.some((heading) => heading.textContent?.trim())).toBe(true);
        return;
      }

      expect(headings).toHaveLength(0);
    },
  );

  it.each(ERROR_BOUNDARIES)(
    "%s records whether it exposes the error digest",
    ({ ErrorBoundary, rendersDigest }) => {
      const { container } = render(
        <ErrorBoundary
          error={Object.assign(new Error("Network failed"), { digest: DIGEST })}
          reset={vi.fn()}
        />,
      );

      if (rendersDigest) {
        expect(container.textContent).toContain(DIGEST);
        return;
      }

      expect(container.textContent).not.toContain(DIGEST);
    },
  );

  it.each(ERROR_BOUNDARIES)("%s handles an absent digest", ({ ErrorBoundary }) => {
    const { container } = render(
      <ErrorBoundary error={new Error("Network failed")} reset={vi.fn()} />,
    );

    expect(container.textContent).not.toContain("undefined");
  });

  it("keeps at least five distinct route error screens", () => {
    const contents = ERROR_BOUNDARIES.map(({ ErrorBoundary }) => {
      const { container, unmount } = render(
        <ErrorBoundary error={new Error("Network failed")} reset={vi.fn()} />,
      );
      const content = container.textContent;
      unmount();
      return content;
    });

    expect(new Set(contents).size).toBeGreaterThanOrEqual(5);
  });
});
