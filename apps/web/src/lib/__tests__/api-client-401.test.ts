// apiFetch 의 401 정책 — 재발급기 1회 재시도 · 세션 없음 → /sign-in 1회 · 서버(미등록)는 throw.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

function res(status: number, body: unknown = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function authHeader(call: unknown[]): string | null {
  const init = call[1] as RequestInit | undefined;
  return new Headers(init?.headers).get("authorization");
}

async function loadClient() {
  vi.resetModules();
  return import("../api-client");
}

let assign: ReturnType<typeof vi.fn>;

beforeEach(() => {
  vi.stubEnv("NEXT_PUBLIC_API_URL", "http://api.test");
  assign = vi.fn();
  vi.stubGlobal("location", { pathname: "/strategies", search: "?page=2", assign });
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
  vi.restoreAllMocks();
});

describe("apiFetch 401 정책", () => {
  it("401 → 재발급기 → 새 토큰으로 한 번 재시도해 성공을 돌려준다", async () => {
    const fetchMock = vi
      .fn<() => Promise<Response>>()
      .mockResolvedValueOnce(res(401, { detail: { code: "auth_invalid_token" } }))
      .mockResolvedValueOnce(res(200, { ok: true }));
    vi.stubGlobal("fetch", fetchMock);
    const { apiFetch, setUnauthorizedHandler } = await loadClient();
    const refresh = vi.fn(async () => "fresh");
    setUnauthorizedHandler(refresh);

    await expect(apiFetch("/api/v1/strategies", { token: "stale" })).resolves.toEqual({
      ok: true,
    });
    expect(refresh).toHaveBeenCalledOnce();
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(authHeader(fetchMock.mock.calls[0] ?? [])).toBe("Bearer stale");
    expect(authHeader(fetchMock.mock.calls[1] ?? [])).toBe("Bearer fresh");
    expect(assign).not.toHaveBeenCalled();
  });

  it("새 토큰으로도 401 이면 리다이렉트 없이 throw 하고 무한루프에 빠지지 않는다", async () => {
    const fetchMock = vi.fn(async () => res(401, { detail: { code: "auth_invalid_token" } }));
    vi.stubGlobal("fetch", fetchMock);
    const { apiFetch, ApiError, setUnauthorizedHandler } = await loadClient();
    const refresh = vi.fn(async () => "fresh");
    setUnauthorizedHandler(refresh);

    await expect(apiFetch("/api/v1/strategies", { token: "stale" })).rejects.toBeInstanceOf(
      ApiError,
    );
    expect(refresh).toHaveBeenCalledOnce();
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(assign).not.toHaveBeenCalled();
  });

  it("재발급기가 null(세션 없음)이면 /sign-in 으로 한 번만 보내고 throw 한다", async () => {
    const fetchMock = vi.fn(async () => res(401));
    vi.stubGlobal("fetch", fetchMock);
    const { apiFetch, ApiError, setUnauthorizedHandler } = await loadClient();
    setUnauthorizedHandler(async () => null);

    const results = await Promise.allSettled([
      apiFetch("/api/v1/a", { token: null }),
      apiFetch("/api/v1/b", { token: null }),
      apiFetch("/api/v1/c", { token: "stale" }),
    ]);
    expect(results.map((r) => r.status)).toEqual(["rejected", "rejected", "rejected"]);
    for (const r of results) {
      if (r.status === "rejected") expect(r.reason).toBeInstanceOf(ApiError);
    }
    expect(assign).toHaveBeenCalledOnce();
    expect(assign).toHaveBeenCalledWith("/sign-in?redirect_url=%2Fstrategies%3Fpage%3D2");
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("재발급기가 없으면(서버) 재시도·리다이렉트 없이 즉시 throw 한다", async () => {
    const fetchMock = vi.fn(async () => res(401));
    vi.stubGlobal("fetch", fetchMock);
    const { apiFetch, ApiError } = await loadClient();

    await expect(apiFetch("/api/v1/strategies", { token: "stale" })).rejects.toBeInstanceOf(
      ApiError,
    );
    expect(fetchMock).toHaveBeenCalledOnce();
    expect(assign).not.toHaveBeenCalled();
  });

  it("재발급기 자체가 실패하면 판단을 미루고 원래 401 을 throw 한다", async () => {
    const fetchMock = vi.fn(async () => res(401));
    vi.stubGlobal("fetch", fetchMock);
    const { apiFetch, ApiError, setUnauthorizedHandler } = await loadClient();
    setUnauthorizedHandler(async () => {
      throw new Error("network");
    });

    await expect(apiFetch("/api/v1/strategies", { token: "stale" })).rejects.toBeInstanceOf(
      ApiError,
    );
    expect(fetchMock).toHaveBeenCalledOnce();
    expect(assign).not.toHaveBeenCalled();
  });

  it("401 이 아닌 실패는 재발급기를 부르지 않는다", async () => {
    const fetchMock = vi.fn(async () => res(500));
    vi.stubGlobal("fetch", fetchMock);
    const { apiFetch, setUnauthorizedHandler } = await loadClient();
    const refresh = vi.fn(async () => "fresh");
    setUnauthorizedHandler(refresh);

    await expect(apiFetch("/api/v1/strategies", { token: "t" })).rejects.toThrow();
    expect(refresh).not.toHaveBeenCalled();
    expect(fetchMock).toHaveBeenCalledOnce();
  });
});
