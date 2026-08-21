// Waitlist REST 래퍼의 정상 경로·응답 스키마 계약을 고정한다.
import { afterEach, describe, expect, it, vi } from "vitest";

const apiFetchMock = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api-client", () => ({ apiFetch: apiFetchMock }));

import { approveWaitlistApplication, listAdminWaitlist, submitWaitlist } from "../api";

const APPLICATION = {
  email: "alice@example.com",
  tv_subscription: "pro_plus" as const,
  exchange_capital: "1k_to_10k" as const,
  pine_experience: "intermediate" as const,
  pain_point: "백테스트와 데모 거래의 결과를 함께 확인하고 싶습니다.",
};

afterEach(() => {
  apiFetchMock.mockReset();
});

describe("waitlist API contract", () => {
  it("공개 신청은 token 없이 검증된 payload를 POST하고 접수 응답을 파싱한다", async () => {
    apiFetchMock.mockResolvedValueOnce({
      id: "00000000-0000-4000-a000-000000000021",
      status: "pending",
    });

    await expect(submitWaitlist(APPLICATION)).resolves.toEqual({
      id: "00000000-0000-4000-a000-000000000021",
      status: "pending",
    });

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/waitlist", {
      method: "POST",
      token: null,
      body: APPLICATION,
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("관리자 목록은 상태와 기본 페이지네이션을 GET 파라미터로 전달한다", async () => {
    apiFetchMock.mockResolvedValueOnce({ items: [], total: 0 });

    await expect(listAdminWaitlist({ status: "pending" }, "jwt")).resolves.toEqual({
      items: [],
      total: 0,
    });

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/admin/waitlist", {
      method: "GET",
      token: "jwt",
      params: { status: "pending", limit: 50, offset: 0 },
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });

  it("관리자 승인 요청은 application 식별자 POST와 인증을 전달한다", async () => {
    const applicationId = "00000000-0000-4000-a000-000000000022";
    const approved = {
      id: applicationId,
      status: "invited",
      email: APPLICATION.email,
      invite_sent_at: "2026-08-22T00:00:00+00:00",
    };
    apiFetchMock.mockResolvedValueOnce(approved);

    await expect(approveWaitlistApplication(applicationId, "jwt")).resolves.toEqual(approved);

    expect(apiFetchMock).toHaveBeenCalledWith(`/api/v1/admin/waitlist/${applicationId}/approve`, {
      method: "POST",
      token: "jwt",
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
  });
});
