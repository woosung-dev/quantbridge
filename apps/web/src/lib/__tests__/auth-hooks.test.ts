import { afterEach, describe, expect, it, vi } from "vitest";

import { auth } from "@/lib/auth";

type CreateBefore = (
  user: Record<string, unknown>,
  context: { headers?: Headers; request?: Request } | null,
) => Promise<{ data: Record<string, unknown> } | undefined>;

type BeforeDelete = (user: unknown, request?: Request) => Promise<void>;

const authOptions = auth as unknown as {
  options: {
    databaseHooks: { user: { create: { before: CreateBefore } } };
    user: { deleteUser: { beforeDelete: BeforeDelete } };
  };
};

const createBefore = authOptions.options.databaseHooks.user.create.before;
const beforeDelete = (
  auth as unknown as {
    options: {
      user: {
        deleteUser: {
          beforeDelete: (u: unknown, req?: Request) => Promise<void>;
        };
      };
    };
  }
).options.user.deleteUser.beforeDelete;

describe("auth database hooks", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("exposes the signup and deletion hooks", () => {
    expect(createBefore).toBeTypeOf("function");
    expect(beforeDelete).toBeTypeOf("function");
  });

  it("rejects signups from a restricted Cloudflare country", async () => {
    await expect(
      createBefore({ email: "blocked@example.com" }, { headers: new Headers({ "cf-ipcountry": "US" }) }),
    ).rejects.toMatchObject({
      status: "FORBIDDEN",
      body: { code: "GEO_BLOCKED_COUNTRY" },
    });
  });

  it("normalizes lowercase Cloudflare country codes before blocking", async () => {
    await expect(
      createBefore({ email: "blocked@example.com" }, { headers: new Headers({ "cf-ipcountry": "us" }) }),
    ).rejects.toMatchObject({
      status: "FORBIDDEN",
      body: { code: "GEO_BLOCKED_COUNTRY" },
    });
  });

  it("trims Cloudflare country codes before blocking", async () => {
    await expect(
      createBefore({ email: "blocked@example.com" }, { headers: new Headers({ "cf-ipcountry": " US " }) }),
    ).rejects.toMatchObject({
      status: "FORBIDDEN",
      body: { code: "GEO_BLOCKED_COUNTRY" },
    });
  });

  it("uses Vercel country headers and prioritizes Cloudflare", async () => {
    await expect(
      createBefore(
        { email: "blocked@example.com" },
        { headers: new Headers({ "x-vercel-ip-country": "US" }) },
      ),
    ).rejects.toMatchObject({
      status: "FORBIDDEN",
      body: { code: "GEO_BLOCKED_COUNTRY" },
    });

    await expect(
      createBefore(
        { email: "blocked@example.com" },
        { headers: new Headers({ "cf-ipcountry": "US", "x-vercel-ip-country": "KR" }) },
      ),
    ).rejects.toMatchObject({
      status: "FORBIDDEN",
      body: { code: "GEO_BLOCKED_COUNTRY" },
    });
  });

  it("passes allowed signups through with their country and original fields", async () => {
    await expect(
      createBefore(
        { email: "allowed@example.com", name: "Allowed User" },
        { headers: new Headers({ "cf-ipcountry": "KR" }) },
      ),
    ).resolves.toEqual({
      data: { email: "allowed@example.com", name: "Allowed User", country: "KR" },
    });
  });

  it("allows missing country headers and stores null", async () => {
    const user = { email: "local@example.com" };

    await expect(createBefore(user, null)).resolves.toEqual({ data: { ...user, country: null } });
    await expect(createBefore(user, {})).resolves.toEqual({ data: { ...user, country: null } });
    await expect(
      createBefore(user, { headers: new Headers({ "x-request-id": "request-id" }) }),
    ).resolves.toEqual({ data: { ...user, country: null } });
  });

  it("stores null for non-alpha-2 country values", async () => {
    const user = { email: "invalid-country@example.com" };

    for (const country of ["USA", "U", ""]) {
      await expect(
        createBefore(user, { headers: new Headers({ "cf-ipcountry": country }) }),
      ).resolves.toEqual({ data: { ...user, country: null } });
    }
  });

  it("reads country headers from the request context", async () => {
    await expect(
      createBefore(
        { email: "request-context@example.com" },
        { request: new Request("http://x", { headers: { "cf-ipcountry": "KR" } }) },
      ),
    ).resolves.toEqual({ data: { email: "request-context@example.com", country: "KR" } });
  });

  it("allows deletion after the API cleanup succeeds", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(auth.api, "getToken").mockResolvedValue({ token: "jwt-x" } as never);

    await expect(beforeDelete({}, new Request("http://app.local/delete"))).resolves.toBeUndefined();

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/v1\/auth\/me$/),
      {
        method: "DELETE",
        headers: { Authorization: "Bearer jwt-x" },
      },
    );
  });

  it("allows retry when the API reports an already inactive user", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: { code: "auth_user_inactive" } }), { status: 403 }),
    );
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(auth.api, "getToken").mockResolvedValue({ token: "jwt-x" } as never);

    // 멱등 — 우리 쪽 정리는 이미 끝났다는 뜻이다(codex P2).
    await expect(beforeDelete({}, new Request("http://app.local/delete"))).resolves.toBeUndefined();
  });

  it("rejects a 403 response with a different error code", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: { code: "forbidden" } }), { status: 403 }),
    );
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(auth.api, "getToken").mockResolvedValue({ token: "jwt-x" } as never);

    await expect(beforeDelete({}, new Request("http://app.local/delete"))).rejects.toThrow("status 403");
  });

  it("rejects a 403 response whose body is not JSON", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("not-json", { status: 403 }));
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(auth.api, "getToken").mockResolvedValue({ token: "jwt-x" } as never);

    await expect(beforeDelete({}, new Request("http://app.local/delete"))).rejects.toThrow("status 403");
  });

  it("rejects a 500 cleanup failure", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 500 }));
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(auth.api, "getToken").mockResolvedValue({ token: "jwt-x" } as never);

    await expect(beforeDelete({}, new Request("http://app.local/delete"))).rejects.toThrow("status 500");
  });

  it("rejects a 502 cleanup failure", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 502 }));
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(auth.api, "getToken").mockResolvedValue({ token: "jwt-x" } as never);

    await expect(beforeDelete({}, new Request("http://app.local/delete"))).rejects.toThrow("status 502");
  });

  it("rejects deletion without a request and does not call the API", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(auth.api, "getToken").mockResolvedValue({ token: "jwt-x" } as never);

    await expect(beforeDelete({}, undefined)).rejects.toThrow("요청 컨텍스트");

    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("rejects deletion without a token and does not call the API", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(auth.api, "getToken").mockResolvedValue(null as never);

    await expect(beforeDelete({}, new Request("http://app.local/delete"))).rejects.toThrow("토큰");

    expect(fetchMock).not.toHaveBeenCalled();
  });
});
