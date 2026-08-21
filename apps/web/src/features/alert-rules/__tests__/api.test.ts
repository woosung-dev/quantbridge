// Alert rule API가 세션 범위 목록 endpoint와 응답 계약을 지키는지 확인한다.
// 네트워크 구현은 apiFetch 하나에 있으므로 이 경계에서만 mock 한다.

import { afterEach, describe, expect, it, vi } from "vitest";

const apiFetchMock = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api-client", () => ({ apiFetch: apiFetchMock }));

import { listAlertRules } from "../api";

const TOKEN = "access-token";
const SESSION_ID = "55555555-5555-4555-8555-555555555555";

afterEach(() => {
  apiFetchMock.mockReset();
});

describe("alert rules api", () => {
  it("listAlertRules는 세션별 목록 endpoint로 요청하고 목록 응답을 검증한다", async () => {
    apiFetchMock.mockResolvedValueOnce({ items: [], total: 0 });

    await expect(listAlertRules(SESSION_ID, TOKEN)).resolves.toEqual({ items: [], total: 0 });

    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/live-sessions/${SESSION_ID}/alert-rules`, {
      method: "GET",
      token: TOKEN,
    });
  });
});
