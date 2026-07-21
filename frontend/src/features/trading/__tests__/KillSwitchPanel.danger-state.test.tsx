// Sprint 44 W F3 — KillSwitchPanel danger 상태 (active vs ok) 시각 polish 검증
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, test, vi } from "vitest";

import { KillSwitchPanel } from "../components/kill-switch-panel";

vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({ getToken: async () => "test-token" }),
}));

vi.mock("@/lib/api-client", () => ({
  apiFetch: vi.fn().mockResolvedValue({ items: [] }),
  ApiError: class ApiError extends Error {},
}));

describe("KillSwitchPanel — Sprint 44 W F3 danger state polish", () => {
  test("active=0 시 data-state='ok' + '이상 없음' 표시", async () => {
    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={qc}>
        <KillSwitchPanel />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("이상 없음")).toBeInTheDocument();
    const panel = screen.getByTestId("kill-switch-panel");
    expect(panel).toHaveAttribute("data-state", "ok");
    // qb-danger-pulse class 미적용
    expect(panel.className).not.toContain("qb-danger-pulse");
  });

  // C 이식(S8) — active KS 의 '해결' 버튼은 공용 .btn.btn-danger 를 소비한다.
  test("active KS '해결' 버튼은 danger 톤 공용 버튼", async () => {
    const { apiFetch } = await import("@/lib/api-client");
    vi.mocked(apiFetch).mockResolvedValueOnce({
      items: [
        {
          id: "11111111-1111-4111-a111-111111111111",
          trigger_type: "daily_loss",
          trigger_value: "120",
          threshold: "100",
          triggered_at: "2026-06-26T00:00:00Z",
          resolved_at: null,
        },
      ],
    });
    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={qc}>
        <KillSwitchPanel />
      </QueryClientProvider>,
    );

    const resolveBtn = await screen.findByRole("button", { name: /해결/ });
    expect(resolveBtn.className).toContain("btn-danger");
    // 패널이 active 상태로 전환됐는지도 확인.
    expect(screen.getByTestId("kill-switch-panel")).toHaveAttribute(
      "data-state",
      "active",
    );
  });
});
