/**
 * Sprint 37 BL-187 — BacktestForm 폼 simplify (BL-185 spot-equivalent 정합).
 *
 * 이전 (Sprint 31 BL-162a): leverage / include_funding input 검증.
 * 현재: BL-185 spot-equivalent 결정 후 두 필드 misleading → form 에서 제거 +
 * "모델: Spot-equivalent" visible info row 노출 + payload 는 default
 * (leverage=1, include_funding=true) 자동 채움 (assumptions-card graceful
 * upgrade 패턴 보존).
 *
 * 검증: 비용 (수수료/슬리피지) 입력 + 모델 info row + payload default 자동.
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

import { BacktestForm } from "../backtest-form";

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

describe("BacktestForm — Sprint 37 BL-187 spot-equivalent 정합", () => {
  it("비용 시뮬레이션 input 기본값 = Bybit Perpetual taker 표준 (fees/slippage 만)", () => {
    render(<BacktestForm />);

    const fees = screen.getByLabelText(
      /수수료 \(소수, 0.001 = 0.10%\)/,
    ) as HTMLInputElement;
    const slippage = screen.getByLabelText(
      /슬리피지 \(소수, 0.0005 = 0.05%\)/,
    ) as HTMLInputElement;

    // Bybit/OKX taker 표준 default
    expect(fees.value).toBe("0.001");
    expect(slippage.value).toBe("0.0005");

    // BL-187: leverage / 펀딩비 input row 제거 → label 미존재
    expect(screen.queryByLabelText(/레버리지 \(배, 1 = 현물\)/)).toBeNull();
    expect(screen.queryByLabelText(/펀딩비 반영/)).toBeNull();
  });

  it("section 헤더 — 비용 시뮬레이션 + 시뮬레이션 모델 (BL-187a 라벨 simplify)", () => {
    render(<BacktestForm />);

    // 비용 시뮬레이션 섹션 존재
    expect(screen.getByLabelText("비용 시뮬레이션")).toBeInTheDocument();
    expect(screen.getByText("비용 시뮬레이션")).toBeInTheDocument();

    // BL-187: 마진/레버리지 섹션 → 시뮬레이션 모델
    expect(screen.getByLabelText("시뮬레이션 모델")).toBeInTheDocument();
    // BL-187a: 라벨 "Spot-equivalent" → "1x · 롱/숏" (사용자 오해 회피)
    expect(screen.getByText("모델: 1x · 롱/숏")).toBeInTheDocument();
    expect(screen.queryByText("모델: Spot-equivalent")).toBeNull();
    // 롱/숏 둘 다 가능 명시
    expect(
      screen.getByText(/롱\/숏 모두 가능|자기자본 한도/i),
    ).toBeInTheDocument();
    // BL-186 후속 명시 (사용자 trust)
    expect(screen.getByText(/BL-186 후속/)).toBeInTheDocument();
  });

  it("form 제출 → mutate payload 의 leverage / include_funding default 자동 채움", async () => {
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
      fireEvent.change(
        screen.getByLabelText(/수수료 \(소수, 0.001 = 0.10%\)/),
        { target: { value: "0.0006" } },
      );
      fireEvent.change(
        screen.getByLabelText(/슬리피지 \(소수, 0.0005 = 0.05%\)/),
        { target: { value: "0.0001" } },
      );

      fireEvent.submit(screen.getByLabelText("backtest-form"));
    });

    await vi.waitFor(() => {
      expect(mutate).toHaveBeenCalledTimes(1);
    });

    const firstCall = mutate.mock.calls[0];
    expect(firstCall).toBeDefined();
    const payload = firstCall![0] as Record<string, unknown>;
    expect(payload.fees_pct).toBe(0.0006);
    expect(payload.slippage_pct).toBe(0.0001);
    // BL-187: 두 필드 form 입력 X → default 값 자동 (graceful upgrade 호환)
    expect(payload.leverage).toBe(1);
    expect(payload.include_funding).toBe(true);
    // 기존 필드 정합
    expect(payload.strategy_id).toBe("abc");
    expect(payload.symbol).toBe("BTC/USDT");
    expect(payload.initial_capital).toBe(10000);
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
      fireEvent.change(screen.getByLabelText("초기 자본 (USDT)"), {
        target: { value: "10000" },
      });
      fireEvent.change(
        screen.getByLabelText(/수수료 \(소수, 0.001 = 0.10%\)/),
        { target: { value: "-0.1" } },
      );
      fireEvent.submit(screen.getByLabelText("backtest-form"));
    });

    expect(
      await screen.findByText(/0 ~ 0.01 \(1%\) 범위여야 합니다/),
    ).toBeInTheDocument();
    expect(mutate).not.toHaveBeenCalled();
  });

  it("BL-188a: 기본 주문 크기 input (default_qty_type dropdown + value)", () => {
    render(<BacktestForm />);
    // dropdown 3 options 노출
    expect(screen.getByLabelText("type")).toBeInTheDocument();
    expect(
      screen.getByText("자기자본 % (percent_of_equity)"),
    ).toBeInTheDocument();
    expect(screen.getByText("고정 USDT (cash)")).toBeInTheDocument();
    expect(screen.getByText("고정 수량 (fixed)")).toBeInTheDocument();
    // value input 노출
    const valueInput = screen.getByLabelText("value") as HTMLInputElement;
    expect(valueInput).toBeInTheDocument();
    expect(valueInput.value).toBe("10");
    // section testid
    expect(
      screen.getByTestId("backtest-form-default-qty-section"),
    ).toBeInTheDocument();
    // Pine override 안내
    expect(
      screen.getByText(/Pine\s+code\s+의|미명시 시 아래 입력값/i),
    ).toBeInTheDocument();
  });

  it("BL-188a: form 제출 → payload 에 default_qty_type/value 포함", async () => {
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
      // dropdown 변경: percent_of_equity → cash
      fireEvent.change(screen.getByLabelText("type"), {
        target: { value: "strategy.cash" },
      });
      fireEvent.change(screen.getByLabelText("value"), {
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

  it("section data-testid + 모바일 1열 grid (반응형)", () => {
    render(<BacktestForm />);

    const costSection = screen.getByTestId("backtest-form-cost-section");
    // BL-187: margin section → model section (Spot-equivalent info row)
    const modelSection = screen.getByTestId("backtest-form-model-section");

    expect(costSection).toBeInTheDocument();
    expect(modelSection).toBeInTheDocument();

    // 비용 grid 1열 (모바일) / 2열 (sm+)
    const costGrid = costSection.querySelector(".grid");
    expect(costGrid?.className).toMatch(/grid-cols-1/);
    expect(costGrid?.className).toMatch(/sm:grid-cols-2/);
  });
});
