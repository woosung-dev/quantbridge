// AuthForm — USER_ALREADY_EXISTS 에러 카피가 「로그인해 주세요」라고 지시만 하지 않고
// /sign-in 인라인 링크를 실제로 주는지 검증한다.
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), refresh: vi.fn(), push: vi.fn() }),
}));

vi.mock("@/lib/auth-client", () => ({
  signIn: { email: vi.fn() },
  signUp: { email: vi.fn() },
  clearAuthTokenCache: vi.fn(),
}));

import { signUp } from "@/lib/auth-client";
import { AuthForm } from "../auth-form";

describe("AuthForm", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("sign-up USER_ALREADY_EXISTS — 에러 문구에 /sign-in 인라인 로그인 링크가 렌더된다", async () => {
    vi.mocked(signUp.email).mockResolvedValue({
      error: { code: "USER_ALREADY_EXISTS", status: 422 },
    } as never);

    render(<AuthForm mode="sign-up" redirectTo="/strategies" />);

    fireEvent.change(screen.getByLabelText("이름"), { target: { value: "홍길동" } });
    fireEvent.change(screen.getByLabelText("이메일 주소"), {
      target: { value: "dup@example.com" },
    });
    fireEvent.change(screen.getByLabelText("비밀번호"), {
      target: { value: "password123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "계정 만들기" }));

    await waitFor(() => {
      expect(screen.getByText(/이미 가입된 이메일입니다/)).toBeInTheDocument();
    });
    // 지시(「로그인해 주세요」)가 아니라 길 — 링크가 있어야 한다.
    const errorBox = document.getElementById("auth-form-error");
    expect(errorBox).not.toBeNull();
    const link = screen.getByRole("link", { name: "로그인" });
    expect(link).toHaveAttribute("href", "/sign-in");
    expect(errorBox!.contains(link)).toBe(true);
  });
});
