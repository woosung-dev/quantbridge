// Sprint 43 W15 — WaitlistStatsStrip KPI 집계/표시 검증.

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { WaitlistApplicationResponse } from "@/features/waitlist/schemas";

import { WaitlistStatsStrip } from "../waitlist-stats-strip";

function mkItem(
  overrides: Partial<WaitlistApplicationResponse> &
    Pick<WaitlistApplicationResponse, "id" | "status">,
): WaitlistApplicationResponse {
  return {
    email: "u@example.com",
    tv_subscription: "pro",
    exchange_capital: "1k_to_10k",
    pine_experience: "beginner",
    existing_tool: null,
    pain_point: "n/a",
    invite_sent_at: null,
    invited_at: null,
    joined_at: null,
    created_at: "2026-05-01T00:00:00+00:00",
    ...overrides,
  };
}

describe("WaitlistStatsStrip", () => {
  it("빈 배열 — 모두 0", () => {
    render(<WaitlistStatsStrip items={[]} />);
    expect(screen.getByLabelText("Waitlist 요약 통계")).toBeInTheDocument();
    expect(screen.getByTestId("waitlist-stat-총 신청")).toHaveTextContent("0");
    expect(screen.getByTestId("waitlist-stat-미승인 (대기중)")).toHaveTextContent(
      "0",
    );
    expect(screen.getByTestId("waitlist-stat-승인됨")).toHaveTextContent("0");
  });

  it("status 별 집계 — 승인됨 = invited + joined", () => {
    const items: WaitlistApplicationResponse[] = [
      mkItem({ id: "00000000-0000-0000-0000-000000000001", status: "pending" }),
      mkItem({ id: "00000000-0000-0000-0000-000000000002", status: "pending" }),
      mkItem({ id: "00000000-0000-0000-0000-000000000003", status: "invited" }),
      mkItem({ id: "00000000-0000-0000-0000-000000000004", status: "joined" }),
      mkItem({ id: "00000000-0000-0000-0000-000000000005", status: "rejected" }),
    ];
    render(<WaitlistStatsStrip items={items} total={42} />);
    // total prop 우선 — BE total
    expect(screen.getByTestId("waitlist-stat-총 신청")).toHaveTextContent("42");
    expect(screen.getByTestId("waitlist-stat-미승인 (대기중)")).toHaveTextContent(
      "2",
    );
    // 승인됨 = invited(1) + joined(1)
    expect(screen.getByTestId("waitlist-stat-승인됨")).toHaveTextContent("2");
  });

  it("total 미제공 — items.length 사용", () => {
    const items: WaitlistApplicationResponse[] = [
      mkItem({ id: "00000000-0000-0000-0000-000000000001", status: "pending" }),
    ];
    render(<WaitlistStatsStrip items={items} />);
    expect(screen.getByTestId("waitlist-stat-총 신청")).toHaveTextContent("1");
  });
});
