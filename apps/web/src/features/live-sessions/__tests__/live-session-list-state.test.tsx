// Sprint 33 BL-174 list-only 회귀 — Empty/Failed/Loading state 통일.
// LiveSessionStateView 가 3 state 모두 testid + title 노출.

import { fireEvent, render, screen } from "@testing-library/react";
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
      screen.getByText("활성 세션이 없습니다."),
    ).toBeInTheDocument();
  });

  test("활성 0건이어도 최근 종료 세션을 표시하고 선택한다", () => {
    const onSelect = vi.fn();
    mockUseLiveSessions.mockReturnValue({
      data: {
        items: [
          {
            id: "id1",
            symbol: "BTC/USDT",
            interval: "1h",
            is_active: false,
            created_at: new Date().toISOString(),
            deactivated_at: "2026-07-28T12:00:00Z",
          },
        ],
      },
      isLoading: false,
      error: null,
    });

    render(<LiveSessionList onSelect={onSelect} />);

    expect(screen.getByTestId("live-session-empty")).toBeInTheDocument();
    expect(screen.getByTestId("recent-inactive-list")).toBeInTheDocument();
    expect(screen.getByText("최근 종료된 세션")).toBeInTheDocument();
    expect(screen.getByText("종료된 세션")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /BTC\/USDT/ }));
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ id: "id1", is_active: false }));
  });

  test("BL-484 — 종료 세션 카드에 한국어 사유가 붙는다", () => {
    mockUseLiveSessions.mockReturnValue({
      data: {
        items: [
          {
            id: "id-reason",
            symbol: "BTC/USDT",
            interval: "1h",
            is_active: false,
            created_at: new Date().toISOString(),
            deactivated_at: "2026-07-30T12:00:00Z",
            deactivated_reason: "gap_resync_position_mismatch",
          },
        ],
      },
      isLoading: false,
      error: null,
    });

    render(<LiveSessionList />);

    expect(screen.getByTestId("inactive-live-session-reason-id-reason")).toHaveTextContent(
      "평가 공백 후 포지션 불일치",
    );
  });

  test("BL-484 — 사유가 없는 과거 행은 사유 칩 없이 렌더된다", () => {
    mockUseLiveSessions.mockReturnValue({
      data: {
        items: [
          {
            id: "id-legacy",
            symbol: "ETH/USDT",
            interval: "1h",
            is_active: false,
            created_at: new Date().toISOString(),
            deactivated_at: "2026-07-30T12:00:00Z",
            deactivated_reason: null,
          },
        ],
      },
      isLoading: false,
      error: null,
    });

    render(<LiveSessionList />);

    // 카드는 그대로 뜨고 사유 칩만 없다 — 마이그레이션 이전 행에서 화면이 깨지지 않는다.
    expect(screen.getByTestId("inactive-live-session-id-legacy")).toBeInTheDocument();
    expect(
      screen.queryByTestId("inactive-live-session-reason-id-legacy"),
    ).not.toBeInTheDocument();
  });

  test("최근 종료 세션이 없으면 별도 빈 상태를 표시한다", () => {
    mockUseLiveSessions.mockReturnValue({
      data: { items: [] },
      isLoading: false,
      error: null,
    });
    render(<LiveSessionList />);

    expect(screen.getByTestId("live-session-empty")).toBeInTheDocument();
    expect(screen.getByTestId("recent-inactive-empty")).toBeInTheDocument();
    expect(screen.getByText("최근 종료된 세션이 없습니다.")).toBeInTheDocument();
  });
});
