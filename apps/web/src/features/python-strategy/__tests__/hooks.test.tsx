import { afterEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { ApiError } from "@/lib/api-client";
import { backtestDraft } from "../defaults";
import { usePythonLab } from "../hooks";
import { makeRun, STRATEGY } from "./fixtures";

const api = vi.hoisted(() => ({
  getPythonCapabilities: vi.fn(),
  listPythonStrategies: vi.fn(),
  listPythonRuns: vi.fn(),
  getPythonRun: vi.fn(),
  savePythonStrategy: vi.fn(),
  startPythonBacktest: vi.fn(),
  cancelPythonRun: vi.fn(),
}));
vi.mock("../api", () => api);
vi.mock("@/hooks/use-auth-ctx", () => ({
  useAuthCtx: () => ({ uid: "user", getToken: async () => "token" }),
}));
let client: QueryClient;
function setup() {
  client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  api.getPythonCapabilities.mockResolvedValue({ available: true, reason: null });
  api.listPythonStrategies.mockResolvedValue({ items: [STRATEGY] });
  api.listPythonRuns.mockResolvedValue({ items: [] });
  api.startPythonBacktest.mockResolvedValue(makeRun());
  api.getPythonRun.mockResolvedValue(makeRun({ status: "completed" }));
  return renderHook(usePythonLab, {
    wrapper: ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    ),
  });
}
afterEach(() => {
  cleanup();
  client?.clear();
  vi.resetAllMocks();
});
describe("Python 실험실 버전 고정", () => {
  it("현재 편집기에 선택한 저장 버전을 실행 요청에 고정한다", async () => {
    const { result } = setup();
    act(() => result.current.selectStrategy(STRATEGY));
    act(() => result.current.startRun(backtestDraft()));
    await waitFor(() =>
      expect(api.startPythonBacktest).toHaveBeenCalledWith(
        STRATEGY.id,
        expect.objectContaining({ expected_version_id: STRATEGY.version_id }),
        "token",
      ),
    );
  });
  it("버전 충돌은 최신 목록을 재조회하고 편집기를 조용히 교체하지 않는다", async () => {
    const { result } = setup();
    await waitFor(() => expect(result.current.strategies.isSuccess).toBe(true));
    api.startPythonBacktest.mockRejectedValue(
      new ApiError(409, "python_strategy_version_conflict", "버전 변경"),
    );
    act(() => result.current.selectStrategy(STRATEGY));
    act(() => result.current.startRun(backtestDraft()));
    await waitFor(() => expect(result.current.start.isError).toBe(true));
    await waitFor(() => expect(api.listPythonStrategies).toHaveBeenCalledTimes(2));
    expect(result.current.strategy?.version_id).toBe(STRATEGY.version_id);
  });
});
