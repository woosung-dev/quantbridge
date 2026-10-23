import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const getSession = vi.fn();
const getToken = vi.fn();
const requestHeaders = vi.hoisted(() => ({ value: new Headers() }));

vi.mock("next/headers", () => ({
  headers: async () => requestHeaders.value,
}));
vi.mock("@/lib/auth", () => ({
  auth: {
    api: {
      getSession: (...args: unknown[]) => getSession(...args),
      getToken: (...args: unknown[]) => getToken(...args),
    },
  },
}));

beforeEach(() => {
  vi.resetModules();
  getSession.mockReset();
  getToken.mockReset();
  requestHeaders.value = new Headers({ cookie: "s=1" });
});

afterEach(() => {
  vi.clearAllMocks();
});

const load = async () => (await import("@/lib/auth-server")).getServerAuth;

describe("getServerAuth", () => {
  it("returns the session user and issued token", async () => {
    getSession.mockResolvedValue({ user: { id: "u1" } });
    getToken.mockResolvedValue({ token: "jwt-x" });

    const getServerAuth = await load();

    expect(typeof getServerAuth).toBe("function");
    await expect(getServerAuth()).resolves.toEqual({ userId: "u1", token: "jwt-x" });
    expect(getSession).toHaveBeenCalledOnce();
  });

  it("returns null values when no session exists", async () => {
    getSession.mockResolvedValue(null);
    getToken.mockResolvedValue({ token: "jwt-x" });

    const getServerAuth = await load();

    await expect(getServerAuth()).resolves.toEqual({ userId: null, token: null });
  });

  it("swallows a session lookup failure", async () => {
    getSession.mockRejectedValue(new Error("database unavailable"));
    getToken.mockResolvedValue({ token: "jwt-x" });

    const getServerAuth = await load();

    await expect(getServerAuth()).resolves.toEqual({ userId: null, token: null });
  });

  it("keeps the user when token issuance fails", async () => {
    getSession.mockResolvedValue({ user: { id: "u1" } });
    getToken.mockRejectedValue(new Error("token unavailable"));

    const getServerAuth = await load();

    await expect(getServerAuth()).resolves.toEqual({ userId: "u1", token: null });
  });

  it.each([undefined, {}])("returns a null token for issued value %j", async (issued) => {
    getSession.mockResolvedValue({ user: { id: "u1" } });
    getToken.mockResolvedValue(issued);

    const getServerAuth = await load();

    await expect(getServerAuth()).resolves.toEqual({ userId: "u1", token: null });
  });

  it("starts token issuance before a slow session lookup resolves", async () => {
    let resolveSession: ((value: { user: { id: string } }) => void) | undefined;
    getSession.mockReturnValue(
      new Promise<{ user: { id: string } }>((resolve) => {
        resolveSession = resolve;
      }),
    );
    getToken.mockResolvedValue({ token: "jwt-x" });

    const getServerAuth = await load();
    const result = getServerAuth();

    await vi.waitFor(() => {
      expect(getSession).toHaveBeenCalledOnce();
    });
    expect(getToken).toHaveBeenCalledOnce();

    resolveSession?.({ user: { id: "u1" } });

    await expect(result).resolves.toEqual({ userId: "u1", token: "jwt-x" });
  });

  it("skips session lookup and token issuance when the request has no cookies", async () => {
    requestHeaders.value = new Headers();
    const getServerAuth = await load();

    await expect(getServerAuth()).resolves.toEqual({ userId: null, token: null });
    expect(getSession).not.toHaveBeenCalled();
    expect(getToken).not.toHaveBeenCalled();
  });
});

describe("getServerSession", () => {
  it("returns verified identity without issuing a token", async () => {
    getSession.mockResolvedValue({ user: { id: "u1" } });
    const { getServerSession } = await import("@/lib/auth-server");

    await expect(getServerSession()).resolves.toEqual({ userId: "u1" });
    expect(getSession).toHaveBeenCalledOnce();
    expect(getToken).not.toHaveBeenCalled();
  });

  it("skips authentication work when the request has no cookies", async () => {
    requestHeaders.value = new Headers();
    const { getServerSession } = await import("@/lib/auth-server");

    await expect(getServerSession()).resolves.toEqual({ userId: null });
    expect(getSession).not.toHaveBeenCalled();
    expect(getToken).not.toHaveBeenCalled();
  });

  it("does not trust cookie presence as authentication", async () => {
    getSession.mockResolvedValue(null);
    const { getServerSession } = await import("@/lib/auth-server");

    await expect(getServerSession()).resolves.toEqual({ userId: null });
    expect(getSession).toHaveBeenCalledWith({ headers: requestHeaders.value });
    expect(getToken).not.toHaveBeenCalled();
  });

  it("degrades to anonymous identity when session lookup fails", async () => {
    getSession.mockRejectedValue(new Error("database unavailable"));
    const { getServerSession } = await import("@/lib/auth-server");

    await expect(getServerSession()).resolves.toEqual({ userId: null });
    expect(getToken).not.toHaveBeenCalled();
  });
});
