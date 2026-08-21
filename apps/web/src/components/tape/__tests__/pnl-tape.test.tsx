// PnlTape 계약 — 구간 델타 수·끝 절단·절대값 정규화·접근성·크기 변형.

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PnlTape } from "../pnl-tape";

describe("PnlTape", () => {
  it("deltas 길이만큼 바 span 을 렌더한다", () => {
    const { container } = render(<PnlTape deltas={[1, 2, 3]} />);

    expect(container.querySelectorAll("span")).toHaveLength(3);
  });

  it("maxBars 는 앞이 아니라 끝의 델타만 남긴다", () => {
    const { container } = render(
      <PnlTape deltas={[-9, -9, -9, -9, -9, -9, -9, 1, 2, 3]} maxBars={3} />,
    );
    const bars = container.querySelectorAll("span");

    expect(bars).toHaveLength(3);
    expect([...bars].map((bar) => bar.style.backgroundColor)).toEqual([
      "var(--bullish)",
      "var(--bullish)",
      "var(--bullish)",
    ]);
  });

  it("양수 델타는 최대 절대값을 100% 높이로 정규화한다", () => {
    const { container } = render(<PnlTape deltas={[1, 2, 4]} />);
    const bars = container.querySelectorAll("span");

    expect(bars[2]?.style.height).toBe("100%");
  });

  it("음수 절대값이 가장 크면 그 바를 100% 높이로 정규화한다", () => {
    const { container } = render(<PnlTape deltas={[-4, 1]} />);
    const bars = container.querySelectorAll("span");

    expect(bars[0]?.style.height).toBe("100%");
    expect(bars[1]?.style.height).toBe("25%");
  });

  it("0 델타도 최소 6% 높이로 표시한다", () => {
    const { container } = render(<PnlTape deltas={[100, 0]} />);
    const bars = container.querySelectorAll("span");

    expect(bars[1]?.style.height).toBe("6%");
  });

  it("양수와 0은 bullish, 음수는 bearish 색을 사용한다", () => {
    const { container } = render(<PnlTape deltas={[1, -1, 0]} />);
    const bars = container.querySelectorAll("span");

    expect(bars[0]?.style.backgroundColor).toBe("var(--bullish)");
    expect(bars[1]?.style.backgroundColor).toBe("var(--bearish)");
    expect(bars[2]?.style.backgroundColor).toBe("var(--bullish)");
  });

  it("빈 델타는 aria-hidden 40개 baseline 틱, 데이터는 이름 있는 img를 렌더한다", () => {
    const { container, rerender } = render(<PnlTape deltas={[]} />);

    expect(container.firstElementChild).toHaveAttribute("aria-hidden", "true");
    expect(container.querySelectorAll("span")).toHaveLength(40);

    rerender(<PnlTape deltas={[1]} />);
    expect(screen.getByRole("img", { name: "구간별 손익 추이 마이크로바" })).toBeInTheDocument();
  });

  it("size=micro 는 h-4, 기본 size 는 h-6 프레임 클래스를 사용한다", () => {
    const { container, rerender } = render(<PnlTape deltas={[1]} />);

    expect(container.firstElementChild).toHaveClass("h-6");

    rerender(<PnlTape deltas={[1]} size="micro" />);
    expect(container.firstElementChild).toHaveClass("h-4");
  });
});
