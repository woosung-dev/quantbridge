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
});
