/**
 * Sprint 31 BL-162a — BacktestForm 비용 시뮬레이션 + 마진 사용자 입력 검증.
 *
 * TradingView strategy 속성 패턴 대응. 4 신규 input field (수수료/슬리피지/
 * 레버리지/펀딩) + Bybit Perpetual taker 표준 default + validation + form 제출
 * payload 정합 + 모바일 320px 레이아웃.
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

describe("BacktestForm — Sprint 31 BL-162a 비용/마진 입력", () => {
  it("4 신규 input field 기본값 = Bybit Perpetual taker 표준", () => {
    render(<BacktestForm />);

    const fees = screen.getByLabelText(
      /수수료 \(소수, 0.001 = 0.10%\)/,
    ) as HTMLInputElement;
    const slippage = screen.getByLabelText(
      /슬리피지 \(소수, 0.0005 = 0.05%\)/,
    ) as HTMLInputElement;
    const leverage = screen.getByLabelText(
      /레버리지 \(배, 1 = 현물\)/,
    ) as HTMLInputElement;
    const funding = screen.getByLabelText(
      /펀딩비 반영/,
    ) as HTMLInputElement;

    // Bybit/OKX taker 표준 default
    expect(fees.value).toBe("0.001");
    expect(slippage.value).toBe("0.0005");
    expect(leverage.value).toBe("1");
    expect(funding.checked).toBe(true);
  });

  it("section 헤더 — 비용 시뮬레이션 + 마진 / 레버리지 (TradingView 패턴)", () => {
    render(<BacktestForm />);

    // 섹션 aria-label 정합 (TradingView strategy 속성 패턴)
    expect(screen.getByLabelText("비용 시뮬레이션")).toBeInTheDocument();
    expect(screen.getByLabelText("마진 / 레버리지")).toBeInTheDocument();
    // 헤더 텍스트 노출
    expect(screen.getByText("비용 시뮬레이션")).toBeInTheDocument();
    expect(screen.getByText("마진 / 레버리지")).toBeInTheDocument();
  });

  it("사용자 입력 후 form 제출 → mutate 가 4 신규 필드 포함 payload 로 호출", async () => {
    render(<BacktestForm />);

    // 기본 필수 + 신규 4 필드 입력
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
      fireEvent.change(screen.getByLabelText(/레버리지 \(배, 1 = 현물\)/), {
        target: { value: "10" },
      });
      fireEvent.click(screen.getByLabelText(/펀딩비 반영/));

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
    expect(payload.leverage).toBe(10);
    expect(payload.include_funding).toBe(false); // toggled OFF
    // 기존 필드 보존 정합
    expect(payload.strategy_id).toBe("abc");
    expect(payload.symbol).toBe("BTC/USDT");
    expect(payload.initial_capital).toBe(10000);
  });

  it("validation — leverage 200 (>125) 입력 시 inline error 표시 + mutate 미호출", async () => {
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
      fireEvent.change(screen.getByLabelText(/레버리지 \(배, 1 = 현물\)/), {
        target: { value: "200" },
      });
      fireEvent.submit(screen.getByLabelText("backtest-form"));
    });

    expect(
      await screen.findByText(/1 ~ 125 범위여야 합니다/),
    ).toBeInTheDocument();
    expect(mutate).not.toHaveBeenCalled();
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

  it("section data-testid + 모바일 1열 grid (반응형 sm:grid-cols-2)", () => {
    render(<BacktestForm />);

    const costSection = screen.getByTestId("backtest-form-cost-section");
    const marginSection = screen.getByTestId("backtest-form-margin-section");

    expect(costSection).toBeInTheDocument();
    expect(marginSection).toBeInTheDocument();

    // grid 컨테이너 — 모바일 1열, sm 2열 (Tailwind responsive 패턴)
    // .ai/stacks/nextjs-shared.md §4 — 320px 가로 스크롤 회피.
    const costGrid = costSection.querySelector(".grid");
    const marginGrid = marginSection.querySelector(".grid");
    expect(costGrid?.className).toMatch(/grid-cols-1/);
    expect(costGrid?.className).toMatch(/sm:grid-cols-2/);
    expect(marginGrid?.className).toMatch(/grid-cols-1/);
    expect(marginGrid?.className).toMatch(/sm:grid-cols-2/);
  });
});
