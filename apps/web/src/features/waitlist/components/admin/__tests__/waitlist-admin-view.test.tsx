// WaitlistAdminView — 목록 상태·기본 pending 필터·검색 배선·승인 토스트를 검증한다.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { ApiError } from "@/lib/api-client";

const { useAdminWaitlistList, useApproveWaitlist } = vi.hoisted(() => ({
  useAdminWaitlistList: vi.fn(),
  useApproveWaitlist: vi.fn(),
}));
vi.mock("@/features/waitlist/hooks", () => ({
  useAdminWaitlistList: (...a: unknown[]) => useAdminWaitlistList(...a),
  useApproveWaitlist: (...a: unknown[]) => useApproveWaitlist(...a),
}));

const { toastSuccess, toastError } = vi.hoisted(() => ({
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
}));
vi.mock("sonner", () => ({
  toast: { success: toastSuccess, error: toastError },
}));

vi.mock("../waitlist-filter-bar", () => ({
  WaitlistFilterBar: ({
    status,
    search,
    onSearchChange,
  }: {
    status: string;
    search: string;
    onSearchChange: (value: string) => void;
  }) => (
    <div data-testid="waitlist-filter-bar">
      <span>필터: {status}</span>
      <input
        aria-label="더미 이메일 검색"
        value={search}
        onChange={(event) => onSearchChange(event.target.value)}
      />
    </div>
  ),
}));

vi.mock("../waitlist-stats-strip", () => ({
  WaitlistStatsStrip: ({ total }: { total: number }) => (
    <div data-testid="waitlist-stats-strip">통계: {total}</div>
  ),
}));

vi.mock("../waitlist-table", () => ({
  WaitlistTable: ({
    items,
    onApprove,
  }: {
    items: readonly { id: string; email: string }[];
    onApprove: (id: string) => void;
  }) => (
    <div data-testid="waitlist-table">
      <span>표: {items.map((item) => item.email).join(", ")}</span>
      <button type="button" onClick={() => onApprove(items[0]!.id)}>
        더미 승인
      </button>
    </div>
  ),
}));

import { WaitlistAdminView } from "../waitlist-admin-view";

const APPLICATION = {
  id: "00000000-0000-0000-0000-000000000001",
  email: "pending@example.com",
  tv_subscription: "pro",
  exchange_capital: "1k_to_10k",
  pine_experience: "beginner",
  existing_tool: null,
  pain_point: "승인 흐름을 확인하고 싶습니다.",
  status: "pending" as const,
  invite_sent_at: null,
  invited_at: null,
  joined_at: null,
  created_at: "2026-08-21T00:00:00+00:00",
};

type ApproveCallbacks = {
  onSuccess?: (approved: { email: string }) => void;
  onError?: (error: unknown) => void;
};

let listState: {
  data: { items: typeof APPLICATION[]; total: number } | undefined;
  isPending: boolean;
  error: Error | null;
};
let approveState: { mutate: ReturnType<typeof vi.fn>; isPending: boolean };
let approveCallbacks: ApproveCallbacks;

describe("WaitlistAdminView", () => {
  beforeEach(() => {
    listState = { data: undefined, isPending: false, error: null };
    approveState = { mutate: vi.fn(), isPending: false };
    approveCallbacks = {};
    useAdminWaitlistList.mockImplementation(() => listState);
    useApproveWaitlist.mockImplementation((callbacks: ApproveCallbacks) => {
      approveCallbacks = callbacks;
      return approveState;
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("로딩 — 스켈레톤을 보이고 표는 렌더하지 않는다", () => {
    listState = { data: undefined, isPending: true, error: null };

    render(<WaitlistAdminView />);

    expect(screen.getByTestId("waitlist-admin-loading")).toBeInTheDocument();
    expect(screen.queryByTestId("waitlist-table")).not.toBeInTheDocument();
  });

  it("에러 — 사람이 읽을 메시지를 보이고 던지지 않는다", () => {
    listState = { data: undefined, isPending: false, error: new Error("서버 연결 실패") };

    expect(() => render(<WaitlistAdminView />)).not.toThrow();
    expect(screen.getByText("Waitlist 불러오기 실패: 서버 연결 실패")).toBeInTheDocument();
  });

  it("기본 필터 — 목록 훅에 pending query를 전달한다", () => {
    render(<WaitlistAdminView />);

    expect(useAdminWaitlistList).toHaveBeenCalledWith({ status: "pending" });
  });

  it("검색어 — 클라이언트 목록을 필터링한다", () => {
    listState = { data: { items: [APPLICATION], total: 1 }, isPending: false, error: null };
    render(<WaitlistAdminView />);

    fireEvent.change(screen.getByLabelText("더미 이메일 검색"), {
      target: { value: "alice@example.com" },
    });

    expect(useAdminWaitlistList).toHaveBeenLastCalledWith({ status: "pending" });
    expect(screen.getByText('"alice@example.com" 와 일치하는 신청이 없습니다')).toBeInTheDocument();
  });

  it("승인 성공 — 성공 toast를 보낸다", () => {
    listState = { data: { items: [APPLICATION], total: 1 }, isPending: false, error: null };
    render(<WaitlistAdminView />);

    fireEvent.click(screen.getByRole("button", { name: "더미 승인" }));
    approveCallbacks.onSuccess?.({ email: APPLICATION.email });

    expect(approveState.mutate).toHaveBeenCalledWith(APPLICATION.id);
    expect(toastSuccess).toHaveBeenCalledWith(`초대 발송: ${APPLICATION.email}`);
    expect(toastError).not.toHaveBeenCalled();
  });

  it("승인 실패 ApiError — 실패 toast를 보낸다", () => {
    listState = { data: { items: [APPLICATION], total: 1 }, isPending: false, error: null };
    render(<WaitlistAdminView />);

    approveCallbacks.onError?.(new ApiError(422, "invalid_status", "이미 처리된 신청입니다."));

    expect(toastError).toHaveBeenCalledWith("이미 처리된 신청입니다.");
    expect(toastSuccess).not.toHaveBeenCalled();
  });

  it("데이터 0건 — 빈 상태를 렌더하고 던지지 않는다", () => {
    listState = { data: { items: [], total: 0 }, isPending: false, error: null };

    expect(() => render(<WaitlistAdminView />)).not.toThrow();
    expect(screen.getByTestId("waitlist-empty-state")).toBeInTheDocument();
  });

  it("양성 대조 — 두 훅이 호출되고 렌더 텍스트가 비어 있지 않다", () => {
    listState = { data: { items: [APPLICATION], total: 1 }, isPending: false, error: null };
    const { container } = render(<WaitlistAdminView />);

    expect(useAdminWaitlistList).toHaveBeenCalled();
    expect(useApproveWaitlist).toHaveBeenCalled();
    expect(container.textContent?.trim()).not.toBe("");
  });
});
