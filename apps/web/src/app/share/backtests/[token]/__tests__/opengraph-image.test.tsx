// 공유 OG 이미지의 정적 계약과 실패 시 fallback 렌더링을 고정한다.
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const imageResponseSpy = vi.hoisted(() => vi.fn());

type ImageResponseCall = [ReactNode, { width: number; height: number }];

function collectText(node: ReactNode): string[] {
  if (typeof node === "string" || typeof node === "number") return [String(node)];
  if (Array.isArray(node)) return node.flatMap(collectText);
  if (node && typeof node === "object" && "props" in node) {
    return collectText((node as { props?: { children?: ReactNode } }).props?.children ?? null);
  }
  return [];
}

function mockFetch(responder: (input: RequestInfo | URL, init?: RequestInit) => Promise<unknown>) {
  const fetchMock = vi.fn(responder);
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function jsonResponse(body: unknown, ok = true) {
  return { ok, json: async () => body };
}

function minimumDetail(totalReturn: unknown = "0.1234") {
  return {
    id: "11111111-1111-4111-8111-111111111111",
    strategy_id: "22222222-2222-4222-8222-222222222222",
    symbol: "BTC/USDT",
    timeframe: "1h",
    period_start: "2026-08-01T00:00:00+00:00",
    period_end: "2026-08-02T00:00:00+00:00",
    status: "completed",
    created_at: "2026-08-02T00:00:00+00:00",
    completed_at: "2026-08-02T00:00:00+00:00",
    initial_capital: "10000",
    metrics: {
      total_return: totalReturn,
      sharpe_ratio: "1.5",
      max_drawdown: "-0.056",
      win_rate: "0.5",
      num_trades: 7,
    },
  };
}

async function loadOG() {
  return import("../opengraph-image");
}

async function renderOG(token = "share-token") {
  imageResponseSpy.mockClear();
  const { default: OG } = await loadOG();

  await OG({ params: Promise.resolve({ token }) });

  expect(imageResponseSpy).toHaveBeenCalledOnce();
  const call = imageResponseSpy.mock.calls[0] as unknown as ImageResponseCall | undefined;
  if (!call) throw new Error("ImageResponse가 호출되지 않았습니다");
  return { element: call[0], options: call[1], text: collectText(call[0]) };
}

describe("공유 백테스트 OG 이미지", () => {
  beforeEach(() => {
    vi.resetModules();
    imageResponseSpy.mockReset();
    vi.doMock("next/og", () => ({ ImageResponse: imageResponseSpy }));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.doUnmock("next/og");
    vi.resetModules();
  });

  it("OG 모듈 상수 세 가지를 고정한다", async () => {
    const { contentType, runtime, size } = await loadOG();

    expect(runtime).toBe("nodejs");
    expect(size).toEqual({ width: 1200, height: 630 });
    expect(contentType).toBe("image/png");
  });

  it("ImageResponse에 모듈 size 객체를 그대로 넘긴다", async () => {
    mockFetch(async () => jsonResponse(minimumDetail()));
    const route = await loadOG();

    await route.default({ params: Promise.resolve({ token: "share-token" }) });

    expect(imageResponseSpy).toHaveBeenCalledOnce();
    const call = imageResponseSpy.mock.calls[0] as unknown as ImageResponseCall | undefined;
    expect(call?.[1]).toBe(route.size);
    expect(call?.[1]).toEqual({ width: 1200, height: 630 });
  });

  it("fetch 예외에서도 fallback OG를 만든다", async () => {
    mockFetch(async () => Promise.reject(new Error("network failed")));

    const rendered = await renderOG();

    expect(rendered.text).toContain("—");
  });

  it("비200 응답은 fetch 예외와 같은 fallback 마크업이다", async () => {
    mockFetch(async () => Promise.reject(new Error("network failed")));
    const rejected = await renderOG();

    mockFetch(async () => jsonResponse({}, false));
    const nonOk = await renderOG();

    expect(nonOk.element).toEqual(rejected.element);
    expect(nonOk.text).toEqual(rejected.text);
  });

  it("스키마 불일치는 다른 실패와 같은 fallback 마크업이다", async () => {
    mockFetch(async () => Promise.reject(new Error("network failed")));
    const rejected = await renderOG();

    mockFetch(async () => jsonResponse({ 엉뚱한: "모양" }));
    const malformed = await renderOG();

    expect(malformed.element).toEqual(rejected.element);
    expect(malformed.text).toEqual(rejected.text);
  });

  it("정상 응답의 symbol과 timeframe을 그린다", async () => {
    mockFetch(async () => jsonResponse(minimumDetail()));

    const rendered = await renderOG();

    expect(rendered.text).toContain("BTC/USDT");
    expect(rendered.text).toContain("1h");
  });

  it("토큰을 URL 인코딩하고 cache: no-store로 조회한다", async () => {
    const fetchMock = mockFetch(async () => jsonResponse(minimumDetail()));
    const token = "a/b?c=1";

    await renderOG(token);

    const [url, init] = fetchMock.mock.calls[0] ?? [];
    expect(String(url)).toContain(encodeURIComponent(token));
    expect(init).toEqual({ cache: "no-store" });
  });

  it.each([
    ["null", null],
    ["NaN", Number.NaN],
    ["비숫자 문자열", "not-a-number"],
  ])("total_return이 %s이면 NaN·Infinity 대신 fallback을 그린다", async (_, value) => {
    mockFetch(async () => jsonResponse(minimumDetail(value)));

    const rendered = await renderOG();

    expect(rendered.text).toContain("—");
    expect(rendered.text.join(" ")).not.toMatch(/NaN|Infinity/);
  });
});
