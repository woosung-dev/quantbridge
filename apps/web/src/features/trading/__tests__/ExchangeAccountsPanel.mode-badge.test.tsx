import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ExchangeAccountsPanel } from "../components/exchange-accounts-panel";

// C-2: ModeBadge 렌더 단위 테스트

vi.mock("@/lib/api-client", () => ({
  apiFetch: vi.fn(),
  ApiError: class ApiError extends Error {},
}));

const DEMO_ACCOUNT = {
  id: "a0000000-0000-4000-a000-000000000001",
  exchange: "bybit_futures",
  mode: "demo",
  label: "Bybit Demo",
  api_key_masked: "***masked***",
  created_at: "2026-04-24T00:00:00Z",
};

const LIVE_ACCOUNT = {
  id: "a0000000-0000-4000-a000-000000000002",
  exchange: "bybit_futures",
  mode: "live",
  label: null,
  api_key_masked: "***live***",
  created_at: "2026-04-24T00:00:00Z",
};

function makeQc() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
}

beforeEach(async () => {
  const { apiFetch } = await import("@/lib/api-client");
  vi.mocked(apiFetch).mockReset();
});

// 2026-08-18 톤 역전 — 리스크 서사(데모=안전 기본, 라이브=실자금 주의)에 맞춰
// demo 는 중립 상시 배지, live 는 warn 계열이다. 종전(demo=warn/live=done)은 반대였다.
test("ExchangeAccountsPanel — DEMO 배지는 중립 chip (경고 톤 아님)", async () => {
  const { apiFetch } = await import("@/lib/api-client");
  vi.mocked(apiFetch).mockResolvedValueOnce({ items: [DEMO_ACCOUNT] });

  render(
    <QueryClientProvider client={makeQc()}>
      <ExchangeAccountsPanel />
    </QueryClientProvider>,
  );

  const demoBadge = await screen.findByText("DEMO");
  expect(demoBadge).toBeInTheDocument();
  expect(demoBadge).not.toHaveAttribute("data-tone");
  expect(demoBadge.className).toBe("chip");
});

test("ExchangeAccountsPanel — LIVE 배지 렌더 (warning 톤)", async () => {
  const { apiFetch } = await import("@/lib/api-client");
  vi.mocked(apiFetch).mockResolvedValueOnce({ items: [LIVE_ACCOUNT] });

  render(
    <QueryClientProvider client={makeQc()}>
      <ExchangeAccountsPanel />
    </QueryClientProvider>,
  );

  // Precision Instrument: 리터럴 팔레트 클래스 대신 시맨틱 data-tone 어서션
  // (globals.css [data-tone] 규칙이 색 결정).
  const liveBadge = await screen.findByText("LIVE");
  expect(liveBadge).toBeInTheDocument();
  expect(liveBadge).toHaveAttribute("data-tone", "warning");
  expect(liveBadge).not.toHaveAttribute("data-tone", "success");
});

test("ExchangeAccountsPanel — 읽기 전용 권한을 배지로 표시", async () => {
  const { apiFetch } = await import("@/lib/api-client");
  vi.mocked(apiFetch).mockResolvedValueOnce({
    items: [{ ...DEMO_ACCOUNT, read_only: true }],
  });

  render(
    <QueryClientProvider client={makeQc()}>
      <ExchangeAccountsPanel />
    </QueryClientProvider>,
  );

  const readOnlyBadge = await screen.findByText("읽기 전용");
  expect(readOnlyBadge).toHaveAttribute("data-tone", "warning");
});
