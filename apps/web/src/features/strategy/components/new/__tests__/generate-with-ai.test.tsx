// [ADR-041] 자연어 → 전략 생성 화면.
//
// 잠그는 것 넷.
//  ⑴ 판정 칩이 **서버 값**을 그린다(LLM 이 아니라 `analyze_coverage`).
//  ⑵ 미지원이면 **무엇이 막았는지** 보이고 「이 코드 쓰기」가 막힌다.
//  ⑶ 드리프트가 있으면 「**다를 수 있습니다**」로 경고한다 — 「다릅니다」가 아니다.
//  ⑷ 생성만으로 저장되지 않는다 — 사용자가 눌러야 소스에 들어간다.

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { GenerateWithAI } from "@/features/strategy/components/new/generate-with-ai";

const mockUseGenerateStrategy = vi.hoisted(() => vi.fn());
vi.mock("@/features/strategy/hooks", () => ({
  useGenerateStrategy: () => mockUseGenerateStrategy(),
}));

const RUNNABLE = {
  provider: "anthropic" as const,
  pine_source: '//@version=5\nstrategy("RSI")\nr = ta.rsi(close, 14)\n',
  llm_python: "r = ta.rsi(close, 14)\n",
  notes: ["손절이 없습니다."],
  is_runnable: true,
  unsupported: [],
  drift: { rendered_python: "r = ta.rsi(close, 14)\n", only_in_llm: [], only_in_rendered: [] },
};

function ready(data: unknown, extra: Record<string, unknown> = {}) {
  const mutate = vi.fn();
  mockUseGenerateStrategy.mockReturnValue({
    mutate,
    data,
    isPending: false,
    isError: false,
    ...extra,
  });
  return mutate;
}

function renderIt(onUsePine = vi.fn()) {
  render(<GenerateWithAI symbol="BTC/USDT" timeframe="1h" onUsePine={onUsePine} />);
  return onUsePine;
}

describe("GenerateWithAI", () => {
  afterEach(() => {
    cleanup();
    mockUseGenerateStrategy.mockReset();
  });

  it("★생성만으로는 소스에 들어가지 않는다 — 눌러야 들어간다", () => {
    ready(RUNNABLE);
    const onUsePine = renderIt();

    expect(onUsePine).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "이 Pine 코드 쓰기" }));
    expect(onUsePine).toHaveBeenCalledWith(RUNNABLE.pine_source);
  });

  it("판정 칩은 서버 값을 그린다", () => {
    ready(RUNNABLE);
    renderIt();
    expect(screen.getByTestId("generate-verdict").textContent).toBe("실행 가능");
  });

  it("★미지원이면 무엇이 막았는지 보이고 「이 코드 쓰기」가 막힌다", () => {
    ready({
      ...RUNNABLE,
      is_runnable: false,
      unsupported: ["ta.supertrend"],
      drift: null,
    });
    renderIt();

    expect(screen.getByTestId("generate-verdict").textContent).toBe("실행 불가");
    expect(screen.getByTestId("generate-blocked").textContent).toContain("ta.supertrend");
    const use = screen.getByRole("button", { name: "이 Pine 코드 쓰기" }) as HTMLButtonElement;
    expect(use.disabled).toBe(true);
  });

  it("★드리프트는 「다를 수 있습니다」로 말한다 — 탐지기가 확정할 수 없기 때문이다", () => {
    ready({
      ...RUNNABLE,
      drift: {
        rendered_python: "r = ta.rsi(close, 14)\n",
        only_in_llm: ["ta.macd"],
        only_in_rendered: [],
      },
    });
    renderIt();

    const box = screen.getByTestId("generate-drift");
    expect(box.textContent).toContain("다를 수 있습니다");
    expect(box.textContent).not.toContain("다릅니다.");
  });

  it("드리프트가 없으면 경고를 그리지 않는다 (음성 대조)", () => {
    ready(RUNNABLE);
    renderIt();
    expect(screen.queryByTestId("generate-drift")).toBeNull();
  });

  it("프롬프트가 짧으면 생성 버튼이 막힌다", () => {
    ready(null);
    renderIt();
    const btn = screen.getByRole("button", { name: "AI 로 만들기" }) as HTMLButtonElement;
    expect(btn.disabled).toBe(true);

    fireEvent.change(screen.getByLabelText("어떤 전략을 원하시나요?"), {
      target: { value: "RSI 과매도에서 롱 잡는 전략" },
    });
    expect(
      (screen.getByRole("button", { name: "AI 로 만들기" }) as HTMLButtonElement).disabled,
    ).toBe(false);
  });
});
