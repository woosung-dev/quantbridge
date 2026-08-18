// Sprint 43 W15 — WaitlistTable 정렬/렌더 검증.

import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { WAITLIST_ACTION_EMPTY_REASON } from "@/features/waitlist/labels";
import type { WaitlistApplicationResponse } from "@/features/waitlist/schemas";
import { EMPTY_CELL } from "@/lib/labels";

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
    render(<WaitlistTable items={items} onApprove={() => {}} isApproving={false} />);
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
    render(<WaitlistTable items={items} onApprove={() => {}} isApproving={false} />);
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
    render(<WaitlistTable items={items} onApprove={onApprove} isApproving={false} />);
    const approveBtn = screen.getByRole("button", { name: /승인 \+ 초대/ });
    fireEvent.click(approveBtn);
    expect(onApprove).toHaveBeenCalledWith("00000000-0000-0000-0000-000000000001");
    // 승인 버튼은 1개만 — joined row 는 — 표시
    expect(screen.getAllByRole("button", { name: /승인 \+ 초대/ })).toHaveLength(1);
  });

  // ① 상태 배지 = .chip 어휘 (v3 캐논 — pill 반경 폐기)
  it("상태 배지 — .chip 톤 클래스로 그리고 rounded-full 을 쓰지 않는다", () => {
    const items: WaitlistApplicationResponse[] = [
      mkItem({
        id: "00000000-0000-0000-0000-000000000001",
        email: "joined@example.com",
        status: "joined",
        created_at: "2026-05-01T00:00:00+00:00",
      }),
      mkItem({
        id: "00000000-0000-0000-0000-000000000002",
        email: "rejected@example.com",
        status: "rejected",
        created_at: "2026-05-02T00:00:00+00:00",
      }),
    ];
    render(<WaitlistTable items={items} onApprove={() => {}} isApproving={false} />);
    const joinedBadge = screen.getByText("가입완료");
    expect(joinedBadge.className).toBe("chip done");
    const rejectedBadge = screen.getByText("거절");
    expect(rejectedBadge.className).toBe("chip warn");
    expect(joinedBadge.className).not.toContain("rounded-full");
  });

  // ③ 승인 중 스피너 = lucide (수제 SVG 금지)
  it("isApproving — 버튼 스피너가 lucide 아이콘이다", () => {
    const items: WaitlistApplicationResponse[] = [
      mkItem({
        id: "00000000-0000-0000-0000-000000000001",
        email: "pending@example.com",
        status: "pending",
        created_at: "2026-05-01T00:00:00+00:00",
      }),
    ];
    render(<WaitlistTable items={items} onApprove={() => {}} isApproving={true} />);
    const btn = screen.getByRole("button", { name: /전송 중/ });
    const svg = btn.querySelector("svg");
    expect(svg).not.toBeNull();
    // lucide 컴포넌트는 svg 에 lucide 클래스를 붙인다 — 수제 SVG 에는 없다.
    expect(svg!.getAttribute("class") ?? "").toContain("lucide");
  });

  // ④ 표 헤더 — 영문 축약 대신 한국어 카피 레지스터
  it("표 헤더 — TV/Pine/Pain Point 영문 축약이 없다", () => {
    const items: WaitlistApplicationResponse[] = [
      mkItem({
        id: "00000000-0000-0000-0000-000000000001",
        email: "a@example.com",
        status: "pending",
        created_at: "2026-05-01T00:00:00+00:00",
      }),
    ];
    render(<WaitlistTable items={items} onApprove={() => {}} isApproving={false} />);
    const headerTexts = screen.getAllByRole("columnheader").map((th) => th.textContent?.trim());
    expect(headerTexts).toContain("TV 구독");
    expect(headerTexts).toContain("Pine 경험");
    expect(headerTexts).toContain("풀고 싶은 문제");
    expect(headerTexts).not.toContain("TV");
    expect(headerTexts).not.toContain("Pine");
    expect(headerTexts).not.toContain("Pain Point");
  });

  // ⑥ 액션 열 무데이터 — EMPTY_CELL SSOT + 사유 title (orders-blotter 관례)
  it("pending 아닌 행 — EMPTY_CELL + 사유 title", () => {
    const items: WaitlistApplicationResponse[] = [
      mkItem({
        id: "00000000-0000-0000-0000-000000000001",
        email: "joined@example.com",
        status: "joined",
        created_at: "2026-05-01T00:00:00+00:00",
      }),
    ];
    render(<WaitlistTable items={items} onApprove={() => {}} isApproving={false} />);
    const dash = screen.getByTitle(WAITLIST_ACTION_EMPTY_REASON.joined);
    expect(dash).toHaveTextContent(EMPTY_CELL);
  });
});
