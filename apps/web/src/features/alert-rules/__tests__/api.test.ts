// Alert rule API가 세션 범위 목록 endpoint와 응답 계약을 지키는지 확인한다.
// 네트워크 구현은 apiFetch 하나에 있으므로 이 경계에서만 mock 한다.

import { afterEach, describe, expect, it, vi } from "vitest";

const apiFetchMock = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiFetchMock };
});

import { ApiError } from "@/lib/api-client";
import { createAlertRule, deactivateAlertRule, listAlertRules } from "../api";

const TOKEN = "access-token";
const SESSION_ID = "55555555-5555-4555-8555-555555555555";
const RULE_ID = "66666666-6666-4666-8666-666666666666";

function alertRuleResponse() {
  return {
    id: RULE_ID,
    session_id: SESSION_ID,
    rule_type: "loss_limit" as const,
    threshold_percent: "5.5",
    channel: "slack" as const,
    is_active: true,
    created_at: "2026-08-22T00:00:00Z",
    updated_at: "2026-08-22T00:00:00Z",
  };
}

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
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("createAlertRule은 세션별 create endpoint로 요청을 보내고 검증된 규칙을 반환한다", async () => {
    const request = {
      rule_type: "loss_limit" as const,
      threshold_percent: "5.5",
      channel: "slack" as const,
    };
    const response = alertRuleResponse();
    apiFetchMock.mockResolvedValueOnce(response);

    await expect(createAlertRule(SESSION_ID, request, TOKEN)).resolves.toEqual(response);

    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/live-sessions/${SESSION_ID}/alert-rules`, {
      method: "POST",
      token: TOKEN,
      body: request,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("deactivateAlertRule은 세션 범위 rule delete endpoint를 한 번 호출한다", async () => {
    apiFetchMock.mockResolvedValueOnce(undefined);

    await expect(deactivateAlertRule(SESSION_ID, RULE_ID, TOKEN)).resolves.toBeUndefined();

    expect(apiFetchMock).toHaveBeenCalledWith(
      `/api/v1/live-sessions/${SESSION_ID}/alert-rules/${RULE_ID}`,
      {
        method: "DELETE",
        token: TOKEN,
      },
    );
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("createAlertRule은 ApiError의 status와 code를 감싸지 않고 그대로 전파한다", async () => {
    const request = {
      rule_type: "loss_limit" as const,
      threshold_percent: "5.5",
      channel: "slack" as const,
    };
    const error = new ApiError(409, "alert_rule_conflict", "rule already exists");
    apiFetchMock.mockRejectedValueOnce(error);

    await expect(createAlertRule(SESSION_ID, request, TOKEN)).rejects.toBe(error);

    expect(error).toMatchObject({ status: 409, code: "alert_rule_conflict" });
    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/live-sessions/${SESSION_ID}/alert-rules`, {
      method: "POST",
      token: TOKEN,
      body: request,
    });
  });

  it("listAlertRules는 계약을 어긴 목록 응답을 조용히 반환하지 않는다", async () => {
    apiFetchMock.mockResolvedValueOnce({ items: [alertRuleResponse()], total: "1" });

    await expect(listAlertRules(SESSION_ID, TOKEN)).rejects.toThrow();

    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("deactivateAlertRule은 204가 아닌 ApiError도 그대로 전파한다", async () => {
    const error = new ApiError(404, "alert_rule_not_found", "rule not found");
    apiFetchMock.mockRejectedValueOnce(error);

    await expect(deactivateAlertRule(SESSION_ID, RULE_ID, TOKEN)).rejects.toBe(error);

    expect(error).toMatchObject({ status: 404, code: "alert_rule_not_found" });
  });
});
