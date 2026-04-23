import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ExchangeAccountsPanel } from "../components/exchange-accounts-panel";

// C-2: ModeBadge 렌더 단위 테스트

vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({ getToken: async () => "test-token" }),
}));

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

test("ExchangeAccountsPanel — DEMO 배지 렌더 (amber 텍스트)", async () => {
  const { apiFetch } = await import("@/lib/api-client");
  vi.mocked(apiFetch).mockResolvedValueOnce({ items: [DEMO_ACCOUNT] });

  render(
    <QueryClientProvider client={makeQc()}>
      <ExchangeAccountsPanel />
    </QueryClientProvider>,
  );

  // DEMO 배지 노출
  const demoBadge = await screen.findByText("DEMO");
  expect(demoBadge).toBeInTheDocument();
  // amber 색상 클래스 확인
  expect(demoBadge).toHaveClass("text-amber-600");
});

test("ExchangeAccountsPanel — LIVE 배지 렌더 (green 텍스트)", async () => {
  const { apiFetch } = await import("@/lib/api-client");
  vi.mocked(apiFetch).mockResolvedValueOnce({ items: [LIVE_ACCOUNT] });

  render(
    <QueryClientProvider client={makeQc()}>
      <ExchangeAccountsPanel />
    </QueryClientProvider>,
  );

  const liveBadge = await screen.findByText("LIVE");
  expect(liveBadge).toBeInTheDocument();
  expect(liveBadge).toHaveClass("text-green-600");
});
