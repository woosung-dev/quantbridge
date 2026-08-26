// [ADR-040] 전략 브리핑 — 결정론 층 계약.
//
// 이 파일이 잠그는 것은 둘이다.
//  ⑴ **판정어는 결정론 층이 독점한다** — 여기 그려지는 값에 LLM 산출물이 섞이면 안 된다.
//  ⑵ **없는 데이터는 그리지 않는다**(`_KIT.md` §4.9) — 특히 `signals` 는 Track S 에서
//     비는 것이 정상이고, 그때 「신호 없음」이라고 쓰면 거짓이다.

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { StrategyBriefPanel } from "@/features/strategy/components/brief/strategy-brief";
import type { StrategyBrief } from "@/features/strategy/schemas";

const mockUseStrategyBrief = vi.fn();
vi.mock("@/features/strategy/hooks", () => ({
  useStrategyBrief: (...args: unknown[]) => mockUseStrategyBrief(...args),
}));

function makeBrief(overrides: Partial<StrategyBrief> = {}): StrategyBrief {
  return {
    strategy_id: "s-1",
    source_hash: "a".repeat(64),
    track: "S",
    parse: {
      status: "ok",
      pine_version: "v5",
      warnings: [],
      errors: [],
      entry_count: 1,
      exit_count: 1,
      functions_used: ["ta.rsi", "ta.crossover"],
      unsupported_builtins: [],
      unsupported_calls: [],
      is_runnable: true,
      dogfood_only_warning: null,
      declaration: {
        kind: "strategy",
        title: "RSI",
        default_qty_type: null,
        default_qty_value: null,
        pyramiding: null,
      },
      inputs: [{ input_type: "int", var_name: "length", defval: "14", title: "RSI Length" }],
    },
    orders: [
      { name: "strategy.entry", line: 6, args: [{ name: null, value: "strategy.long" }] },
      { name: "strategy.close", line: 8, args: [] },
    ],
    signals: [],
    ...overrides,
  };
}

function ready(brief: StrategyBrief) {
  mockUseStrategyBrief.mockReturnValue({ isPending: false, isError: false, data: brief });
}

describe("StrategyBriefPanel — 결정론 층", () => {
  afterEach(() => {
    cleanup();
    mockUseStrategyBrief.mockReset();
  });

  it("실행 가능 판정 · 파라미터 · 지표 · 주문 줄번호를 그린다", () => {
    ready(makeBrief());
    render(<StrategyBriefPanel strategyId="s-1" />);

    expect(screen.getByTestId("brief-verdict").textContent).toBe("실행 가능");
    expect(screen.getByTestId("brief-params").textContent).toContain("length");
    expect(screen.getByTestId("brief-indicators").textContent).toContain("ta.rsi");

    const orders = screen.getByTestId("brief-orders").textContent ?? "";
    expect(orders).toContain("진입");
    expect(orders).toContain("L6"); // 소스 어디서 나오는지
    expect(orders).toContain("strategy.long"); // 어느 방향인지
  });

  it("★signals 가 비면 그 절을 아예 그리지 않는다", () => {
    // Track S 의 `if cond` 형태는 BE SignalExtractor 가 못 잡는다 — 비는 것이 정상이고
    // 「신호 없음」이라고 쓰면 거짓이다.
    ready(makeBrief({ signals: [] }));
    render(<StrategyBriefPanel strategyId="s-1" />);
    expect(screen.queryByTestId("brief-signals")).toBeNull();
    expect(screen.queryByText(/신호 변수/)).toBeNull();
  });

  it("signals 가 있으면 그린다 (양성 대조)", () => {
    ready(makeBrief({ track: "A", signals: ["buySignal"] }));
    render(<StrategyBriefPanel strategyId="s-1" />);
    expect(screen.getByTestId("brief-signals").textContent).toContain("buySignal");
  });

  it("미지원이 있으면 무엇이 막았는지 줄번호와 함께 보여준다", () => {
    ready(
      makeBrief({
        parse: {
          ...makeBrief().parse,
          is_runnable: false,
          unsupported_builtins: ["ta.supertrend"],
          unsupported_calls: [
            {
              name: "ta.supertrend",
              line: 3,
              col: 9,
              workaround: "ta.atr 로 직접 구현",
              category: "data",
            },
          ],
        },
      }),
    );
    render(<StrategyBriefPanel strategyId="s-1" />);

    expect(screen.getByTestId("brief-verdict").textContent).toBe("실행 불가");
    const blocked = screen.getByTestId("brief-blocked").textContent ?? "";
    expect(blocked).toContain("ta.supertrend");
    expect(blocked).toContain("L3");
    expect(blocked).toContain("ta.atr 로 직접 구현");
  });

  it("Trust Layer degraded 경고를 판정 줄에 노출한다", () => {
    ready(
      makeBrief({
        parse: {
          ...makeBrief().parse,
          dogfood_only_warning: "heikinashi 는 TV 와 달라질 수 있습니다",
        },
      }),
    );
    render(<StrategyBriefPanel strategyId="s-1" />);
    expect(screen.getByText(/heikinashi/)).toBeTruthy();
  });

  it("사이징이 전부 미지정이면 그 절을 그리지 않는다", () => {
    ready(makeBrief());
    render(<StrategyBriefPanel strategyId="s-1" />);
    expect(screen.queryByTestId("brief-sizing")).toBeNull();
  });

  it("로딩은 스켈레톤 하나 · 실패해도 화면이 산다", () => {
    mockUseStrategyBrief.mockReturnValue({ isPending: true, isError: false, data: undefined });
    const { unmount } = render(<StrategyBriefPanel strategyId="s-1" />);
    expect(screen.getByTestId("brief-skeleton")).toBeTruthy();
    unmount();

    mockUseStrategyBrief.mockReturnValue({ isPending: false, isError: true, data: undefined });
    render(<StrategyBriefPanel strategyId="s-1" />);
    expect(screen.getByTestId("brief-error")).toBeTruthy();
  });
});
