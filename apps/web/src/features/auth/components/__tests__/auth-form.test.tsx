// AuthForm — USER_ALREADY_EXISTS 에러 카피가 「로그인해 주세요」라고 지시만 하지 않고
// /sign-in 인라인 링크를 실제로 주는지, 폼 레벨 에러가 블록 알럿(.form-alert)으로 렌더되는지,
// 비밀번호 표시 토글이 input type 을 실제로 바꾸는지 검증한다.
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
    // 폼 레벨 에러는 필드 프리미티브(.field-error)가 아니라 블록 알럿(.form-alert)이어야 하고,
    // 인라인 링크가 그 블록 안에서도 살아 있어야 한다(위 contains 단언이 그것이다).
    expect(errorBox!.classList.contains("form-alert")).toBe(true);
    expect(errorBox!.classList.contains("field-error")).toBe(false);
  });

  it("비밀번호 표시 토글 — 클릭마다 input type 이 password ↔ text 로 바뀌고 aria 가 따라간다", () => {
    render(<AuthForm mode="sign-in" redirectTo="/strategies" />);

    const input = screen.getByLabelText("비밀번호");
    expect(input).toHaveAttribute("type", "password");

    const toggle = screen.getByRole("button", { name: "비밀번호 표시" });
    expect(toggle).toHaveAttribute("aria-pressed", "false");
    expect(toggle).toHaveAttribute("aria-controls", "auth-password");

    fireEvent.click(toggle);
    expect(input).toHaveAttribute("type", "text");
    // 표시 중에는 라벨이 「숨기기」로 뒤집힌다 — 같은 버튼이다.
    expect(screen.getByRole("button", { name: "비밀번호 숨기기" })).toBe(toggle);
    expect(toggle).toHaveAttribute("aria-pressed", "true");

    fireEvent.click(toggle);
    expect(input).toHaveAttribute("type", "password");
    expect(toggle).toHaveAttribute("aria-pressed", "false");
  });
});
