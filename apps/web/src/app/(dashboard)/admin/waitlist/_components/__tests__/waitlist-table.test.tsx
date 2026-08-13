// Sprint 43 W15 — WaitlistTable 정렬/렌더 검증.

import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { WaitlistApplicationResponse } from "@/features/waitlist/schemas";

import { WaitlistTable } from "../waitlist-table";

function mkItem(
  overrides: Partial<WaitlistApplicationResponse> &
    Pick<WaitlistApplicationResponse, "id" | "email" | "status" | "created_at">,
): WaitlistApplicationResponse {
  return {
    tv_subscription: "pro",
    exchange_capital: "1k_to_10k",
    pine_experience: "beginner",
    existing_tool: null,
    pain_point: "n/a",
    invite_sent_at: null,
    invited_at: null,
    joined_at: null,
    ...overrides,
  };
}

describe("WaitlistTable", () => {
  it("기본 정렬 = 신청일 desc — 최신 row 가 위", async () => {
    const items: WaitlistApplicationResponse[] = [
      mkItem({
        id: "00000000-0000-0000-0000-000000000001",
        email: "older@example.com",
        status: "pending",
        created_at: "2026-04-01T00:00:00+00:00",
      }),
      mkItem({
        id: "00000000-0000-0000-0000-000000000002",
        email: "newer@example.com",
        status: "pending",
        created_at: "2026-05-01T00:00:00+00:00",
      }),
    ];
    render(
      <WaitlistTable items={items} onApprove={() => {}} isApproving={false} />,
    );
    const rows = screen.getAllByRole("row").slice(1); // skip header
    expect(within(rows[0]!).getByText("newer@example.com")).toBeInTheDocument();
    expect(within(rows[1]!).getByText("older@example.com")).toBeInTheDocument();
    // aria-sort = descending on 신청일 헤더
    const createdHeader = screen
      .getAllByRole("columnheader")
      .find((th) => th.textContent?.includes("신청일"));
    expect(createdHeader).toHaveAttribute("aria-sort", "descending");
  });

  it("이메일 헤더 클릭 — asc 정렬 + aria-sort=ascending", async () => {
    const items: WaitlistApplicationResponse[] = [
      mkItem({
        id: "00000000-0000-0000-0000-000000000001",
        email: "zoe@example.com",
        status: "pending",
        created_at: "2026-04-01T00:00:00+00:00",
      }),
      mkItem({
        id: "00000000-0000-0000-0000-000000000002",
        email: "alice@example.com",
        status: "pending",
        created_at: "2026-05-01T00:00:00+00:00",
      }),
    ];
    render(
      <WaitlistTable items={items} onApprove={() => {}} isApproving={false} />,
    );
    const emailButton = screen.getByRole("button", { name: /이메일/ });
    fireEvent.click(emailButton);

    const rows = screen.getAllByRole("row").slice(1);
    expect(within(rows[0]!).getByText("alice@example.com")).toBeInTheDocument();
    expect(within(rows[1]!).getByText("zoe@example.com")).toBeInTheDocument();
    const emailHeader = screen
      .getAllByRole("columnheader")
      .find((th) => th.textContent?.includes("이메일"));
    expect(emailHeader).toHaveAttribute("aria-sort", "ascending");
  });

  it("pending 만 승인 버튼 노출 + onApprove 호출", async () => {
    const onApprove = vi.fn();
    const items: WaitlistApplicationResponse[] = [
      mkItem({
        id: "00000000-0000-0000-0000-000000000001",
        email: "pending@example.com",
        status: "pending",
        created_at: "2026-05-01T00:00:00+00:00",
      }),
      mkItem({
        id: "00000000-0000-0000-0000-000000000002",
        email: "joined@example.com",
        status: "joined",
        created_at: "2026-05-02T00:00:00+00:00",
      }),
    ];
    render(
      <WaitlistTable items={items} onApprove={onApprove} isApproving={false} />,
    );
    const approveBtn = screen.getByRole("button", { name: /승인 \+ 초대/ });
    fireEvent.click(approveBtn);
    expect(onApprove).toHaveBeenCalledWith(
      "00000000-0000-0000-0000-000000000001",
    );
    // 승인 버튼은 1개만 — joined row 는 — 표시
    expect(screen.getAllByRole("button", { name: /승인 \+ 초대/ })).toHaveLength(
      1,
    );
  });
});
