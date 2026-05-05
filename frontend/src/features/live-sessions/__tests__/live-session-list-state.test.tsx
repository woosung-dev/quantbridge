// Sprint 33 BL-174 list-only 회귀 — Empty/Failed/Loading state 통일.
// LiveSessionStateView 가 3 state 모두 testid + title 노출.

import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

vi.mock("../hooks", () => ({
  useLiveSessions: vi.fn(),
  useDeactivateLiveSession: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
}));

import { LiveSessionList } from "../components/live-session-list";
import { useLiveSessions } from "../hooks";

const mockUseLiveSessions = useLiveSessions as unknown as ReturnType<
  typeof vi.fn
>;

describe("LiveSessionList state view (BL-174 list-only)", () => {
  test("Loading state — title 로드 중 + testid live-session-loading", () => {
    mockUseLiveSessions.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });
    render(<LiveSessionList />);
    expect(screen.getByTestId("live-session-loading")).toBeInTheDocument();
    expect(screen.getByText("로드 중")).toBeInTheDocument();
  });

  test("Failed state — error.message 노출 + testid live-session-error", () => {
    mockUseLiveSessions.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("Network down"),
    });
    render(<LiveSessionList />);
    expect(screen.getByTestId("live-session-error")).toBeInTheDocument();
    expect(screen.getByText("로드 실패")).toBeInTheDocument();
    expect(screen.getByText(/Network down/)).toBeInTheDocument();
  });

  test("Empty state — items 0 + testid live-session-empty", () => {
    mockUseLiveSessions.mockReturnValue({
      data: { items: [] },
      isLoading: false,
      error: null,
    });
    render(<LiveSessionList />);
    expect(screen.getByTestId("live-session-empty")).toBeInTheDocument();
    expect(
      screen.getByText("활성 Live Session 이 없습니다"),
    ).toBeInTheDocument();
  });

  test("Empty state — is_active=false 만 있으면 empty", () => {
    mockUseLiveSessions.mockReturnValue({
      data: {
        items: [
          {
            id: "id1",
            symbol: "BTC/USDT",
            interval: "1h",
            is_active: false,
            created_at: new Date().toISOString(),
          },
        ],
      },
      isLoading: false,
      error: null,
    });
    render(<LiveSessionList />);
    expect(screen.getByTestId("live-session-empty")).toBeInTheDocument();
  });
});
