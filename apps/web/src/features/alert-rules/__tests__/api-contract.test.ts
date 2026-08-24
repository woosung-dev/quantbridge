// Alert rule REST 래퍼의 현재 경로·요청·응답 계약을 고정한다.
import { afterEach, describe, expect, it, vi } from "vitest";

const apiFetchMock = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api-client", () => ({ apiFetch: apiFetchMock }));

import { createAlertRule, deactivateAlertRule, listAlertRules } from "../api";

const SESSION_ID = "00000000-0000-4000-a000-000000000001";
const RULE_ID = "00000000-0000-4000-a000-000000000002";
const ALERT_RULE = {
  id: RULE_ID,
  session_id: SESSION_ID,
  rule_type: "loss_limit" as const,
  threshold_percent: "5.5",
  channel: "slack" as const,
  is_active: true,
  created_at: "2026-08-22T00:00:00Z",
  updated_at: "2026-08-22T00:00:00Z",
};
const ALERT_RULE_LIST = { items: [ALERT_RULE], total: 1 };

afterEach(() => {
  apiFetchMock.mockReset();
});

describe("alert rules API contract", () => {
  it("현재 구현: 세션별 목록 GET은 경로·인증을 전달하고 AlertRule 목록 응답을 파싱한다", async () => {
    apiFetchMock.mockResolvedValueOnce(ALERT_RULE_LIST);

    await expect(listAlertRules(SESSION_ID, "jwt")).resolves.toEqual(ALERT_RULE_LIST);

    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/live-sessions/${SESSION_ID}/alert-rules`, {
      method: "GET",
      token: "jwt",
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("현재 구현: 세션별 규칙 생성은 POST body를 보존하고 AlertRule 응답을 파싱한다", async () => {
    const request = {
      rule_type: "loss_limit" as const,
      threshold_percent: "5.5",
      channel: "slack" as const,
    };
    apiFetchMock.mockResolvedValueOnce(ALERT_RULE);

    await expect(createAlertRule(SESSION_ID, request, "jwt")).resolves.toEqual(ALERT_RULE);

    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/live-sessions/${SESSION_ID}/alert-rules`, {
      method: "POST",
      token: "jwt",
      body: request,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("현재 구현: 세션과 규칙 식별자를 DELETE 경로에 넣고 204 void 응답을 반환한다", async () => {
    apiFetchMock.mockResolvedValueOnce(undefined);

    await expect(deactivateAlertRule(SESSION_ID, RULE_ID, "jwt")).resolves.toBeUndefined();

    expect(apiFetchMock).toHaveBeenCalledWith(
      `/api/v1/live-sessions/${SESSION_ID}/alert-rules/${RULE_ID}`,
      { method: "DELETE", token: "jwt" },
    );
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });
});
