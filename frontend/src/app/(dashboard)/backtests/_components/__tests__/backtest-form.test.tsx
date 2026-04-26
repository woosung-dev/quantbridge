import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";

import { BacktestForm } from "../backtest-form";

const strategies = {
  data: {
    items: [
      { id: "abc", name: "Test strategy", parse_status: "ok" },
      { id: "xyz", name: "Other", parse_status: "ok" },
    ],
  },
};

let mockSearchParams = new URLSearchParams();
const routerPush = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: routerPush, replace: vi.fn(), refresh: vi.fn() }),
  useSearchParams: () => mockSearchParams,
}));

vi.mock("@/features/strategy/hooks", () => ({
  useStrategies: () => strategies,
}));

// `useCreateBacktest` 는 호출 직전에 전달된 onSuccess/onError 콜백을 캡처해
// 테스트가 mutation 결과(성공/실패) 시점을 임의로 트리거할 수 있도록 한다.
// 표준 RHF + React Query 패턴 + Sprint 13 Phase C 422 처리 검증을 위해 필요.
type CapturedOpts = {
  onSuccess?: (data: { backtest_id: string }) => void;
  onError?: (err: Error) => void;
};
const capturedOpts: { current: CapturedOpts } = { current: {} };
const mutate = vi.fn();

vi.mock("@/features/backtest/hooks", () => ({
  useCreateBacktest: (opts: CapturedOpts = {}) => {
    capturedOpts.current = opts;
    return { mutate, isPending: false };
  },
}));

// toast 는 module-level singleton 이라 모듈 자체를 mock 해 호출 여부만 검증한다.
const toastError = vi.fn();
const toastSuccess = vi.fn();
vi.mock("sonner", () => ({
  toast: {
    error: (...args: unknown[]) => toastError(...args),
    success: (...args: unknown[]) => toastSuccess(...args),
  },
}));

beforeEach(() => {
  mockSearchParams = new URLSearchParams();
  routerPush.mockReset();
  mutate.mockReset();
  toastError.mockReset();
  toastSuccess.mockReset();
  capturedOpts.current = {};
});

afterEach(() => {
  cleanup();
});

describe("BacktestForm — searchParams strategy_id 프리필", () => {
  it("searchParams strategy_id=abc 일 때 숨김 input value 가 'abc'", () => {
    mockSearchParams = new URLSearchParams("strategy_id=abc");
    const { container } = render(<BacktestForm />);

    const hidden = container.querySelector<HTMLInputElement>(
      'input[type="hidden"][name="strategy_id"]',
    );
    expect(hidden).not.toBeNull();
    expect(hidden?.value).toBe("abc");
  });

  it("searchParams 없을 때 초기값은 빈 문자열 (placeholder 노출)", () => {
    mockSearchParams = new URLSearchParams();
    const { container } = render(<BacktestForm />);

    const hidden = container.querySelector<HTMLInputElement>(
      'input[type="hidden"][name="strategy_id"]',
    );
    expect(hidden?.value).toBe("");
    expect(screen.getByText(/전략을 선택하세요/)).toBeInTheDocument();
  });
});

describe("BacktestForm — Sprint 13 Phase C inline error UX", () => {
  it("mode:onChange — period_start 입력 후 변경되면 period_end 누락 인라인 에러가 첫 제출 전에도 노출된다", async () => {
    mockSearchParams = new URLSearchParams("strategy_id=abc");
    render(<BacktestForm />);

    // period_end 를 먼저 건드려 dirty/touched 상태로 만든 뒤 비워서 required 트리거.
    const endInput = screen.getByLabelText("종료일") as HTMLInputElement;
    await act(async () => {
      fireEvent.change(endInput, { target: { value: "2026-01-10" } });
      fireEvent.change(endInput, { target: { value: "" } });
    });

    // mode:"onChange" → 첫 submit 없이도 inline 메시지가 떠야 한다.
    expect(await screen.findByText("종료일을 입력하세요")).toBeInTheDocument();
  });

  it("422 백엔드 응답 → setError root.serverError → form-level inline 에러 메시지 노출", async () => {
    mockSearchParams = new URLSearchParams("strategy_id=abc");
    render(<BacktestForm />);

    // 필수 입력값을 채워 RHF resolver 통과 후 mutate 가 호출되도록 한다.
    await act(async () => {
      fireEvent.change(screen.getByLabelText("심볼"), {
        target: { value: "BTC/USDT" },
      });
      fireEvent.change(screen.getByLabelText("시작일"), {
        target: { value: "2026-01-01" },
      });
      fireEvent.change(screen.getByLabelText("종료일"), {
        target: { value: "2026-01-31" },
      });
      fireEvent.change(screen.getByLabelText("초기 자본 (USDT)"), {
        target: { value: "10000" },
      });
      fireEvent.submit(screen.getByLabelText("backtest-form"));
    });

    // RHF validate → handleSubmit → onSubmit → mutate.
    // 비동기 validate 가 끝난 뒤 capturedOpts.current.onError 가 세팅된다.
    await vi.waitFor(() => {
      expect(mutate).toHaveBeenCalledTimes(1);
    });

    // 백엔드가 ApiError(status=422, message="date out of range") 로 reject 했다고 가정.
    const err = Object.assign(new Error("date out of range"), { status: 422 });

    expect(capturedOpts.current.onError).toBeDefined();
    act(() => {
      capturedOpts.current.onError?.(err);
    });

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("date out of range");
    // 422 는 toast 가 아닌 inline 에러로만 처리되어야 한다.
    expect(toastError).not.toHaveBeenCalled();
  });

  it("happy path — onSuccess → router.push(/backtests/{id})", async () => {
    mockSearchParams = new URLSearchParams("strategy_id=abc");
    render(<BacktestForm />);

    await act(async () => {
      fireEvent.change(screen.getByLabelText("심볼"), {
        target: { value: "BTC/USDT" },
      });
      fireEvent.change(screen.getByLabelText("시작일"), {
        target: { value: "2026-01-01" },
      });
      fireEvent.change(screen.getByLabelText("종료일"), {
        target: { value: "2026-01-31" },
      });
      fireEvent.change(screen.getByLabelText("초기 자본 (USDT)"), {
        target: { value: "10000" },
      });
      fireEvent.submit(screen.getByLabelText("backtest-form"));
    });

    await vi.waitFor(() => {
      expect(mutate).toHaveBeenCalledTimes(1);
    });

    expect(capturedOpts.current.onSuccess).toBeDefined();
    act(() => {
      capturedOpts.current.onSuccess?.({ backtest_id: "bt-42" });
    });

    expect(routerPush).toHaveBeenCalledWith("/backtests/bt-42");
    expect(toastSuccess).toHaveBeenCalledWith("백테스트 요청됨");
  });
});
