// useInvalidatingMutation / useAuthCtx 계약 테스트 — 토큰 부착 + remove→invalidate 순서 + 콜백 위임.

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { ANON_USER_ID, useAuthCtx } from "../use-auth-ctx";
import { useInvalidatingMutation } from "../use-invalidating-mutation";

const authState: { userId: string | null } = { userId: "user_1" };

vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({
    userId: authState.userId,
    isSignedIn: authState.userId !== null,
    getToken: async () => "jwt-token",
  }),
}));

function makeWrapper(qc: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

describe("useAuthCtx", () => {
  it("로그인 상태 — uid = userId", () => {
    authState.userId = "user_1";
    const qc = new QueryClient();
    const { result } = renderHook(() => useAuthCtx(), {
      wrapper: makeWrapper(qc),
    });
    expect(result.current.uid).toBe("user_1");
    expect(result.current.isSignedIn).toBe(true);
  });

  it("로그아웃 상태 — uid = anon sentinel (LESSON-005)", () => {
    authState.userId = null;
    const qc = new QueryClient();
    const { result } = renderHook(() => useAuthCtx(), {
      wrapper: makeWrapper(qc),
    });
    expect(result.current.uid).toBe(ANON_USER_ID);
  });
});

describe("useInvalidatingMutation", () => {
  it("토큰을 mutationFn 에 전달하고 removeKeys → invalidateKeys 순서로 캐시 정리 후 onSuccess 위임", async () => {
    authState.userId = "user_1";
    const qc = new QueryClient();
    const calls: string[] = [];
    const removeSpy = vi
      .spyOn(qc, "removeQueries")
      .mockImplementation((f) => {
        calls.push(`remove:${JSON.stringify(f?.queryKey)}`);
      });
    const invalidateSpy = vi
      .spyOn(qc, "invalidateQueries")
      .mockImplementation(async (f) => {
        calls.push(`invalidate:${JSON.stringify(f?.queryKey)}`);
      });
    const onSuccess = vi.fn();
    const mutationFn = vi.fn(
      async (vars: { id: string }, token: string | null) => ({
        echoed: vars.id,
        token,
      }),
    );

    const { result } = renderHook(
      () =>
        useInvalidatingMutation(
          {
            mutationFn,
            invalidateKeys: (uid, data, vars) => [
              ["domain", "list", uid],
              ["domain", "detail", uid, vars.id, data.echoed],
            ],
            removeKeys: (uid, _data, vars) => [
              ["domain", "detail", uid, vars.id],
            ],
          },
          { onSuccess },
        ),
      { wrapper: makeWrapper(qc) },
    );

    result.current.mutate({ id: "abc" });

    await waitFor(() => expect(onSuccess).toHaveBeenCalledTimes(1));
    expect(mutationFn).toHaveBeenCalledWith({ id: "abc" }, "jwt-token");
    expect(onSuccess).toHaveBeenCalledWith({ echoed: "abc", token: "jwt-token" });
    expect(removeSpy).toHaveBeenCalledTimes(1);
    expect(invalidateSpy).toHaveBeenCalledTimes(2);
    // remove 가 invalidate 보다 먼저.
    expect(calls[0]).toContain("remove:");
    expect(calls[1]).toContain("invalidate:");
    expect(calls[0]).toContain('"user_1","abc"');
  });

  it("실패 시 onError 위임", async () => {
    authState.userId = "user_1";
    const qc = new QueryClient();
    const onError = vi.fn();

    const { result } = renderHook(
      () =>
        useInvalidatingMutation<{ ok: true }, void>(
          {
            mutationFn: async () => {
              throw new Error("boom");
            },
            invalidateKeys: () => [],
          },
          { onError },
        ),
      { wrapper: makeWrapper(qc) },
    );

    result.current.mutate();
    await waitFor(() => expect(onError).toHaveBeenCalledTimes(1));
    expect(onError.mock.calls[0]![0]).toBeInstanceOf(Error);
  });
});
