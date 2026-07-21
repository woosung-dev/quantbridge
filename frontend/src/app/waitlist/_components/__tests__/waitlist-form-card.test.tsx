// WaitlistFormCard (C 이식) — 상태 3종: 기본 / 필드 검증 에러(role=alert) / 등록 완료(state-box).
// useCreateWaitlist 훅을 모킹해 성공 경로를 제어한다(공개 제출이라 인증 불필요).
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

let capturedOnSuccess: ((d: unknown) => void) | undefined;
const mutate = vi.fn(() => capturedOnSuccess?.({ id: "wl-1", status: "pending" }));
vi.mock("@/features/waitlist/hooks", () => ({
  useCreateWaitlist: (opts: { onSuccess?: (d: unknown) => void }) => {
    capturedOnSuccess = opts.onSuccess;
    return { mutate, isPending: false };
  },
}));

import { WaitlistFormCard } from "../waitlist-form-card";

describe("WaitlistFormCard", () => {
  afterEach(() => {
    cleanup();
    mutate.mockClear();
  });

  it("기본 상태 — 이메일/구독/자본/경험 필드 + 등록 버튼, 에러 미노출", () => {
    render(<WaitlistFormCard />);
    expect(screen.getByLabelText("이메일 주소")).toBeInTheDocument();
    expect(screen.getByLabelText("TradingView 구독")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "등록" })).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("defaultEmail 프리필", () => {
    render(<WaitlistFormCard defaultEmail="woosung@example.com" />);
    expect(screen.getByLabelText("이메일 주소")).toHaveValue("woosung@example.com");
  });

  it("빈 제출 — 검증 에러(role=alert) 노출 + mutate 미호출", async () => {
    render(<WaitlistFormCard />);
    fireEvent.click(screen.getByRole("button", { name: "등록" }));
    await waitFor(() => expect(screen.getAllByRole("alert").length).toBeGreaterThan(0));
    expect(mutate).not.toHaveBeenCalled();
  });

  it("유효 제출 — 등록 완료 state-box 렌더", async () => {
    render(<WaitlistFormCard />);
    fireEvent.change(screen.getByLabelText("이메일 주소"), {
      target: { value: "woosung@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/풀고 싶은 문제/), {
      target: { value: "알림을 수동으로 옮기다 진입을 놓칩니다." },
    });
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: "등록" }));

    expect(await screen.findByText("등록되었습니다.")).toBeInTheDocument();
    expect(mutate).toHaveBeenCalledTimes(1);
  });
});
