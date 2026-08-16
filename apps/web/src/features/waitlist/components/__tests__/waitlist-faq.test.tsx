// WaitlistFaq (C 이식) — 3문항 + 프로토타입 고지. AI-slop(평생 할인/OKX Demo 지원) 제거 검증.
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { WaitlistFaq } from "../waitlist-faq";

describe("WaitlistFaq", () => {
  afterEach(() => {
    cleanup();
  });

  it("h2 + 3문항(.faq-item)", () => {
    const { container } = render(<WaitlistFaq />);
    expect(
      screen.getByRole("heading", { level: 2, name: /먼저 답해 두는 세 가지/ }),
    ).toBeInTheDocument();
    expect(container.querySelectorAll(".faq-item").length).toBe(3);
    expect(screen.getByText("언제 공개되나요?")).toBeInTheDocument();
  });

  it("Bybit 데모·메인넷 확인 + OKX/Binance/Bitget 로드맵 표기", () => {
    render(<WaitlistFaq />);
    expect(screen.getByText(/OKX, Binance, Bitget 은 로드맵에 있을 뿐/)).toBeInTheDocument();
  });

  it("AI-slop 제거 — 평생 할인/무료 약속 없음", () => {
    render(<WaitlistFaq />);
    expect(screen.queryByText(/평생 할인/)).not.toBeInTheDocument();
    expect(screen.queryByText(/무료입니다/)).not.toBeInTheDocument();
  });
});
