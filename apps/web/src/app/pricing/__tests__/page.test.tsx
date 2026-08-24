// PricingPage (C 이식) — 시맨틱 구조 assert: 히어로/3구성/11행 대조표/SSOT 거래소 지원표/FAQ/웨이트리스트.
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";

import { ROADMAP_DISCLAIMER } from "@/lib/marketing-canon";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

import PricingPage from "../page";

describe("PricingPage", () => {
  afterEach(() => {
    cleanup();
  });

  it("히어로 h1 요금제 + 공개 판매 전/사용자 1명 칩", () => {
    render(<PricingPage />);
    expect(screen.getByRole("heading", { level: 1, name: "요금제" })).toBeInTheDocument();
    expect(screen.getByText("공개 판매 전")).toBeInTheDocument();
    expect(screen.getByText("사용자 1명 (woosung)")).toBeInTheDocument();
  });

  it("계획 3구성(.plan) + 로컬만 지금 도는 구성 칩", () => {
    const { container } = render(<PricingPage />);
    expect(container.querySelectorAll(".plan").length).toBe(3);
    expect(screen.getByText("지금 도는 구성")).toBeInTheDocument();
    expect(screen.getAllByText("아직 열 수 없습니다").length).toBe(2);
  });

  it("대조표 11행 + Bybit 데모 단일 지원과 SSOT 미지원 렌더", () => {
    const { container } = render(<PricingPage />);
    const rows = container.querySelectorAll("table.cmp tbody tr");
    expect(rows.length).toBe(11);
    expect(screen.getByText("지원하는 거래소는 Bybit 데모 하나입니다.")).toBeInTheDocument();

    const exchangeTable = screen.getByRole("table", { name: "거래소별 연동 상태" });
    expect(within(exchangeTable).getAllByText("지원하지 않음")).toHaveLength(3);
    expect(screen.getByText(ROADMAP_DISCLAIMER)).toBeInTheDocument();
  });

  it("FAQ 4문항 + 웨이트리스트 폼", () => {
    const { container } = render(<PricingPage />);
    expect(container.querySelectorAll(".faq-list .faq-q").length).toBe(4);
    expect(container.querySelector("#waitlist")).not.toBeNull();
    expect(screen.getByLabelText("이메일 주소")).toBeInTheDocument();
  });

  it("가격 미정 — 세 구성 모두 무데이터 셀 + 금액 미인쇄", () => {
    const { container } = render(<PricingPage />);
    const amts = container.querySelectorAll(".plan-price .amt");
    expect(amts.length).toBe(3);
    amts.forEach((el) => expect(el.textContent).toBe("—"));
  });

  it("가격 미정 — 진행 막대 없음 (BL-810)", () => {
    const { container } = render(<PricingPage />);
    expect(container.querySelectorAll(".plan .meter").length).toBe(0);
    // 분모·분자 설명 문장은 남는다 — 정보 축은 그쪽이 담당한다.
    expect(container.querySelectorAll(".plan-meter-foot").length).toBe(3);
  });
});
