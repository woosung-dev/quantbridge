// TickRuler 계약 — 순수 장식 접근성·선택자·방향·클래스 병합.

import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TickRuler } from "../tick-ruler";

describe("TickRuler", () => {
  it("두 orientation 모두 aria-hidden=true 로 렌더한다", () => {
    const { container } = render(
      <>
        <TickRuler orientation="horizontal" />
        <TickRuler orientation="vertical" />
      </>,
    );

    expect(container.querySelectorAll('[aria-hidden="true"]')).toHaveLength(2);
  });

  it('선택자 계약인 data-slot="tick-ruler" 를 제공한다', () => {
    render(<TickRuler />);

    expect(document.querySelector('[data-slot="tick-ruler"]')).toBeInTheDocument();
  });

  it("기본값과 horizontal 은 qb-ruler-x w-full, vertical 은 qb-ruler-y h-full 이다", () => {
    const { container } = render(
      <>
        <TickRuler />
        <TickRuler orientation="horizontal" />
        <TickRuler orientation="vertical" />
      </>,
    );
    const rulers = container.querySelectorAll('[data-slot="tick-ruler"]');

    expect(rulers[0]).toHaveClass("qb-ruler-x", "w-full");
    expect(rulers[1]).toHaveClass("qb-ruler-x", "w-full");
    expect(rulers[0]?.className).toBe(rulers[1]?.className);
    expect(rulers[2]).toHaveClass("qb-ruler-y", "h-full");
  });

  it("className 은 방향 클래스와 함께 병합한다", () => {
    const { container } = render(<TickRuler className="mt-4" />);
    const ruler = container.firstElementChild;

    expect(ruler).toHaveClass("qb-ruler-x", "mt-4");
  });

  it("접근 가능한 role과 텍스트가 없는 순수 장식이다", () => {
    const { container } = render(<TickRuler />);

    expect(container.firstElementChild).not.toHaveAttribute("role");
    expect(container.firstElementChild).toHaveTextContent("");
  });

  it("컴포넌트는 함수이며 렌더 결과 요소는 정확히 하나다", () => {
    const { container } = render(<TickRuler />);

    expect(TickRuler).toBeTypeOf("function");
    expect(container.children).toHaveLength(1);
  });
});
