// [ADR-040] 해설 층 — **판정이 아니다**를 화면이 지키는지.
//
// 이 파일이 잠그는 것 넷.
//  ⑴ 열기 전에는 **서버를 부르지 않는다**(LLM 왕복은 느리고 돈이 든다).
//  ⑵ 「판정이 아닙니다」 라벨이 본문과 함께 뜬다.
//  ⑶ 근거 줄 없는 문장은 **그리지 않는다**.
//  ⑷ 실패해도 **브리핑을 대체하지 않는다**.

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { NarrativePanel } from "@/features/strategy/components/brief/narrative-panel";

const mockUseStrategyNarrative = vi.hoisted(() => vi.fn());
vi.mock("@/features/strategy/hooks", () => ({
  useStrategyNarrative: (...args: unknown[]) => mockUseStrategyNarrative(...args),
}));

const NARRATIVE = {
  source_hash: "a".repeat(64),
  provider: "anthropic" as const,
  summary: "RSI 과매도 반전을 노리는 평균회귀 전략입니다.",
  style: "mean_reversion" as const,
  assumptions: [
    { text: "청산이 RSI 단일 조건에 의존합니다.", pine_lines: [27] },
    { text: "근거 없는 문장", pine_lines: [] },
  ],
  risks: [{ text: "추세장에서 드로다운이 커집니다.", pine_lines: [12, 27] }],
  dropped_ungrounded: 1,
};

function ready(data: unknown) {
  mockUseStrategyNarrative.mockReturnValue({ isPending: false, isError: false, data });
}

describe("NarrativePanel — 판정이 아닌 층", () => {
  afterEach(() => {
    cleanup();
    mockUseStrategyNarrative.mockReset();
  });

  it("★열기 전에는 쿼리를 켜지 않는다 (enabled=false)", () => {
    mockUseStrategyNarrative.mockReturnValue({ isPending: false, isError: false, data: undefined });
    render(<NarrativePanel strategyId="s-1" />);

    expect(screen.getByTestId("narrative-idle")).toBeTruthy();
    // 훅은 불리지만 `enabled` 가 false 여야 한다 — 그것이 「서버를 안 부른다」의 실체다.
    expect(mockUseStrategyNarrative).toHaveBeenCalledWith("s-1", false);
  });

  it("열면 켜진다 (양성 대조)", () => {
    ready(NARRATIVE);
    render(<NarrativePanel strategyId="s-1" />);
    fireEvent.click(screen.getByRole("button", { name: "AI 해설 보기" }));

    expect(mockUseStrategyNarrative).toHaveBeenLastCalledWith("s-1", true);
  });

  it("★「판정이 아닙니다」가 본문과 함께 뜬다", () => {
    ready(NARRATIVE);
    render(<NarrativePanel strategyId="s-1" />);
    fireEvent.click(screen.getByRole("button", { name: "AI 해설 보기" }));

    expect(screen.getByTestId("narrative-label").textContent).toContain("판정이 아닙니다");
    expect(screen.getByTestId("narrative-summary").textContent).toContain("평균회귀");
  });

  it("★근거 줄이 없는 문장은 그리지 않는다", () => {
    ready(NARRATIVE);
    render(<NarrativePanel strategyId="s-1" />);
    fireEvent.click(screen.getByRole("button", { name: "AI 해설 보기" }));

    const assumptions = screen.getByTestId("narrative-assumptions").textContent ?? "";
    expect(assumptions).toContain("RSI 단일 조건");
    expect(assumptions).toContain("L27"); // 근거를 화면에 보인다 — 사용자가 대조할 수 있어야 한다
    expect(assumptions).not.toContain("근거 없는 문장");

    // 서버가 버린 개수도 숨기지 않는다.
    expect(screen.getByTestId("narrative-dropped").textContent).toContain("1개");
  });

  it("근거 있는 문장이 하나도 없으면 그 절 자체를 그리지 않는다", () => {
    ready({ ...NARRATIVE, risks: [{ text: "근거 없음", pine_lines: [] }], dropped_ungrounded: 0 });
    render(<NarrativePanel strategyId="s-1" />);
    fireEvent.click(screen.getByRole("button", { name: "AI 해설 보기" }));

    expect(screen.queryByTestId("narrative-risks")).toBeNull();
    expect(screen.queryByText("언제 깨지나")).toBeNull();
  });

  it("★실패는 브리핑을 대체하지 않는다 — 「해설만 실패」라고 말한다", () => {
    mockUseStrategyNarrative.mockReturnValue({ isPending: false, isError: true, data: undefined });
    render(<NarrativePanel strategyId="s-1" />);
    fireEvent.click(screen.getByRole("button", { name: "AI 해설 보기" }));

    const box = screen.getByTestId("narrative-error");
    expect(box.textContent).toContain("그대로 유효합니다");
  });
});
