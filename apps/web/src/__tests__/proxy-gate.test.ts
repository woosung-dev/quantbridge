import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

const getSession = vi.fn();
vi.mock("@/lib/auth", () => ({
  auth: { api: { getSession: (...a: unknown[]) => getSession(...a) } },
}));

const getSessionCookie = vi.fn();
vi.mock("better-auth/cookies", () => ({
  getSessionCookie: (...a: unknown[]) => getSessionCookie(...a),
}));

import proxy, { config } from "@/proxy";

const req = (path: string, headers: Record<string, string> = {}) =>
  new NextRequest(new URL(`http://localhost:3000${path}`), {
    headers: new Headers(headers),
  });

const pathnameFromLocation = (location: string | null) => {
  expect(location).not.toBeNull();
  return new URL(location!).pathname;
};

describe("proxy 인증·지역 제한 게이트", () => {
  beforeEach(() => {
    getSession.mockReset();
    getSessionCookie.mockReset();
  });

  it.each([
    "/",
    "/sign-in",
    "/sign-up",
    "/waitlist",
    "/pricing",
    "/maintenance",
    "/disclaimer",
    "/terms",
    "/privacy",
  ])("공개 경로 %s 는 세션을 조회하지 않는다", async (path) => {
    const res = await proxy(req(path));

    expect(getSession).not.toHaveBeenCalled();
    expect(res.status).toBe(200);
  });

  it.each([
    "/api/auth/session",
    "/api/webhooks/tv/abc",
    "/invite/tok123",
    "/share/backtests/tok123",
    "/qb-canon-404-probe",
  ])("와일드카드 공개 경로 %s 는 세션을 조회하지 않는다", async (path) => {
    const res = await proxy(req(path));

    expect(getSession).not.toHaveBeenCalled();
    expect(res.status).toBe(200);
  });

  it.each(["/strategies", "/dashboard", "/orders", "/api/v1/backtests"])(
    "공개가 아닌 경로 %s 는 완전 세션 검증을 한다",
    async (path) => {
      getSession.mockResolvedValue(null);

      await proxy(req(path));

      expect(getSession).toHaveBeenCalledOnce();
    },
  );

  it("CF-IPCountry 제한 국가는 비면제 경로를 /not-available로 보낸다", async () => {
    const res = await proxy(req("/strategies", { "CF-IPCountry": "US" }));

    expect(res.status).toBe(307);
    expect(pathnameFromLocation(res.headers.get("location"))).toBe("/not-available");
  });

  it("X-Vercel-IP-Country 제한 국가도 비면제 경로를 /not-available로 보낸다", async () => {
    const res = await proxy(req("/strategies", { "X-Vercel-IP-Country": "US" }));

    expect(res.status).toBe(307);
    expect(pathnameFromLocation(res.headers.get("location"))).toBe("/not-available");
  });

  it.each([
    "/",
    "/not-available",
    "/disclaimer",
    "/terms",
    "/privacy",
    "/waitlist",
    "/pricing",
    "/maintenance",
    "/api/webhooks/x",
    "/api/auth/x",
    "/share/backtests/x",
  ])("제한 국가여도 geo 면제 경로 %s 는 리다이렉트하지 않는다", async (path) => {
    const res = await proxy(req(path, { "CF-IPCountry": "US" }));

    expect(res.status).toBe(200);
    expect(res.headers.get("location")).toBeNull();
  });

  it("초대 링크는 공개지만 제한 국가에서는 geo 면제가 아니다", async () => {
    const allowedRes = await proxy(req("/invite/tok123"));
    const restrictedRes = await proxy(req("/invite/tok123", { "CF-IPCountry": "US" }));

    expect(allowedRes.status).toBe(200);
    expect(getSession).not.toHaveBeenCalled();
    expect(restrictedRes.status).toBe(307);
    expect(pathnameFromLocation(restrictedRes.headers.get("location"))).toBe("/not-available");
  });

  it("허용 국가는 waitlist를 통과시킨다", async () => {
    const res = await proxy(req("/waitlist", { "CF-IPCountry": "KR" }));

    expect(res.status).toBe(200);
    expect(res.headers.get("location")).toBeNull();
  });

  it("양성 대조: proxy default export와 matcher 두 패턴을 노출한다", () => {
    expect(proxy).toBeTypeOf("function");
    expect(config.matcher).toHaveLength(2);
  });
});
