// 로그인/가입 화면이 **우리 DOM** 으로 C 디자인 캐논을 지키는지 검증한다(ADR-034).
// ★종전 이 파일은 Clerk 위젯에 넘기는 `appearance` prop 을 단언했다 — 즉 **우리가 만든 문자열을
//   우리가 다시 읽는** 시험이었고, 위젯 내부가 그 클래스를 실제로 쓰는지는 보지 못했다.
//   폼이 우리 것이 된 지금은 렌더 결과를 직접 볼 수 있으므로 그쪽을 단언한다.
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), refresh: vi.fn(), push: vi.fn() }),
}));

vi.mock("@/lib/auth-client", () => ({
  signIn: { email: vi.fn() },
  signUp: { email: vi.fn() },
  clearAuthTokenCache: vi.fn(),
}));

import SignInPage from "../sign-in/[[...sign-in]]/page";
import SignUpPage from "../sign-up/[[...sign-up]]/page";

describe("(auth) 로그인/가입 화면", () => {
  afterEach(cleanup);

  it("로그인 — 이메일·비밀번호 필드와 제출 버튼이 캐논 클래스로 렌더된다", async () => {
    render(await SignInPage({ searchParams: Promise.resolve({}) }));

    expect(screen.getByLabelText("이메일 주소")).toHaveClass("input");
    expect(screen.getByLabelText("비밀번호")).toHaveAttribute("type", "password");
    const submit = screen.getByRole("button", { name: "로그인" });
    expect(submit).toHaveClass("btn", "btn-primary");
    // 로그인 화면에는 이름 필드가 없다.
    expect(screen.queryByLabelText("이름")).toBeNull();
  });

  it("가입 — 이름 필드가 추가되고 비밀번호 autoComplete 가 new-password 다", () => {
    render(<SignUpPage />);

    expect(screen.getByLabelText("이름")).toBeInTheDocument();
    expect(screen.getByLabelText("비밀번호")).toHaveAttribute("autocomplete", "new-password");
    expect(screen.getByRole("button", { name: "계정 만들기" })).toBeInTheDocument();
  });

  it("로그인 — redirect_url 은 앱 내부 경로만 통과한다(열린 리다이렉트 차단)", async () => {
    // 외부 절대 URL 과 프로토콜 상대 URL 둘 다 기본값으로 떨어져야 한다.
    for (const evil of ["https://evil.example/x", "//evil.example/x"]) {
      const el = await SignInPage({ searchParams: Promise.resolve({ redirect_url: evil }) });
      const props = (el as unknown as { props: { children: { props: { redirectTo: string } } } })
        .props.children.props;
      expect(props.redirectTo).toBe("/strategies");
    }
    const ok = await SignInPage({ searchParams: Promise.resolve({ redirect_url: "/trading" }) });
    const okProps = (ok as unknown as { props: { children: { props: { redirectTo: string } } } })
      .props.children.props;
    expect(okProps.redirectTo).toBe("/trading");
  });
});
