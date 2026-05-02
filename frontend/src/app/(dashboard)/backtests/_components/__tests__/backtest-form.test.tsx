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

  // Sprint 21 BL-095 — backend 422 의 unsupported_builtins (구조화 list) 가 있을 때
  // form-level error 가 아닌 친절 inline 카드 + edit link 노출.
  // codex G.0 P1 #5: FE 가 string split 하지 않고 list 직접 접근.
  it("422 + unsupported_builtins list → unsupported card + friendly hints + edit link", async () => {
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

    // backend Phase A.0: ApiError.detail = readErrorBody 결과 =
    // { detail: { code, detail, unsupported_builtins: [...] } }
    const err = Object.assign(
      new Error("Strategy contains unsupported Pine built-ins"),
      {
        status: 422,
        detail: {
          detail: {
            code: "strategy_not_runnable",
            detail:
              "Strategy contains unsupported Pine built-ins: heikinashi, security, max",
            unsupported_builtins: ["heikinashi", "security", "max"],
          },
        },
      },
    );

    expect(capturedOpts.current.onError).toBeDefined();
    act(() => {
      capturedOpts.current.onError?.(err);
    });

    const card = await screen.findByTestId("backtest-form-unsupported-card");
    expect(card).toBeInTheDocument();
    // 친절 hint 메시지 — heikinashi 는 corruption category 의 명확한 메시지
    expect(card).toHaveTextContent(/heikinashi/);
    expect(card).toHaveTextContent(/헤이켄아시 변환/);
    expect(card).toHaveTextContent(/security/);
    expect(card).toHaveTextContent(/max/);
    // Sprint 21 G.2 P2 — max/min/abs 권장 hint 제거 (alias ordering fix 후 부정확).
    // generic fallback 메시지에서 builtin 이름 자체만 노출.
    expect(card).toHaveTextContent(/미지원 빌트인/);
    // strategy 편집 링크 — 선택된 strategy_id 'abc' 의 edit?tab=parse
    const editLink = screen.getByTestId("backtest-form-edit-strategy-link");
    expect(editLink.getAttribute("href")).toBe("/strategies/abc/edit?tab=parse");
    // 422 는 toast 가 아닌 inline 카드로만 처리.
    expect(toastError).not.toHaveBeenCalled();
    // Sprint 13 의 root.serverError fallback 미사용 (구조화 list 우선).
    expect(
      screen.queryByTestId("backtest-form-server-error"),
    ).not.toBeInTheDocument();
  });

  it("422 + empty unsupported_builtins → fallback root.serverError (no card)", async () => {
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

    const err = Object.assign(new Error("date out of range"), {
      status: 422,
      detail: {
        detail: {
          code: "validation_error",
          detail: "date out of range",
          unsupported_builtins: [],
        },
      },
    });

    act(() => {
      capturedOpts.current.onError?.(err);
    });

    // 빈 list — fallback root.serverError 카드 미노출
    expect(
      screen.queryByTestId("backtest-form-unsupported-card"),
    ).not.toBeInTheDocument();
    const serverErr = await screen.findByTestId("backtest-form-server-error");
    expect(serverErr).toHaveTextContent("date out of range");
  });

  it("422 + unsupported_builtins missing → fallback root.serverError", async () => {
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

    // detail 자체가 없는 경우 (legacy backend 또는 다른 422 source)
    const err = Object.assign(new Error("legacy 422"), { status: 422 });

    act(() => {
      capturedOpts.current.onError?.(err);
    });

    expect(
      screen.queryByTestId("backtest-form-unsupported-card"),
    ).not.toBeInTheDocument();
    const serverErr = await screen.findByTestId("backtest-form-server-error");
    expect(serverErr).toHaveTextContent("legacy 422");
  });

  it("non-422 (500) → toast.error (no card, no inline)", async () => {
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

    const err = Object.assign(new Error("Internal Server Error"), {
      status: 500,
    });

    act(() => {
      capturedOpts.current.onError?.(err);
    });

    expect(toastError).toHaveBeenCalledWith(
      expect.stringContaining("Internal Server Error"),
    );
    expect(
      screen.queryByTestId("backtest-form-unsupported-card"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("backtest-form-server-error"),
    ).not.toBeInTheDocument();
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
