// Waitlist REST 래퍼의 public 제출과 admin 목록 경계를 고정한다.
import { afterEach, describe, expect, it, vi } from "vitest";

const apiFetchMock = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api-client", () => ({ apiFetch: apiFetchMock }));

import { listAdminWaitlist, submitWaitlist } from "../api";

const APPLICATION = {
  email: "alice@example.com",
  tv_subscription: "pro_plus",
  exchange_capital: "1k_to_10k",
  pine_experience: "intermediate",
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
  });
});
