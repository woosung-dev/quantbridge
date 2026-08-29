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

  it("보호 경로는 세션이 없으면 /sign-in으로 보낸다", async () => {
    getSession.mockResolvedValue(null);

    const res = await proxy(req("/strategies"));

    expect(res.status).toBe(307);
    expect(pathnameFromLocation(res.headers.get("location"))).toBe("/sign-in");
  });

  it("보호 경로 로그인 리다이렉트는 원래 경로와 쿼리만 redirect_url로 보존한다", async () => {
    getSession.mockResolvedValue(null);

    const res = await proxy(req("/backtests/abc?tab=trades"));
    const location = new URL(res.headers.get("location")!);

    expect(res.status).toBe(307);
    expect(location.pathname).toBe("/sign-in");
    expect(location.searchParams.get("redirect_url")).toBe("/backtests/abc?tab=trades");
    expect([...location.searchParams.keys()]).toEqual(["redirect_url"]);
  });

  it("보호 경로는 완전 세션이 있으면 통과시킨다", async () => {
    getSession.mockResolvedValue({ user: { id: "u1" } });

    const res = await proxy(req("/strategies"));

    expect(res.status).toBe(200);
    expect(res.headers.get("location")).toBeNull();
  });

  it("보호 경로는 쿠키 존재 검사로 인증을 우회하지 않는다", async () => {
    getSession.mockResolvedValue(null);
    getSessionCookie.mockReturnValue("forged-cookie");

    const res = await proxy(req("/strategies"));

    expect(res.status).toBe(307);
    expect(getSessionCookie).not.toHaveBeenCalled();
  });

  it("루트는 쿠키가 있으면 DB 세션 조회 없이 /strategies로 보낸다", async () => {
    getSessionCookie.mockReturnValue("session-cookie");

    const res = await proxy(req("/"));

    expect(res.status).toBe(307);
    expect(pathnameFromLocation(res.headers.get("location"))).toBe("/strategies");
    expect(getSession).not.toHaveBeenCalled();
  });

  it("루트는 쿠키가 없으면 리다이렉트하지 않는다", async () => {
    const res = await proxy(req("/"));

    expect(res.status).toBe(200);
    expect(res.headers.get("location")).toBeNull();
  });

  it("pricing은 쿠키가 있어도 루트 UX 리다이렉트를 적용하지 않는다", async () => {
    getSessionCookie.mockReturnValue("session-cookie");

    const res = await proxy(req("/pricing"));

    expect(res.status).toBe(200);
    expect(res.headers.get("location")).toBeNull();
    expect(getSession).not.toHaveBeenCalled();
  });

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

// ── matcher 자체를 잰다 ────────────────────────────────────────────────────────
// ★위 테스트들은 `proxy()` 를 **직접 부른다**. 그래서 Next 가 애초에 proxy 를 안 태우는 경로는
//   한 건도 못 본다 — 게이트 우회는 함수 안이 아니라 `config.matcher` 에서 일어난다.
//   2026-08-30 아키텍처 감사: 정적 자산 제외 lookahead 에 앵커가 없어서
//   `/backtests/<id>.png` 같은 **동적 세그먼트 경로가 통째로 인증을 건너뛰었다.**
describe("config.matcher — 어떤 경로가 proxy 를 타는가", () => {
  const runsProxy = (pathname: string) => new RegExp(`^${config.matcher[0]}$`).test(pathname);

  it.each([
    ["/backtests/00000000-0000-0000-0000-000000000000.png"],
    ["/backtests/anything.css"],
    ["/optimizer/1.ico"],
    ["/strategies/x.svg"],
    ["/trading/report.pdf.png"],
  ])("보호 라우트는 확장자가 붙어도 proxy 를 탄다: %s", (pathname) => {
    expect(runsProxy(pathname)).toBe(true);
  });

  it.each([["/backtests"], ["/backtests/abc"], ["/dashboard"], ["/strategies/abc/edit"]])(
    "음성 대조: 평범한 보호 라우트도 당연히 proxy 를 탄다: %s",
    (pathname) => {
      expect(runsProxy(pathname)).toBe(true);
    },
  );

  it.each([["/favicon.ico"], ["/icon.svg"]])("루트 정적 자산은 여전히 제외된다: %s", (pathname) => {
    expect(runsProxy(pathname)).toBe(false);
  });
});
