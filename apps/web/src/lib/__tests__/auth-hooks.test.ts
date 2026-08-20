import { describe, expect, it } from "vitest";

import { auth } from "@/lib/auth";

type CreateBefore = (
  user: Record<string, unknown>,
  context: { headers?: Headers; request?: Request } | null,
) => Promise<{ data: Record<string, unknown> } | undefined>;

const authOptions = auth as unknown as {
  options: {
    databaseHooks: { user: { create: { before: CreateBefore } } };
    user: { deleteUser: { beforeDelete: unknown } };
  };
};

const createBefore = authOptions.options.databaseHooks.user.create.before;

describe("auth database hooks", () => {
  it("exposes the signup and deletion hooks", () => {
    expect(createBefore).toBeTypeOf("function");
    expect(authOptions.options.user.deleteUser.beforeDelete).toBeTypeOf("function");
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
});
