// WaitlistProduct (C 이식) — 제품 4장(.cta) + Pine 전체 거부 정책 문구.
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { WaitlistProduct } from "../waitlist-product";

describe("WaitlistProduct", () => {
  afterEach(() => {
    cleanup();
  });

  it("section id=build + 4 카드(.cta)", () => {
    const { container } = render(<WaitlistProduct />);
    expect(container.querySelector("#build")).not.toBeNull();
    expect(container.querySelectorAll(".card.cta").length).toBe(4);
    expect(screen.getByText("Pine Script 파싱")).toBeInTheDocument();
    expect(screen.getByText("거래소 연결")).toBeInTheDocument();
  });

  it("부분 실행 거부 정책 문구 (ADR-003)", () => {
    render(<WaitlistProduct />);
    expect(screen.getByText(/하나라도 있으면 전체를 미지원으로 판정/)).toBeInTheDocument();
  });
});
