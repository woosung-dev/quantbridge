// ErrorRecoveryBox 3 variant 검증 — Sprint 43 W8

import { describe, expect, it, vi, afterEach } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { ErrorRecoveryBox } from "../error-recovery-box";

const mockToastSuccess = vi.fn();
const mockToastError = vi.fn();

vi.mock("sonner", () => ({
  toast: {
    success: (...args: unknown[]) => mockToastSuccess(...args),
    error: (...args: unknown[]) => mockToastError(...args),
  },
}));

afterEach(() => {
  cleanup();
  mockToastSuccess.mockReset();
  mockToastError.mockReset();
});

describe("ErrorRecoveryBox — variant 분기", () => {
  it("variant 404 — 추천 카드 3개 + 검색 input + chips 렌더", () => {
    render(<ErrorRecoveryBox variant="404" />);
    const box = screen.getByTestId("error-recovery-box");
    expect(box).toHaveAttribute("data-variant", "404");
    expect(screen.getByText("내 전략 보기")).toBeInTheDocument();
    expect(screen.getByText("백테스트 결과")).toBeInTheDocument();
    // "대시보드" 는 helpful 카드 title + chip 두 곳에 존재 → 카드 link href 로 검증
    expect(screen.getByRole("link", { name: /내 전략 보기/ })).toHaveAttribute("href", "/strategies");
    expect(screen.getByRole("link", { name: /백테스트 결과/ })).toHaveAttribute("href", "/backtests");
    expect(screen.getByLabelText("원하는 기능을 검색하세요")).toBeInTheDocument();
  });

  it("variant 500 — 요청ID 복사 버튼 클릭 시 clipboard + sonner toast.success", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });

    render(
      <ErrorRecoveryBox
        variant="500"
        requestId="req_abc123xyz789"
        occurredAt="2026-04-14 14:23:45 KST"
      />,
    );

    expect(screen.getByTestId("error-recovery-request-id")).toHaveTextContent("req_abc123xyz789");
    fireEvent.click(screen.getByLabelText("요청 ID 복사"));

    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith("req_abc123xyz789");
      expect(mockToastSuccess).toHaveBeenCalled();
    });
    expect(mockToastError).not.toHaveBeenCalled();
  });

  it("variant 503 — ETA + 진행바 (aria-valuenow=60) + 업데이트 목록", () => {
    render(
      <ErrorRecoveryBox
        variant="503"
        etaLabel="약 15분 남음"
        startedAt="14:10 KST"
        finishesAt="14:40 KST"
        progressPercent={60}
        updates={[
          { status: "done", label: "백테스트 엔진 성능 개선" },
          { status: "progress", label: "DB 정리 중" },
        ]}
      />,
    );

    expect(screen.getByText("약 15분 남음")).toBeInTheDocument();
    const bar = screen.getByRole("progressbar");
    expect(bar).toHaveAttribute("aria-valuenow", "60");
    expect(screen.getByText("백테스트 엔진 성능 개선")).toBeInTheDocument();
    expect(screen.getByText("DB 정리 중")).toBeInTheDocument();
  });
});
