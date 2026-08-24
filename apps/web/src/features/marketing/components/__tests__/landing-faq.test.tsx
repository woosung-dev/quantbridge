// LandingFaq (C 이식) — 5 질문 details/summary + id=faq + 첫 항목 기본 open.
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { EXCHANGE_SUPPORT, ROADMAP_DISCLAIMER } from "@/lib/marketing-canon";

import { LandingFaq } from "../landing-faq";

describe("LandingFaq", () => {
  afterEach(() => {
    cleanup();
  });

  it("section heading + id=faq", () => {
    const { container } = render(<LandingFaq />);
    expect(
      screen.getByRole("heading", { level: 2, name: "먼저 물어볼 만한 것들" }),
    ).toBeInTheDocument();
    expect(container.querySelector("#faq")).not.toBeNull();
  });

  it("5개 질문 렌더 (lp-faq-item)", () => {
    const { container } = render(<LandingFaq />);
    const items = container.querySelectorAll("details.lp-faq-item");
    expect(items.length).toBe(5);
    expect(screen.getByText("어떤 거래소를 지원하나요?")).toBeInTheDocument();
    expect(screen.getByText("지금 쓸 수 있나요?")).toBeInTheDocument();
  });

  it("현재 제공 범위와 미지원 고지를 SSOT로 렌더", () => {
    const [supportedExchange] = EXCHANGE_SUPPORT.filter(({ status }) => status === "supported");
    render(<LandingFaq />);

    expect(
      screen.getByText(
        `지금 연결되는 거래소는 ${supportedExchange?.exchange} 하나뿐이며 ${supportedExchange?.environment} 환경만 제공합니다.`,
      ),
    ).toBeInTheDocument();
    expect(screen.getByText(ROADMAP_DISCLAIMER)).toBeInTheDocument();
  });

  it("첫 항목 기본 open · 다른 summary 클릭 시 open 토글", () => {
    const { container } = render(<LandingFaq />);
    const details = container.querySelectorAll("details.lp-faq-item");
    expect((details[0] as HTMLDetailsElement).open).toBe(true);
    const second = details[1] as HTMLDetailsElement;
    expect(second.open).toBe(false);
    fireEvent.click(second.querySelector("summary") as Element);
    expect(second.open).toBe(true);
  });
});
