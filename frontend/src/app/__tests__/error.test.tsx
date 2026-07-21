// error(500) 루트 바운더리 — screen-13 §02 C 언어 구조 이식 검증(W3-H). 섹션 순서·핵심 시맨틱
// 클래스·요청 ID 유무 분기·복사·재시도를 assert 한다.

import { describe, expect, it, vi, afterEach } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import GlobalError from "../error";

const mockToastSuccess = vi.fn();
const mockToastError = vi.fn();
const mockToast = vi.fn();

vi.mock("sonner", () => ({
  toast: Object.assign((...args: unknown[]) => mockToast(...args), {
    success: (...args: unknown[]) => mockToastSuccess(...args),
    error: (...args: unknown[]) => mockToastError(...args),
  }),
}));

afterEach(() => {
  cleanup();
  mockToastSuccess.mockReset();
  mockToastError.mockReset();
  mockToast.mockReset();
});

function makeError(digest?: string): Error & { digest?: string } {
  const e = new Error("boom") as Error & { digest?: string };
  if (digest) e.digest = digest;
  return e;
}

describe("GlobalError — 500 C 구조", () => {
  it("아이브로 500 + h1 + 상태 박스(failed, role=alert) + 트러스트 그리드 + 액션 줄", () => {
    const { container } = render(<GlobalError error={makeError()} reset={vi.fn()} />);

    expect(container.querySelector(".eyebrow .num")).toHaveTextContent("500");
    expect(
      screen.getByRole("heading", { level: 1, name: "요청을 처리하지 못했습니다." }),
    ).toBeInTheDocument();

    const stateBox = screen.getByTestId("error-500-state");
    expect(stateBox).toHaveClass("state-box", "failed", "err-hero");
    expect(stateBox).toHaveAttribute("role", "alert");

    // 트러스트 그리드에 상태 코드 500 이 실제로 인쇄된다
    expect(container.querySelector(".trust-grid")).toBeInTheDocument();
    expect(container.textContent).toContain("상태 코드");
    // 액션 줄
    expect(container.querySelector(".err-actions")).toBeInTheDocument();
  });

  it("digest 없으면 요청 ID 는 무데이터 셀로 그리고 지어내지 않는다", () => {
    render(<GlobalError error={makeError()} reset={vi.fn()} />);
    const empty = screen.getByTestId("error-request-id-empty");
    expect(empty).toHaveClass("trust-val", "empty");
    expect(empty).toHaveAttribute("title");
    expect(screen.queryByTestId("error-request-id")).not.toBeInTheDocument();
  });

  it("digest 있으면 요청 ID 노출 + 복사 시 clipboard + toast.success", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });

    render(<GlobalError error={makeError("req_abc123xyz")} reset={vi.fn()} />);
    expect(screen.getByTestId("error-request-id")).toHaveTextContent("req_abc123xyz");

    fireEvent.click(screen.getByRole("button", { name: "요청 ID 복사" }));
    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith("req_abc123xyz");
      expect(mockToastSuccess).toHaveBeenCalled();
    });
    expect(mockToastError).not.toHaveBeenCalled();
  });

  it("다시 시도 버튼이 reset() 을 호출한다", () => {
    const reset = vi.fn();
    render(<GlobalError error={makeError()} reset={reset} />);
    fireEvent.click(screen.getByTestId("error-retry-button"));
    expect(reset).toHaveBeenCalledTimes(1);
  });
});
