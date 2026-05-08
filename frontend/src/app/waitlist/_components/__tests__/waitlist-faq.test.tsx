// WaitlistFaq — 5개 FAQ 항목 + native details/summary 토글 검증
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { WaitlistFaq } from "../waitlist-faq";

describe("WaitlistFaq", () => {
  afterEach(() => {
    cleanup();
  });

  it("h2 '자주 묻는 질문' + 5개 질문 노출", () => {
    render(<WaitlistFaq />);
    expect(
      screen.getByRole("heading", { level: 2, name: /자주 묻는 질문/ }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Beta 는 무료인가요/)).toBeInTheDocument();
    expect(screen.getByText(/TradingView Pro\+ 가 꼭 필요한가요/)).toBeInTheDocument();
    expect(screen.getByText(/어떤 거래소를 지원하나요/)).toBeInTheDocument();
    expect(screen.getByText(/초대장은 언제 받을 수 있나요/)).toBeInTheDocument();
    expect(screen.getByText(/Demo 환경에서 진짜 돈을 잃지 않나요/)).toBeInTheDocument();
  });

  it("FAQ 5건 모두 native <details> 요소로 렌더 (접근성 + JS 의존도 0)", () => {
    const { container } = render(<WaitlistFaq />);
    const detailsList = container.querySelectorAll("details");
    expect(detailsList.length).toBe(5);
  });
});
