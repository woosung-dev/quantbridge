/**
 * BacktestForm 자본/체결 입력 — C 이식(W3-A) 라벨·구조 반영.
 *
 * 비용(테이커 수수료/슬리피지) 입력 + 시뮬레이션 모델 info + payload default 자동 채움 +
 * 주문 크기 방식(default_qty_type/value) 을 검증한다. 폼 로직은 재스킨 전과 동일하다.
 */
import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";

import { BacktestForm } from "@/features/backtest/components/forms/backtest-form";

const strategies = {
  data: {
    items: [{ id: "abc", name: "Test strategy", parse_status: "ok" }],
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
  useStrategy: () => ({ data: null, isLoading: false, isError: false }),
}));

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

vi.mock("sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}));

beforeEach(() => {
  mockSearchParams = new URLSearchParams("strategy_id=abc");
  routerPush.mockReset();
  mutate.mockReset();
  capturedOpts.current = {};
});

afterEach(() => {
  cleanup();
});

describe("BacktestForm — 자본과 체결 입력 (C 이식 W3-A)", () => {
  it("수수료/슬리피지 기본값과 1배 레버리지 입력을 표시한다", () => {
    render(<BacktestForm />);

    const fees = screen.getByLabelText("테이커 수수료") as HTMLInputElement;
    const slippage = screen.getByLabelText("슬리피지") as HTMLInputElement;
    const leverage = screen.getByLabelText("레버리지 (배)") as HTMLInputElement;

    expect(fees.value).toBe("0.00055");
    expect(slippage.value).toBe("0.00014");
    expect(leverage.value).toBe("1");
    expect(leverage).toHaveAttribute("min", "1");
    expect(leverage).toHaveAttribute("max", "125");
    expect(leverage).toHaveAttribute("step", "0.01");
    expect(screen.queryByTestId("backtest-leverage-notice")).not.toBeInTheDocument();
  });

  it("레버리지 1배 초과 시 프리뷰와 모델·시맨틱·Live 구분 고지를 표시한다", async () => {
    render(<BacktestForm />);

    await act(async () => {
      fireEvent.change(screen.getByLabelText("레버리지 (배)"), {
        target: { value: "10" },
      });
    });

    expect(screen.getByTestId("backtest-leverage-notice")).toBeInTheDocument();
    expect(screen.getByText("필요 증거금 = 포지션가치의 10.0%")).toBeInTheDocument();
    expect(screen.getByText("청산가는 진입가에서 약 9.50% 역행 지점")).toBeInTheDocument();
    expect(screen.getByText(/플랫 유지증거금률 0.5%/)).toBeInTheDocument();
    expect(screen.getByText(/레버리지는 주문 수량을 바꾸지 않습니다/)).toBeInTheDocument();
    expect(screen.getByText(/전략의 Live Settings 레버리지와 별개/)).toBeInTheDocument();
  });

  it("form 제출 → payload 의 leverage / include_funding default 자동 채움", async () => {
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
      fireEvent.change(screen.getByLabelText("레버리지 (배)"), {
        target: { value: "2.5" },
      });
      fireEvent.change(screen.getByLabelText("테이커 수수료"), {
        target: { value: "0.0006" },
      });
      fireEvent.change(screen.getByLabelText("슬리피지"), {
        target: { value: "0.0001" },
      });

      fireEvent.submit(screen.getByLabelText("backtest-form"));
    });

    await vi.waitFor(() => {
      expect(mutate).toHaveBeenCalledTimes(1);
    });

    const payload = mutate.mock.calls[0]![0] as Record<string, unknown>;
    expect(payload.fees_pct).toBe(0.0006);
    expect(payload.slippage_pct).toBe(0.0001);
    expect(payload.leverage).toBe(2.5);
    expect(payload.include_funding).toBe(true);
    expect(payload.strategy_id).toBe("abc");
    expect(payload.symbol).toBe("BTC/USDT");
    expect(payload.initial_capital).toBe(10000);
  });

  it("펀딩 반영 해제 후 제출 → payload include_funding=false", async () => {
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
      fireEvent.click(screen.getByRole("checkbox", { name: /펀딩 반영/ }));
      fireEvent.submit(screen.getByLabelText("backtest-form"));
    });

    await vi.waitFor(() => {
      expect(mutate).toHaveBeenCalledTimes(1);
    });

    const payload = mutate.mock.calls[0]![0] as Record<string, unknown>;
    expect(payload.include_funding).toBe(false);
  });

  it("펀딩 반영 체크박스가 활성화되고 실측 데이터 안내를 표시", () => {
    render(<BacktestForm />);

    expect(screen.getByRole("checkbox", { name: /펀딩 반영/ })).toBeEnabled();
    expect(
      screen.getByText(/Bybit 실측 펀딩 데이터를 사용하며/),
    ).toBeInTheDocument();
  });

  it("validation — fees_pct -0.1 (음수) 입력 시 inline error", async () => {
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
      fireEvent.change(screen.getByLabelText("테이커 수수료"), {
        target: { value: "-0.1" },
      });
      fireEvent.submit(screen.getByLabelText("backtest-form"));
    });

    expect(
      await screen.findByText(/0 ~ 0.01 \(1%\) 범위여야 합니다/),
    ).toBeInTheDocument();
    expect(mutate).not.toHaveBeenCalled();
  });

  it("주문 크기 방식 — default_qty_type dropdown + value 입력", () => {
    render(<BacktestForm />);
    expect(screen.getByLabelText("주문 크기 기준")).toBeInTheDocument();
    expect(screen.getByText("자기자본 비율")).toBeInTheDocument();
    expect(screen.getByText("고정 금액 (USDT)")).toBeInTheDocument();
    expect(screen.getByText("고정 수량")).toBeInTheDocument();
    const valueInput = screen.getByLabelText("값") as HTMLInputElement;
    expect(valueInput).toBeInTheDocument();
    expect(valueInput.value).toBe("10");
    expect(
      screen.getByTestId("backtest-form-sizing-source-section"),
    ).toBeInTheDocument();
  });

  it("주문 크기 방식 — form 제출 → payload 에 default_qty_type/value 포함", async () => {
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
      fireEvent.change(screen.getByLabelText("주문 크기 기준"), {
        target: { value: "strategy.cash" },
      });
      fireEvent.change(screen.getByLabelText("값"), {
        target: { value: "100" },
      });
      fireEvent.submit(screen.getByLabelText("backtest-form"));
    });

    await vi.waitFor(() => {
      expect(mutate).toHaveBeenCalledTimes(1);
    });

    const payload = mutate.mock.calls[0]![0] as Record<string, unknown>;
    expect(payload.default_qty_type).toBe("strategy.cash");
    expect(payload.default_qty_value).toBe(100);
  });

  it("자본과 체결 필드가 C 디자인 언어 .field-grid 로 렌더된다", () => {
    render(<BacktestForm />);

    const costSection = screen.getByTestId("backtest-form-cost-section");
    const leverageSection = screen.getByTestId("backtest-form-leverage-section");
    expect(costSection).toBeInTheDocument();
    expect(leverageSection).toBeInTheDocument();

    // C 이식 폼 필드는 Tailwind grid 가 아니라 프로토타입 .field-grid 를 소비한다.
    const grid = costSection.querySelector(".field-grid");
    expect(grid).not.toBeNull();
  });
});
