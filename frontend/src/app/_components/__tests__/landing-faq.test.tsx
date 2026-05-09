// LandingFaq — 6 question 노출 + details/summary 토글 검증
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { LandingFaq } from "../landing-faq";

describe("LandingFaq", () => {
  afterEach(() => {
    cleanup();
  });

  it("section heading + id=faq 부착", () => {
    const { container } = render(<LandingFaq />);
    expect(
      screen.getByRole("heading", { level: 2, name: "자주 묻는 질문" }),
    ).toBeInTheDocument();
    expect(container.querySelector("#faq")).not.toBeNull();
  });

  it("6개 question 모두 노출 (summary span)", () => {
    const { container } = render(<LandingFaq />);
    const summaries = container.querySelectorAll("details > summary > span");
    expect(summaries.length).toBe(6);
    const texts = Array.from(summaries).map((el) => el.textContent ?? "");
    expect(texts).toEqual([
      "QuantBridge는 어떤 거래소를 지원하나요?",
      "Pine Script 외에 다른 언어도 지원하나요?",
      "백테스트 데이터는 얼마나 제공되나요?",
      "라이브 트레이딩의 최소 자본금은?",
      "API Key 보안은 어떻게 보장되나요?",
      "환불 정책은 어떻게 되나요?",
    ]);
  });

  it("summary 클릭 시 details open 토글", () => {
    const { container } = render(<LandingFaq />);
    const firstSummary = container.querySelector("details > summary");
    const detailsEl = firstSummary?.closest("details");
    expect(detailsEl).not.toBeNull();
    expect(detailsEl?.open).toBe(false);
    fireEvent.click(firstSummary as Element);
    expect(detailsEl?.open).toBe(true);
  });
});
