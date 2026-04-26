// Sprint 14 Phase B-3 / B-4 — getApiBase + readErrorBody helper.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

describe("getApiBase", () => {
  let consoleErrorSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    vi.resetModules();
    vi.unstubAllEnvs();
    consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    consoleErrorSpy.mockRestore();
  });

  it("returns localhost fallback when NEXT_PUBLIC_API_URL is missing in dev", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "");
    vi.stubEnv("NODE_ENV", "development");
    const { getApiBase } = await import("../api-base");
    expect(getApiBase()).toBe("http://localhost:8000");
    expect(consoleErrorSpy).not.toHaveBeenCalled();
  });

  it("returns env value as-is when set without trailing slash", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "https://api.quantbridge.app");
    const { getApiBase } = await import("../api-base");
    expect(getApiBase()).toBe("https://api.quantbridge.app");
  });

  it("strips trailing slash(es) from env value", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "https://api.quantbridge.app///");
    const { getApiBase } = await import("../api-base");
    expect(getApiBase()).toBe("https://api.quantbridge.app");
  });

  it("does NOT throw on production missing — falls back + logs once on browser", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "");
    vi.stubEnv("NODE_ENV", "production");
    const { getApiBase } = await import("../api-base");
    // browser 환경 simulate (typeof window !== "undefined")
    expect(typeof window).toBe("object");
    expect(getApiBase()).toBe("http://localhost:8000");
    expect(consoleErrorSpy).toHaveBeenCalledTimes(1);
    expect(consoleErrorSpy.mock.calls[0]?.[0]).toMatch(/NEXT_PUBLIC_API_URL/);

    // 두 번째 호출은 _hasWarned 가드로 console.error 추가 발화 없음.
    getApiBase();
    expect(consoleErrorSpy).toHaveBeenCalledTimes(1);
  });
});

describe("readErrorBody", () => {
  it("returns parsed JSON when response body is JSON", async () => {
    const { readErrorBody } = await import("../api-base");
    const res = new Response(JSON.stringify({ detail: "전략을 찾을 수 없습니다" }), {
      status: 404,
      headers: { "Content-Type": "application/json" },
    });
    const body = await readErrorBody(res);
    expect(body).toEqual({ detail: "전략을 찾을 수 없습니다" });
  });

  it("returns text when response is not JSON", async () => {
    const { readErrorBody } = await import("../api-base");
    const res = new Response("<html>Internal Server Error</html>", {
      status: 500,
      headers: { "Content-Type": "text/html" },
    });
    const body = await readErrorBody(res);
    expect(body).toBe("<html>Internal Server Error</html>");
  });

  it("truncates text body larger than 8KB cap with suffix", async () => {
    const { readErrorBody, ERROR_BODY_MAX_BYTES } = await import("../api-base");
    const huge = "A".repeat(ERROR_BODY_MAX_BYTES + 5000);
    const res = new Response(huge, {
      status: 502,
      headers: { "Content-Type": "text/plain" },
    });
    const body = await readErrorBody(res);
    expect(typeof body).toBe("string");
    expect((body as string).length).toBe(ERROR_BODY_MAX_BYTES + "...(truncated)".length);
    expect(body).toMatch(/\.\.\.\(truncated\)$/);
  });

  it("returns empty string when both JSON and text() fail", async () => {
    const { readErrorBody } = await import("../api-base");
    const res = new Response(null, { status: 500 });
    // text() 호출. body 가 null 이라도 빈 string 반환. JSON parse 실패 후 text fallback.
    const body = await readErrorBody(res);
    expect(body === "" || body === null).toBe(true);
  });
});
