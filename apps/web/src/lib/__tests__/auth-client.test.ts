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

describe("재발급 축 2종 (REST 401 · WS 4401) 의 교차", () => {
  it("WS 4401 이 REST 401 재발급 도중에 들어와도 정상 사용자를 로그아웃시키지 않는다", async () => {
    // ★두 축은 **같은 만료 토큰에서 같은 순간에** 난다 — 탭 복귀 = React Query refetch(REST 401)
    //   + WS 재연결(4401). WS 축이 `clearAuthTokenCache` 를 직접 부르면 세대가 밀려
    //   in-flight 재발급이 **멀쩡한 토큰을 받아 놓고 null 을 돌려주고**, `apiFetch` 는 그 null 을
    //   「세션 없음」으로 읽어 /sign-in 으로 보낸다. 둘 다 `reissueAuthToken` 을 지나야 한다.
    const stale = token(Math.floor(Date.now() / 1000) + 3600);
    const fresh = token(Math.floor(Date.now() / 1000) + 7200);
    const secondMint = deferred<Response>();
    let mints = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input).endsWith("/api/auth/token")) {
        mints += 1;
        if (mints === 1) {
          return new Response(JSON.stringify({ token: stale }), { status: 200 });
        }
        return secondMint.promise;
      }
      const auth = new Headers(init?.headers).get("authorization");
      return new Response("{}", { status: auth === `Bearer ${fresh}` ? 200 : 401 });
    });
    const assign = vi.fn();
    vi.stubGlobal("location", { pathname: "/strategies", search: "", assign });
    vi.stubGlobal("fetch", fetchMock);
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://api.test");
    const { getAuthToken, reissueAuthToken } = await loadClient();
    const { apiFetch } = await import("../api-client");

    const cachedStale = await getAuthToken();
    expect(cachedStale).toBe(stale);
    expect(mints).toBe(1);

    // ⑴ REST 401 — 재발급이 뜨고 `/api/auth/token` 응답을 기다리는 창이 열린다.
    const restCall = apiFetch("/api/v1/a", { token: cachedStale });
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(mints).toBe(2);

    // ⑵ 그 창 **안에서** WS 4401 이 온다 — realtime-bridge 의 onAuthFailure 와 같은 호출.
    const wsCall = reissueAuthToken();
    expect(mints).toBe(2); // 두 번째 발급도, 추가 세대 상승도 없다

    secondMint.resolve(new Response(JSON.stringify({ token: fresh }), { status: 200 }));

    // 재발급된 토큰은 살아남고 REST 요청은 그것으로 재시도돼 성공한다.
    await expect(restCall).resolves.toEqual({});
    await expect(wsCall).resolves.toBe(fresh);
    expect(assign).not.toHaveBeenCalled(); // 로그인 화면으로 튕기지 않는다
    expect(mints).toBe(2);
    await expect(getAuthToken()).resolves.toBe(fresh);
    expect(mints).toBe(2);
  });
});
