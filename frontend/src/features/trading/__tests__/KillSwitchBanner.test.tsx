import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { KillSwitchBanner } from "@/app/(dashboard)/trading/_components/kill-switch-banner";

// C-1: KillSwitchBanner 단위 테스트
// - KS API 오류 → 황색 경고 배너 (ks-error-banner)
// - active 이벤트 → destructive 배너 + 한국어 레이블 (ks-active-banner)
// - resolved 이벤트만 → 배너 없음
// - 알 수 없는 trigger_type → fallback 표시

vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({ getToken: async () => "test-token" }),
}));

// apiFetch를 최상위 vi.mock으로 제어. 각 테스트에서 mockResolvedValueOnce로 덮어씀.
vi.mock("@/lib/api-client", () => ({
  apiFetch: vi.fn(),
  ApiError: class ApiError extends Error {},
}));

const ACTIVE_KS_EVENT = {
  id: "b0000000-0000-4000-b000-000000000001",
  trigger_type: "daily_loss",
  trigger_value: "600.00",
  threshold: "500.00",
  triggered_at: "2026-04-24T10:00:00Z",
  resolved_at: null,
};

const RESOLVED_KS_EVENT = {
  id: "b0000000-0000-4000-b000-000000000001",
  trigger_type: "daily_loss",
  trigger_value: "600.00",
  threshold: "500.00",
  triggered_at: "2026-04-24T10:00:00Z",
  resolved_at: "2026-04-24T11:00:00Z",
};

function makeQc() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
}

describe("KillSwitchBanner", () => {
  beforeEach(async () => {
    // apiFetch mock 초기화 — vi.mock의 apiFetch 인스턴스를 가져옴
    const { apiFetch } = await import("@/lib/api-client");
    vi.mocked(apiFetch).mockReset();
  });

  test("resolved 이벤트만 → 배너 렌더 안 함", async () => {
    const { apiFetch } = await import("@/lib/api-client");
    vi.mocked(apiFetch).mockResolvedValueOnce({ items: [RESOLVED_KS_EVENT] });

    render(
      <QueryClientProvider client={makeQc()}>
        <KillSwitchBanner />
      </QueryClientProvider>,
    );

    // 데이터 로드 완료 대기 — 배너가 없어야 함
    await new Promise((r) => setTimeout(r, 50));
    expect(screen.queryByTestId("ks-active-banner")).not.toBeInTheDocument();
    expect(screen.queryByTestId("ks-error-banner")).not.toBeInTheDocument();
  });

  test("active 이벤트 존재 → destructive 배너 + 한국어 레이블", async () => {
    const { apiFetch } = await import("@/lib/api-client");
    vi.mocked(apiFetch).mockResolvedValueOnce({ items: [ACTIVE_KS_EVENT] });

    render(
      <QueryClientProvider client={makeQc()}>
        <KillSwitchBanner />
      </QueryClientProvider>,
    );

    const banner = await screen.findByTestId("ks-active-banner");
    expect(banner).toBeInTheDocument();
    // daily_loss → 한국어 레이블 확인
    expect(banner).toHaveTextContent("일일 손실 한도 초과");
  });

  test("알 수 없는 trigger_type (Zod schema enum 미지원) → API 오류로 처리되어 황색 경고 배너", async () => {
    // KillSwitchEventSchema.trigger_type은 z.enum([...])으로 엄격히 검증.
    // 알 수 없는 trigger_type이 API에서 내려오면 Zod parse 실패 → React Query error 상태 →
    // ks-error-banner 렌더. KS_TRIGGER_LABELS fallback은 schema를 통과한 알려진 값에만 적용.
    const { apiFetch } = await import("@/lib/api-client");
    const unknownEvent = {
      ...ACTIVE_KS_EVENT,
      trigger_type: "unknown_custom_trigger",
    };
    vi.mocked(apiFetch).mockResolvedValueOnce({ items: [unknownEvent] });

    render(
      <QueryClientProvider client={makeQc()}>
        <KillSwitchBanner />
      </QueryClientProvider>,
    );

    // Zod parse 실패 → error 상태 → 황색 경고 배너
    const errorBanner = await screen.findByTestId("ks-error-banner");
    expect(errorBanner).toBeInTheDocument();
  });

  test("API 오류 → 황색 경고 배너", async () => {
    const { apiFetch } = await import("@/lib/api-client");
    vi.mocked(apiFetch).mockRejectedValueOnce(
      new Error("500 Internal Server Error"),
    );

    render(
      <QueryClientProvider client={makeQc()}>
        <KillSwitchBanner />
      </QueryClientProvider>,
    );

    const errorBanner = await screen.findByTestId("ks-error-banner");
    expect(errorBanner).toBeInTheDocument();
    expect(errorBanner).toHaveTextContent("불러오지 못했습니다");
  });
});
