import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("better-auth/react", () => ({
  createAuthClient: () => ({
    useSession: vi.fn(),
    signIn: { email: vi.fn() },
    signUp: { email: vi.fn() },
    signOut: vi.fn(),
    deleteUser: vi.fn(),
  }),
}));
vi.unmock("@/lib/auth-client");

interface Deferred<T> {
  promise: Promise<T>;
  resolve: (value: T) => void;
}

function deferred<T>(): Deferred<T> {
  let resolve: ((value: T) => void) | undefined;
  const promise = new Promise<T>((next) => {
    resolve = next;
  });
  return { promise, resolve: resolve! };
}

function token(expSeconds = Math.floor(Date.now() / 1000) + 3600): string {
  const payload = btoa(JSON.stringify({ exp: expSeconds }))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
  return `header.${payload}.signature`;
}

async function loadClient() {
  vi.resetModules();
  return import("../auth-client");
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("getAuthToken", () => {
  it("같은 세대의 동시 요청은 한 번만 발급하고 결과를 재사용한다", async () => {
    const request = deferred<Response>();
    const fetchMock = vi.fn(() => request.promise);
    vi.stubGlobal("fetch", fetchMock);
    const { getAuthToken } = await loadClient();

    const first = getAuthToken();
    const second = getAuthToken();

    expect(fetchMock).toHaveBeenCalledOnce();
    request.resolve(new Response(JSON.stringify({ token: token() }), { status: 200 }));

    await expect(Promise.all([first, second])).resolves.toEqual([
      expect.any(String),
      expect.any(String),
    ]);
    await expect(getAuthToken()).resolves.toEqual(expect.any(String));
    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it("cache clear 전의 늦은 응답은 새 세대 캐시나 inFlight 를 덮어쓰지 않는다", async () => {
    const firstRequest = deferred<Response>();
    const secondRequest = deferred<Response>();
    const fetchMock = vi
      .fn<() => Promise<Response>>()
      .mockReturnValueOnce(firstRequest.promise)
      .mockReturnValueOnce(secondRequest.promise);
    vi.stubGlobal("fetch", fetchMock);
    const { clearAuthTokenCache, getAuthToken } = await loadClient();

    const first = getAuthToken();
    clearAuthTokenCache();
    const second = getAuthToken();
    expect(fetchMock).toHaveBeenCalledTimes(2);

    firstRequest.resolve(new Response(JSON.stringify({ token: token() }), { status: 200 }));
    await expect(first).resolves.toBeNull();

    // A 의 finally 가 B 의 inFlight 를 지우면 여기서 세 번째 HTTP 요청이 생긴다.
    const secondJoin = getAuthToken();
    expect(fetchMock).toHaveBeenCalledTimes(2);
    const nextToken = token();
    secondRequest.resolve(new Response(JSON.stringify({ token: nextToken }), { status: 200 }));

    await expect(Promise.all([second, secondJoin])).resolves.toEqual([nextToken, nextToken]);
    await expect(getAuthToken()).resolves.toBe(nextToken);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
