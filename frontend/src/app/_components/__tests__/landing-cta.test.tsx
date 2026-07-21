// LandingCta (C 이식) — 이메일 폼 3상태: 기본 / 검증 에러(role=alert) / 유효 시 웨이트리스트 이동.
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

import { LandingCta } from "../landing-cta";

describe("LandingCta", () => {
  afterEach(() => {
    cleanup();
    push.mockClear();
  });

  it("기본 상태 — 이메일 입력 + 알림 신청 버튼, 에러 미노출", () => {
    render(<LandingCta />);
    expect(screen.getByLabelText("알림 받을 이메일")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "알림 신청" })).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("잘못된 이메일 제출 — role=alert 에러 노출 + 이동 안 함", () => {
    render(<LandingCta />);
    fireEvent.change(screen.getByLabelText("알림 받을 이메일"), {
      target: { value: "woosung@" },
    });
    fireEvent.click(screen.getByRole("button", { name: "알림 신청" }));
    expect(screen.getByRole("alert").textContent).toContain("이메일 형식이 올바르지 않습니다");
    expect(push).not.toHaveBeenCalled();
  });

  it("유효한 이메일 제출 — 웨이트리스트로 이동", () => {
    render(<LandingCta />);
    fireEvent.change(screen.getByLabelText("알림 받을 이메일"), {
      target: { value: "woosung@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: "알림 신청" }));
    expect(push).toHaveBeenCalledWith("/waitlist?email=woosung%40example.com");
  });
});
