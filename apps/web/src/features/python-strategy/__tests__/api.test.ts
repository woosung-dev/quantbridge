import { afterEach, describe, expect, it, vi } from "vitest";
const apiFetch = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api-client", () => ({ apiFetch }));
import {
  cancelPythonRun,
  getPythonCapabilities,
  savePythonStrategy,
  startPythonBacktest,
} from "../api";
import { makeRun, STRATEGY } from "./fixtures";

afterEach(() => apiFetch.mockReset());
describe("Python API 계약", () => {
  it("생성은 POST, 새 버전 저장은 PUT으로 인증 토큰과 보낸다", async () => {
    apiFetch.mockResolvedValue(STRATEGY);
    const body = {
      name: STRATEGY.name,
      source: STRATEGY.source,
      params: STRATEGY.params,
      warmup_bars: 100,
    };
    await savePythonStrategy(null, body, "token");
    await savePythonStrategy(STRATEGY.id, body, "token");
    expect(apiFetch).toHaveBeenNthCalledWith(1, "/api/v1/python-strategies", {
      method: "POST",
      body,
      token: "token",
    });
    expect(apiFetch).toHaveBeenNthCalledWith(2, `/api/v1/python-strategies/${STRATEGY.id}`, {
      method: "PUT",
      body,
      token: "token",
    });
  });
  it("실행과 취소는 해당 전략·실행 경로를 사용한다", async () => {
    const run = makeRun();
    apiFetch.mockResolvedValue(run);
    const body = { ...run.request, expected_version_id: STRATEGY.version_id };
    await startPythonBacktest(STRATEGY.id, body, "token");
    await cancelPythonRun(run.id, "token");
    expect(apiFetch).toHaveBeenNthCalledWith(
      1,
      `/api/v1/python-strategies/${STRATEGY.id}/backtests`,
      { method: "POST", body, token: "token" },
    );
    expect(apiFetch).toHaveBeenNthCalledWith(
      2,
      `/api/v1/python-strategies/backtests/${run.id}/cancel`,
      { method: "POST", token: "token" },
    );
  });
  it("실행 가능 여부와 실제 응답 스키마 오류를 구분한다", async () => {
    apiFetch.mockResolvedValueOnce({ available: false, reason: "격리 실행기 미설정" });
    await expect(getPythonCapabilities("token")).resolves.toMatchObject({ available: false });
    apiFetch.mockResolvedValueOnce({ available: "yes" });
    await expect(getPythonCapabilities("token")).rejects.toThrow();
  });
});
