// Public share page (200 / 410 / 404 / network error 분기) — Sprint 41 Worker H
import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api-base", () => ({ getApiBase: () => "http://test.api" }));

import SharedBacktestPage from "../[token]/page";

const realFetch = global.fetch;

beforeEach(() => {
  global.fetch = vi.fn() as unknown as typeof fetch;
});
afterEach(() => {
  global.fetch = realFetch;
  vi.clearAllMocks();
});

const mockOk = (json: object) =>
  ({
    ok: true,
    status: 200,
    json: async () => json,
  }) as unknown as Response;
const mockStatus = (status: number) =>
  ({ ok: false, status, json: async () => ({}) }) as unknown as Response;

const SAMPLE_DETAIL = {
  id: "1a4b7c2d-3e5f-4a6b-8c9d-0e1f2a3b4c5d",
  strategy_id: "2b5c8d3e-4f6a-4b7c-9d0e-1f2a3b4c5d6e",
  symbol: "BTCUSDT",
  timeframe: "1h",
  period_start: "2024-01-01T00:00:00+00:00",
  period_end: "2024-01-31T00:00:00+00:00",
  status: "completed",
  created_at: "2024-01-01T00:00:00+00:00",
  completed_at: "2024-01-31T01:00:00+00:00",
  initial_capital: "10000",
  config: null,
  metrics: {
    total_return: "0.42",
    sharpe_ratio: "1.85",
    max_drawdown: "-0.12",
    win_rate: "0.60",
    num_trades: 24,
  },
  equity_curve: [
    { timestamp: "2024-01-01T00:00:00+00:00", value: "10000" },
    { timestamp: "2024-01-31T00:00:00+00:00", value: "14200" },
  ],
  error: null,
};

describe("SharedBacktestPage (server component)", () => {
  it("200 — 백테스트 메트릭과 CTA 가 렌더된다", async () => {
    (global.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockOk(SAMPLE_DETAIL),
    );
    const ui = await SharedBacktestPage({
      params: Promise.resolve({ token: "tkn-ok" }),
    });
    render(ui);
    expect(screen.getByText(/BTCUSDT/)).toBeInTheDocument();
    expect(screen.getByText(/총 수익률/)).toBeInTheDocument();
    expect(screen.getByText(/QuantBridge 시작하기/)).toBeInTheDocument();
  });

  it("410 — 해제 안내 문구", async () => {
    (global.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockStatus(410),
    );
    const ui = await SharedBacktestPage({
      params: Promise.resolve({ token: "tkn-revoked" }),
    });
    render(ui);
    expect(
      screen.getByText(/공유 링크가 해제되었습니다/),
    ).toBeInTheDocument();
  });

  it("404 — 찾을 수 없음 안내", async () => {
    (global.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockStatus(404),
    );
    const ui = await SharedBacktestPage({
      params: Promise.resolve({ token: "tkn-missing" }),
    });
    render(ui);
    expect(
      screen.getByText(/공유 링크를 찾을 수 없습니다/),
    ).toBeInTheDocument();
  });

  it("네트워크 에러 — 일반 에러 안내", async () => {
    (global.fetch as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error("network down"),
    );
    const ui = await SharedBacktestPage({
      params: Promise.resolve({ token: "tkn-err" }),
    });
    render(ui);
    expect(screen.getByText(/잠시 후 다시 시도해 주세요/)).toBeInTheDocument();
  });

  it("generateMetadata — og:image path 가 token 기반으로 생성", async () => {
    const { generateMetadata } = await import("../[token]/page");
    const meta = await generateMetadata({
      params: Promise.resolve({ token: "abc-123" }),
    });
    const og = meta.openGraph;
    expect(og?.images).toEqual([
      "/share/backtests/abc-123/opengraph-image",
    ]);
  });
});
