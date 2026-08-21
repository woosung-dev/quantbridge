import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";

import { BacktestForm } from "@/features/backtest/components/forms/backtest-form";

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
  // Sprint 38 BL-188 v3 — BacktestForm 가 useStrategy fetch (settings prefill).
  // 본 테스트 묶음은 sizing UI 와 무관 — null 반환으로 manual 기본 동작 유지.
  useStrategy: () => ({ data: null, isLoading: false, isError: false }),
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
      fireEvent.change(screen.getByLabelText("초기 자본"), {
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
      fireEvent.change(screen.getByLabelText("초기 자본"), {
        target: { value: "10000" },
      });
      fireEvent.submit(screen.getByLabelText("backtest-form"));
    });

    await vi.waitFor(() => {
      expect(mutate).toHaveBeenCalledTimes(1);
    });

    // backend Phase A.0: ApiError.detail = readErrorBody 결과 =
    // { detail: { code, detail, unsupported_builtins: [...] } }
    const err = Object.assign(new Error("Strategy contains unsupported Pine built-ins"), {
      status: 422,
      detail: {
        detail: {
          code: "strategy_not_runnable",
          detail: "Strategy contains unsupported Pine built-ins: heikinashi, security, max",
          unsupported_builtins: ["heikinashi", "security", "max"],
        },
      },
    });

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
    expect(screen.queryByTestId("backtest-form-server-error")).not.toBeInTheDocument();
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
      fireEvent.change(screen.getByLabelText("초기 자본"), {
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
    expect(screen.queryByTestId("backtest-form-unsupported-card")).not.toBeInTheDocument();
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
      fireEvent.change(screen.getByLabelText("초기 자본"), {
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

    expect(screen.queryByTestId("backtest-form-unsupported-card")).not.toBeInTheDocument();
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
      fireEvent.change(screen.getByLabelText("초기 자본"), {
        target: { value: "10000" },
      });
      fireEvent.submit(screen.getByLabelText("backtest-form"));
    });

    await vi.waitFor(() => {
      expect(mutate).toHaveBeenCalledTimes(1);
    });

    const err = Object.assign(new Error("API 500 /backtests"), {
      status: 500,
      detail: { detail: "Internal server error. 잠시 후 다시 시도해 주세요." },
    });

    act(() => {
      capturedOpts.current.onError?.(err);
    });

    // Sprint 32 E (BL-163): 500+ 표준 toast — backend `{detail: <msg>}` 포맷에서
    // 사용자 친화 메시지 + ADR-003 supported list 안내 포함.
    expect(toastError).toHaveBeenCalledTimes(1);
    const firstCall = toastError.mock.calls[0];
    const callArg = (firstCall ? firstCall[0] : "") as string;
    expect(callArg).toContain("백테스트 실행 중 오류 발생");
    expect(callArg).toContain("Internal server error");
    expect(callArg).toContain("지원 함수 목록 참조");
    expect(screen.queryByTestId("backtest-form-unsupported-card")).not.toBeInTheDocument();
    expect(screen.queryByTestId("backtest-form-server-error")).not.toBeInTheDocument();
  });

  // Sprint 32 E (BL-163) — 422 응답에 friendly_message 가 함께 오면 카드 헤더 노출.
  it("422 + friendly_message → 카드 헤더에 friendly_message + supported list 링크", async () => {
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
      fireEvent.change(screen.getByLabelText("초기 자본"), {
        target: { value: "10000" },
      });
      fireEvent.submit(screen.getByLabelText("backtest-form"));
    });

    await vi.waitFor(() => {
      expect(mutate).toHaveBeenCalledTimes(1);
    });

    const err = Object.assign(new Error("Strategy contains unsupported Pine built-ins"), {
      status: 422,
      detail: {
        detail: {
          code: "strategy_not_runnable",
          detail: "Strategy contains unsupported Pine built-ins: array.new_float",
          unsupported_builtins: ["array.new_float"],
          friendly_message:
            "이 strategy 는 미지원 Pine 빌트인을 포함합니다. array.new_float — Pine v6 collection types 미지원 (paradigm mismatch). ADR-003 supported list 참조.",
        },
      },
    });

    act(() => {
      capturedOpts.current.onError?.(err);
    });

    const card = await screen.findByTestId("backtest-form-unsupported-card");
    expect(card).toBeInTheDocument();
    const fmEl = await screen.findByTestId("backtest-form-friendly-message");
    expect(fmEl).toHaveTextContent("array.new_float");
    expect(fmEl).toHaveTextContent("Pine v6");
    // edit link — ADR-003 안내 텍스트 포함
    const editLink = screen.getByTestId("backtest-form-edit-strategy-link");
    expect(editLink).toHaveTextContent(/지원 함수 목록 참조/);
  });

  it("422 + degraded_calls → 동의 체크 후 allow_degraded_pine=true로 재제출", async () => {
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
      fireEvent.change(screen.getByLabelText("초기 자본"), {
        target: { value: "10000" },
      });
      fireEvent.submit(screen.getByLabelText("backtest-form"));
    });

    await vi.waitFor(() => {
      expect(mutate).toHaveBeenCalledTimes(1);
    });
    expect(mutate.mock.calls[0]?.[0]).not.toHaveProperty("allow_degraded_pine");

    const err = Object.assign(new Error("Strategy uses degraded functions"), {
      status: 422,
      detail: {
        detail: {
          code: "strategy_degraded",
          detail: "Strategy uses degraded Pine functions: heikinashi",
          degraded_calls: ["heikinashi"],
          friendly_message:
            "이 strategy 는 미지원 Pine 빌트인을 포함합니다. heikinashi — Trust Layer 위반 (결과 부정확 risk). ADR-003 supported list 참조.",
        },
      },
    });

    act(() => {
      capturedOpts.current.onError?.(err);
    });

    const card = await screen.findByTestId("backtest-form-degraded-card");
    expect(card).toHaveTextContent(/heikinashi/);
    expect(card).toHaveTextContent(/TradingView와 다를 수 있습니다/);
    const fmEl = await screen.findByTestId("backtest-form-friendly-message");
    expect(fmEl).toHaveTextContent("Trust Layer");

    const consent = screen.getByTestId("backtest-form-degraded-consent") as HTMLInputElement;
    expect(consent.checked).toBe(false);
    await act(async () => {
      fireEvent.click(consent);
      fireEvent.submit(screen.getByLabelText("backtest-form"));
    });

    await vi.waitFor(() => {
      expect(mutate).toHaveBeenCalledTimes(2);
    });
    expect(mutate.mock.calls[1]?.[0]).toMatchObject({ allow_degraded_pine: true });
  });

  // ★동의는 **그 전략에만** 유효하다 (2026-08-15 적대 리뷰 P2). 종전에는 전략과 무관한
  //   boolean 이라 전략 A 에서 동의한 뒤 B 로 바꿔 제출하면 B 요청에도 `true` 가 실렸다 —
  //   동의 문구는 「이 전략을 실행합니다」라고 말하는데.
  it("전략을 바꾸면 degraded 동의가 따라가지 않는다", async () => {
    mockSearchParams = new URLSearchParams("strategy_id=abc");
    render(<BacktestForm />);

    await act(async () => {
      fireEvent.change(screen.getByLabelText("심볼"), { target: { value: "BTC/USDT" } });
      fireEvent.change(screen.getByLabelText("시작일"), { target: { value: "2026-01-01" } });
      fireEvent.change(screen.getByLabelText("종료일"), { target: { value: "2026-01-31" } });
      fireEvent.change(screen.getByLabelText("초기 자본"), { target: { value: "10000" } });
      fireEvent.submit(screen.getByLabelText("backtest-form"));
    });
    await vi.waitFor(() => expect(mutate).toHaveBeenCalledTimes(1));

    const err = Object.assign(new Error("degraded"), {
      status: 422,
      detail: {
        detail: {
          code: "strategy_degraded",
          detail: "Strategy uses degraded Pine functions: heikinashi",
          degraded_calls: ["heikinashi"],
        },
      },
    });
    act(() => {
      capturedOpts.current.onError?.(err);
    });

    const consent = await screen.findByTestId("backtest-form-degraded-consent");
    await act(async () => {
      fireEvent.click(consent);
    });

    // 다른 전략으로 바꾼다 — 동의는 A 에 대한 것이었다.
    await act(async () => {
      fireEvent.change(screen.getByLabelText("전략"), { target: { value: "xyz" } });
      fireEvent.submit(screen.getByLabelText("backtest-form"));
    });
    await vi.waitFor(() => expect(mutate).toHaveBeenCalledTimes(2));

    expect(mutate.mock.calls[1]?.[0]).not.toHaveProperty("allow_degraded_pine");
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
      fireEvent.change(screen.getByLabelText("초기 자본"), {
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

// ---------------------------------------------------------------------------
// BL-698 — 제출이 실제로 mutate 에 도달하는가.
//
// ★위 묶음이 전부 `fireEvent.submit(form)` 인 것이 이 결함을 8일간 가렸다. submit 이벤트를
//   직접 디스패치하면 브라우저의 native constraint validation 을 **통째로 우회**한다.
//   실제 사용자는 요약 패널의 실행 버튼을 누르고, 그 경로에서는 폼이 constraint-invalid 이면
//   submit 이벤트가 **발화조차 하지 않는다** — handleSubmit 도, onSubmit 도, mutate 도 안 돈다.
//   그래서 증상이 「422 가 아니라 요청이 아예 안 나감」이었다.
//   회귀 커밋 753f4bf6(BL-603): fees 0.0005→0.00055 로 좁히면서 step="0.0001" 격자를 벗어났다.
// ---------------------------------------------------------------------------
describe("BacktestForm — 제출이 mutate 에 도달한다 (BL-698)", () => {
  it("요약 패널 실행 버튼 클릭이 create.mutate 를 호출한다", async () => {
    mockSearchParams = new URLSearchParams("strategy_id=abc");
    render(<BacktestForm />);

    await act(async () => {
      fireEvent.click(screen.getByTestId("backtest-submit"));
    });

    // ★`vi.waitFor` 를 쓰지 않는다. RHF handleSubmit 은 `await act` 안에서 마이크로태스크까지
    //   전부 flush 되므로 mutate 호출은 이 시점에 이미 확정이다. waitFor 를 끼우면 폴링 타임아웃이
    //   유일한 실패 표면이 되어 **결함이 아니라 지연으로도 red** 가 된다 — 상시 red 게이트를
    //   없애려는 회차가 새 flake 를 심으면 안 된다.
    expect(mutate).toHaveBeenCalledTimes(1);
  });

  it("기본값이 자기 step 격자를 위반하지 않는다 — 위반하면 제출이 조용히 삼켜진다", () => {
    const { container } = render(<BacktestForm />);

    for (const id of ["fees_pct", "slippage_pct", "initial_capital", "leverage"]) {
      const el = container.querySelector<HTMLInputElement>(`#${id}`);
      expect(el, `#${id} 가 렌더돼야 한다`).not.toBeNull();
      expect(el?.validity.stepMismatch, `#${id} stepMismatch`).toBe(false);
    }
  });

  it("step 격자 밖 레버리지(1.005)를 입력해도 제출이 막히지 않는다", async () => {
    // RHF validate 는 1~125 라 1.005 를 통과시킨다. native validation 이 살아 있으면
    // step="0.01" 격자를 벗어났다는 이유로 submit 이벤트가 삼켜져 사용자는 아무 반응도 못 본다.
    mockSearchParams = new URLSearchParams("strategy_id=abc");
    const { container } = render(<BacktestForm />);

    await act(async () => {
      fireEvent.change(container.querySelector<HTMLInputElement>("#leverage")!, {
        target: { value: "1.005" },
      });
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId("backtest-submit"));
    });

    expect(mutate).toHaveBeenCalledTimes(1);
  });
});
