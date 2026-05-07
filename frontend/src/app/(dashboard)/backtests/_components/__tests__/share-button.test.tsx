// 백테스트 공유 버튼 동작 테스트 — Sprint 41 Worker H
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mockCreateMutate = vi.fn();
const mockRevokeMutate = vi.fn();
const mockToastSuccess = vi.fn();
const mockToastError = vi.fn();
const mockClipboardWrite = vi.fn(() => Promise.resolve());

let createPending = false;
let createTrigger: "success" | "error" = "success";
let createError: Error | null = null;
let revokePending = false;

vi.mock("sonner", () => ({
  toast: {
    success: (...args: unknown[]) => mockToastSuccess(...args),
    error: (...args: unknown[]) => mockToastError(...args),
  },
}));

vi.mock("@/features/backtest/hooks", () => ({
  useCreateBacktestShare: (opts: {
    onSuccess?: (r: {
      backtest_id: string;
      share_token: string;
      share_url_path: string;
      revoked: boolean;
    }) => void;
    onError?: (e: Error) => void;
  }) => ({
    mutate: (id: string) => {
      mockCreateMutate(id);
      if (createTrigger === "error") {
        opts.onError?.(createError ?? new Error("create failed"));
        return;
      }
      opts.onSuccess?.({
        backtest_id: id,
        share_token: "tkn-abc",
        share_url_path: "/share/backtests/tkn-abc",
        revoked: false,
      });
    },
    isPending: createPending,
  }),
  useRevokeBacktestShare: (opts: {
    onSuccess?: () => void;
    onError?: (e: Error) => void;
  }) => ({
    mutate: (id: string) => {
      mockRevokeMutate(id);
      opts.onSuccess?.();
    },
    isPending: revokePending,
  }),
}));

import { ShareButton } from "../share-button";

beforeEach(() => {
  mockCreateMutate.mockClear();
  mockRevokeMutate.mockClear();
  mockToastSuccess.mockClear();
  mockToastError.mockClear();
  mockClipboardWrite.mockClear();
  createPending = false;
  revokePending = false;
  createTrigger = "success";
  createError = null;

  Object.defineProperty(window, "location", {
    writable: true,
    value: { origin: "https://quantbridge.app" },
  });
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText: mockClipboardWrite },
  });
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("ShareButton", () => {
  it("렌더 시 '공유' 버튼이 보인다", () => {
    render(<ShareButton backtestId="bt-1" />);
    expect(screen.getByRole("button", { name: /공유/ })).toBeInTheDocument();
  });

  it("isEnabled=false 시 disabled", () => {
    render(<ShareButton backtestId="bt-1" isEnabled={false} />);
    expect(screen.getByRole("button", { name: /공유/ })).toBeDisabled();
  });

  it("클릭 시 mutate 호출 + 토큰 url clipboard 복사 + 성공 토스트", async () => {
    render(<ShareButton backtestId="bt-1" />);
    fireEvent.click(screen.getByRole("button", { name: /공유/ }));

    expect(mockCreateMutate).toHaveBeenCalledWith("bt-1");
    await waitFor(() => {
      expect(mockClipboardWrite).toHaveBeenCalledWith(
        "https://quantbridge.app/share/backtests/tkn-abc",
      );
    });
    expect(mockToastSuccess).toHaveBeenCalled();
  });

  it("성공 후 '공유 취소' 버튼으로 변환 + 클릭 시 revoke", async () => {
    render(<ShareButton backtestId="bt-1" />);
    fireEvent.click(screen.getByRole("button", { name: /공유/ }));

    await waitFor(() => {
      expect(screen.getByText(/공유 중/)).toBeInTheDocument();
    });
    const revokeBtn = screen.getByRole("button", { name: /공유 취소/ });
    fireEvent.click(revokeBtn);

    expect(mockRevokeMutate).toHaveBeenCalledWith("bt-1");
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /^공유$/ })).toBeInTheDocument();
    });
  });

  it("mutation 실패 시 error toast 노출", () => {
    createTrigger = "error";
    createError = new Error("HTTP 500");
    render(<ShareButton backtestId="bt-1" />);
    fireEvent.click(screen.getByRole("button", { name: /공유/ }));

    expect(mockToastError).toHaveBeenCalledWith(
      "공유 링크 생성에 실패했습니다",
      expect.objectContaining({ description: "HTTP 500" }),
    );
  });

  it("createPending=true 시 disabled + '생성 중…' 표시", () => {
    createPending = true;
    render(<ShareButton backtestId="bt-1" />);
    const btn = screen.getByRole("button", { name: /생성 중/ });
    expect(btn).toBeDisabled();
  });
});
