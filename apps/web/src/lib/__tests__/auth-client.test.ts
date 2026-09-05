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

describe("apiFetch 401 재발급기 (모듈 로드 시 등록)", () => {
  it("동시 401 3건은 /api/auth/token 을 한 번만 부르고 전부 새 토큰으로 성공한다", async () => {
    const stale = token(Math.floor(Date.now() / 1000) + 3600);
    const fresh = token(Math.floor(Date.now() / 1000) + 7200);
    let mints = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input).endsWith("/api/auth/token")) {
        mints += 1;
        return new Response(JSON.stringify({ token: mints === 1 ? stale : fresh }), {
          status: 200,
        });
      }
      const auth = new Headers(init?.headers).get("authorization");
      return new Response("{}", { status: auth === `Bearer ${fresh}` ? 200 : 401 });
    });
    vi.stubGlobal("fetch", fetchMock);
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://api.test");
    const { getAuthToken } = await loadClient();
    const { apiFetch } = await import("../api-client");

    // 캐시에 stale 을 심는다 — 서버 기준으로는 이미 만료된 토큰이다.
    const cachedStale = await getAuthToken();
    expect(cachedStale).toBe(stale);
    expect(mints).toBe(1);

    await expect(
      Promise.all([
        apiFetch("/api/v1/a", { token: cachedStale }),
        apiFetch("/api/v1/b", { token: cachedStale }),
        apiFetch("/api/v1/c", { token: cachedStale }),
      ]),
    ).resolves.toEqual([{}, {}, {}]);

    // 재발급은 정확히 1회. N 회였다면 세대 카운터가 N 번 올라 앞선 응답이 null 로 버려지고
    // 그 요청들은 「세션 없음」으로 오판돼 로그인 화면으로 튕겼을 것이다.
    expect(mints).toBe(2);
    await expect(getAuthToken()).resolves.toBe(fresh);
    expect(mints).toBe(2);
  });
});
