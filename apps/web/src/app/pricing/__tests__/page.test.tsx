// PricingPage (C 이식) — 시맨틱 구조 assert: 히어로/3구성/11행 대조표/FAQ/웨이트리스트 + OKX 로드맵.
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

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

  it("대조표 11행 + Bybit 단일 연결 문구(OKX 로드맵)", () => {
    const { container } = render(<PricingPage />);
    const rows = container.querySelectorAll("table.cmp tbody tr");
    expect(rows.length).toBe(11);
    expect(
      screen.getByText(/연결해 본 거래소는 Bybit \(데모 · 메인넷\) 하나입니다/),
    ).toBeInTheDocument();
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
});
