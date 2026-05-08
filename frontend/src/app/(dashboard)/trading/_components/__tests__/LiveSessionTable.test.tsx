// Sprint 43-W12 — LiveSessionTable 단위 테스트.
// - 빈 배열 → 안내 문구
// - 활성 세션 → ACTIVE badge + 심볼 / 인터벌 표시
// - sort toggle: 최신 시작순 ↔ 활성 우선

import { fireEvent, render, screen } from "@testing-library/react";

import { LiveSessionTable } from "@/app/(dashboard)/trading/_components/live-session-table";
import type { LiveSession } from "@/features/live-sessions/schemas";

const SESSION_A: LiveSession = {
  id: "10000000-0000-4000-a000-000000000001",
  user_id: "u0000000-0000-4000-a000-000000000001",
  strategy_id: "s0000000-0000-4000-a000-000000000001",
  exchange_account_id: "e0000000-0000-4000-a000-000000000001",
  symbol: "BTC/USDT",
  interval: "5m",
  is_active: true,
  last_evaluated_bar_time: null,
  created_at: "2026-05-08T10:00:00Z",
  deactivated_at: null,
};

const SESSION_B: LiveSession = {
  ...SESSION_A,
  id: "10000000-0000-4000-a000-000000000002",
  symbol: "ETH/USDT",
  interval: "15m",
  is_active: false,
  created_at: "2026-05-08T11:00:00Z",
};

describe("LiveSessionTable", () => {
  test("빈 배열 → 빈 상태 안내 문구", () => {
    render(<LiveSessionTable sessions={[]} />);
    expect(screen.getByText("활성 세션이 없습니다.")).toBeInTheDocument();
    expect(screen.queryByTestId("live-session-table")).not.toBeInTheDocument();
  });

  test("세션 2개 → 심볼 + ACTIVE/PAUSED badge 표시", () => {
    render(<LiveSessionTable sessions={[SESSION_A, SESSION_B]} />);
    expect(screen.getByTestId("live-session-table")).toBeInTheDocument();
    expect(screen.getByText("BTC/USDT")).toBeInTheDocument();
    expect(screen.getByText("ETH/USDT")).toBeInTheDocument();
    expect(screen.getByText("ACTIVE")).toBeInTheDocument();
    expect(screen.getByText("PAUSED")).toBeInTheDocument();
    expect(screen.getByText("라이브 세션 (2)")).toBeInTheDocument();
  });

  test("sort toggle: 최신 시작순 ↔ 활성 우선", () => {
    render(<LiveSessionTable sessions={[SESSION_A, SESSION_B]} />);

    const toggle = screen.getByTestId("live-session-sort-toggle");
    expect(toggle).toHaveTextContent("최신 시작순");

    fireEvent.click(toggle);
    expect(toggle).toHaveTextContent("활성 우선");

    fireEvent.click(toggle);
    expect(toggle).toHaveTextContent("최신 시작순");
  });

  test("resolveStrategyName / resolveExchangeLabel 적용", () => {
    render(
      <LiveSessionTable
        sessions={[SESSION_A]}
        resolveStrategyName={(id) => `전략-${id.slice(0, 4)}`}
        resolveExchangeLabel={(id) => `Bybit-${id.slice(0, 4)}`}
      />,
    );
    expect(screen.getByText(/전략-s000/)).toBeInTheDocument();
    expect(screen.getByText(/Bybit-e000/)).toBeInTheDocument();
  });
});
