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

test("ExchangeAccountsPanel — DEMO 배지 렌더 (warning 톤)", async () => {
  const { apiFetch } = await import("@/lib/api-client");
  vi.mocked(apiFetch).mockResolvedValueOnce({ items: [DEMO_ACCOUNT] });

  render(
    <QueryClientProvider client={makeQc()}>
      <ExchangeAccountsPanel />
    </QueryClientProvider>,
  );

  // DEMO 배지 노출 — Precision Instrument: 리터럴 팔레트 클래스 대신
  // 시맨틱 data-tone 어서션 (globals.css [data-tone] 규칙이 색 결정).
  const demoBadge = await screen.findByText("DEMO");
  expect(demoBadge).toBeInTheDocument();
  expect(demoBadge).toHaveAttribute("data-tone", "warning");
});

test("ExchangeAccountsPanel — LIVE 배지 렌더 (success 톤)", async () => {
  const { apiFetch } = await import("@/lib/api-client");
  vi.mocked(apiFetch).mockResolvedValueOnce({ items: [LIVE_ACCOUNT] });

  render(
    <QueryClientProvider client={makeQc()}>
      <ExchangeAccountsPanel />
    </QueryClientProvider>,
  );

  const liveBadge = await screen.findByText("LIVE");
  expect(liveBadge).toBeInTheDocument();
  expect(liveBadge).toHaveAttribute("data-tone", "success");
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
