// AccountButton — 로그아웃/계정 삭제의 **부르는 쪽**이 실재하는지 잰다(ADR-034).
//
// ★★왜 이 파일이 있나 — 2026-08-17 codex 적대 리뷰가 P1 을 잡았다: `DELETE /api/v1/auth/me`
//   엔드포인트와 그 회귀 테스트는 있는데 **부르는 코드가 0건**이었다. 같은 회차가 [LESSON-114]
//   (「가드를 셀 때 소비자가 아니라 생산자를 세라」)를 쓰고도 자기 코드에서 그것을 반복했다.
//   이 테스트가 그 생산자를 고정한다.

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

const replace = vi.fn();
const refresh = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, refresh, push: vi.fn() }),
}));

import {
  clearAuthTokenCache,
  deleteAccount,
  resetAuthMock,
  signOut,
} from "@/lib/__mocks__/auth-client";

import { AccountButton } from "../account-button";

afterEach(() => {
  cleanup();
  resetAuthMock();
  replace.mockClear();
  refresh.mockClear();
});

describe("AccountButton", () => {
  it("로그아웃 — 토큰 캐시를 먼저 비우고 sign-in 으로 보낸다", async () => {
    render(<AccountButton />);

    fireEvent.click(screen.getByRole("button", { name: /로그아웃/ }));

    await waitFor(() => expect(signOut).toHaveBeenCalledTimes(1));
    expect(clearAuthTokenCache).toHaveBeenCalled();
    expect(replace).toHaveBeenCalledWith("/sign-in");
  });

  it("트리거 라벨이 거래소 계정 삭제와 겹치지 않는다 (e2e strict-mode 충돌 방지)", () => {
    // ★`exchange-accounts-panel` 의 행 삭제 버튼이 `aria-label="계정 삭제"` 다.
    //   같은 이름을 쓰면 `getByRole` 이 둘을 잡아 기존 e2e(#7)가 죽는다 — 실제로 밟았다.
    render(<AccountButton />);
    // ★Playwright 의 `getByRole(name)` 은 **부분 문자열** 매칭이라 「내 계정 삭제」로 바꿔도
    //   여전히 겹친다. 부분 문자열 자체가 없어야 한다.
    expect(screen.getByRole("button", { name: "내 계정 지우기" })).toBeInTheDocument();
    expect(screen.queryAllByRole("button").map((b) => b.getAttribute("aria-label"))).not.toContain(
      "계정 삭제",
    );
    for (const b of screen.queryAllByRole("button")) {
      expect(b.getAttribute("aria-label") ?? "").not.toContain("계정 삭제");
    }
  });

  it("아이콘 레일(769~1024px) — 액션 버튼 2개는 숨김 변형을 갖고 아바타만 남는다", () => {
    // KITPORT 레일 CSS 는 .account-name 등 텍스트만 숨긴다 — 액션 버튼까지 두면
    // 콘텐츠 폭 ~124px 가 64px 레일을 넘친다. 「레일에서는 아바타만 남는다」(사이드바 주석) 이행.
    render(<AccountButton />);
    const logout = screen.getByRole("button", { name: /로그아웃/ });
    const del = screen.getByRole("button", { name: "내 계정 지우기" });
    // ★스택 변형 max-[1024px]: 은 `width < 1024` 라 KITPORT(max-width:1024, 경계 포함)와
    //   정확히 1024px 에서 어긋난다 — raw 미디어 변형이어야 한다(실측 근거는 컴포넌트 주석).
    for (const b of [logout, del]) {
      expect(b.className).toContain("[@media(min-width:769px)_and_(max-width:1024px)]:hidden");
    }
    expect(screen.getByTestId("account-avatar").className).not.toContain("hidden");
  });

  it("위계 — 삭제 트리거는 muted 텍스트 버튼이고 hover 에서만 destructive 톤이다", () => {
    render(<AccountButton />);
    const del = screen.getByRole("button", { name: "내 계정 지우기" });
    // 아이콘 동급 버튼 강등 — 기본 ink-3 무채색, hover 에서만 destructive.
    expect(del).toHaveTextContent("계정 지우기");
    expect(del.className).toContain("text-[color:var(--ink-3)]");
    expect(del.className).toContain("hover:text-[color:var(--destructive)]");
  });

  it("hover 피드백 — 로그아웃 버튼이 셸 관용구(hover 배경 var(--card-2))를 갖는다", () => {
    // 같은 셸의 .nav-item/.hamburger 는 hover 배경이 있는데 계정 액션만 무반응이었다.
    render(<AccountButton />);
    const logout = screen.getByRole("button", { name: /로그아웃/ });
    expect(logout.className).toContain("hover:bg-[color:var(--card-2)]");
  });

  it("계정 삭제 — 확인 없이는 아무것도 부르지 않는다 (음성 대조)", async () => {
    render(<AccountButton />);

    fireEvent.click(screen.getByRole("button", { name: "내 계정 지우기" }));

    // 다이얼로그만 열린다. 되돌릴 수 없는 동작이므로 이 단계에서 호출이 나가면 안 된다.
    expect(await screen.findByText("계정을 삭제할까요?")).toBeInTheDocument();
    expect(deleteAccount).not.toHaveBeenCalled();
  });

  it("계정 삭제 — 확인하면 deleteAccount 를 부르고 sign-in 으로 보낸다", async () => {
    render(<AccountButton />);

    fireEvent.click(screen.getByRole("button", { name: "내 계정 지우기" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(await screen.findByRole("button", { name: "영구 삭제" }));
    void dialog;

    await waitFor(() => expect(deleteAccount).toHaveBeenCalledTimes(1));
    expect(replace).toHaveBeenCalledWith("/sign-in");
  });

  it("계정 삭제 실패 — 사용자에게 말하고 **이동하지 않는다**", async () => {
    // 서버가 「돈을 멈추지 못했다」고 답하면 계정은 그대로 남는다(fail-closed).
    // 조용히 닫으면 사용자는 지워진 줄 안다 — 그 침묵을 이 단언이 막는다.
    deleteAccount.mockResolvedValueOnce({
      error: { message: "계정 정리에 실패했습니다 (status 500)." },
    });
    render(<AccountButton />);

    fireEvent.click(screen.getByRole("button", { name: "내 계정 지우기" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(await screen.findByRole("button", { name: "영구 삭제" }));
    void dialog;

    expect(await screen.findByRole("alert")).toHaveTextContent("계정 정리에 실패했습니다");
    expect(replace).not.toHaveBeenCalled();
  });
});
