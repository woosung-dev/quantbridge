// PricingWaitlistForm — 3상태: 기본 / 검증 에러(role=alert) / 유효 시 /waitlist 이동.
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

import { PricingWaitlistForm } from "../pricing-waitlist-form";

describe("PricingWaitlistForm", () => {
  afterEach(() => {
    cleanup();
    push.mockClear();
  });

  it("기본 상태 — 이메일 + 등록하기 버튼, 에러 미노출, 순번 미집계 문구", () => {
    render(<PricingWaitlistForm />);
    expect(screen.getByLabelText("이메일 주소")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "등록하기" })).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByText(/등록 인원수나 대기 순번은 집계하지 않습니다/)).toBeInTheDocument();
  });

  it("잘못된 이메일 제출 — role=alert 에러 + input.invalid + 이동 안 함", () => {
    const { container } = render(<PricingWaitlistForm />);
    fireEvent.change(screen.getByLabelText("이메일 주소"), {
      target: { value: "woosung@" },
    });
    fireEvent.click(screen.getByRole("button", { name: "등록하기" }));
    expect(screen.getByRole("alert").textContent).toContain("이메일 주소 형식이 올바르지 않습니다");
    expect(container.querySelector(".input.invalid")).not.toBeNull();
    expect(push).not.toHaveBeenCalled();
  });

  it("유효한 이메일 제출 — /waitlist 로 이동", () => {
    render(<PricingWaitlistForm />);
    fireEvent.change(screen.getByLabelText("이메일 주소"), {
      target: { value: "woosung@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: "등록하기" }));
    expect(push).toHaveBeenCalledWith("/waitlist?email=woosung%40example.com");
  });
});
