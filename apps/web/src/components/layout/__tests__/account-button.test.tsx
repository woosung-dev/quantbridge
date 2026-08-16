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

  it("계정 삭제 — 확인 없이는 아무것도 부르지 않는다 (음성 대조)", async () => {
    render(<AccountButton />);

    fireEvent.click(screen.getByRole("button", { name: "계정 삭제" }));

    // 다이얼로그만 열린다. 되돌릴 수 없는 동작이므로 이 단계에서 호출이 나가면 안 된다.
    expect(await screen.findByText("계정을 삭제할까요?")).toBeInTheDocument();
    expect(deleteAccount).not.toHaveBeenCalled();
  });

  it("계정 삭제 — 확인하면 deleteAccount 를 부르고 sign-in 으로 보낸다", async () => {
    render(<AccountButton />);

    fireEvent.click(screen.getByRole("button", { name: "계정 삭제" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(
      screen.getAllByRole("button", { name: "계정 삭제" }).find((b) => dialog.contains(b))!,
    );

    await waitFor(() => expect(deleteAccount).toHaveBeenCalledTimes(1));
    expect(replace).toHaveBeenCalledWith("/sign-in");
  });

  it("계정 삭제 실패 — 사용자에게 말하고 **이동하지 않는다**", async () => {
    // 서버가 「돈을 멈추지 못했다」고 답하면 계정은 그대로 남는다(fail-closed).
    // 조용히 닫으면 사용자는 지워진 줄 안다 — 그 침묵을 이 단언이 막는다.
    deleteAccount.mockResolvedValueOnce({ error: { message: "계정 정리에 실패했습니다 (status 500)." } });
    render(<AccountButton />);

    fireEvent.click(screen.getByRole("button", { name: "계정 삭제" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(
      screen.getAllByRole("button", { name: "계정 삭제" }).find((b) => dialog.contains(b))!,
    );

    expect(await screen.findByRole("alert")).toHaveTextContent("계정 정리에 실패했습니다");
    expect(replace).not.toHaveBeenCalled();
  });
});
