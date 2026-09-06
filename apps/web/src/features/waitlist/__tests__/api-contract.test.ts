// Waitlist REST 래퍼의 정상 경로·응답 스키마 계약을 고정한다.
import { afterEach, describe, expect, it, vi } from "vitest";

const apiFetchMock = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api-client", () => ({ apiFetch: apiFetchMock }));

import {
  approveWaitlistApplication,
  listAdminWaitlist,
  submitWaitlist,
  verifyInviteToken,
} from "../api";

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
  // ★위 케이스는 이미 트림된 fixture 를 넣고 **그것과 같은 객체**를 단언하므로 api.ts 가
  //   `body: parsed` 를 보내든 `body` 를 보내든 초록이다. 폼은 pain_point 를 트림하지 않으므로
  //   (waitlist-form-card.tsx 는 existing_tool 만 트림) 와이어의 정규화는 오직 `body: parsed`
  //   덕분이다 — 그 사실을 재는 곳이 여기뿐이다(원문 = refs/stash-archive/02).
  it("공개 신청은 정규화한 payload를 보낸다 — 원본이 아니라 스키마 통과본이다", async () => {
    const untrimmed = {
      ...APPLICATION,
      existing_tool: null,
      pain_point: "  백테스트와 데모 거래의 결과를 함께 확인하고 싶습니다.  ",
    };
    apiFetchMock.mockResolvedValueOnce({
      id: "00000000-0000-4000-a000-000000000021",
      status: "pending",
    });

    await expect(submitWaitlist(untrimmed)).resolves.toEqual({
      id: "00000000-0000-4000-a000-000000000021",
      status: "pending",
    });

    expect(apiFetchMock).toHaveBeenCalledTimes(1);
    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/waitlist", {
      method: "POST",
      token: null,
      body: { ...untrimmed, pain_point: APPLICATION.pain_point },
    });
  });

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

  it("선택 status가 없을 때 undefined를 넘기고 0·음수 페이지 경계를 보존한다", async () => {
    apiFetchMock.mockResolvedValueOnce({ items: [], total: 0 });

    await expect(listAdminWaitlist({ limit: 0, offset: -1 }, null)).resolves.toEqual({
      items: [],
      total: 0,
    });

    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/admin/waitlist", {
      method: "GET",
      token: null,
      params: { status: undefined, limit: 0, offset: -1 },
    });
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

  it("신청 API 오류는 status·code가 든 같은 Error 객체를 그대로 전파한다", async () => {
    const { ApiError } =
      await vi.importActual<typeof import("@/lib/api-client")>("@/lib/api-client");
    const apiError = new ApiError(422, "duplicate_email", "API 422 /api/v1/waitlist");
    apiFetchMock.mockRejectedValueOnce(apiError);

    await expect(submitWaitlist(APPLICATION)).rejects.toBe(apiError);
    expect(apiError).toMatchObject({ status: 422, code: "duplicate_email" });
  });

  it("승인 응답이 계약을 어기면 Zod parse 오류로 중단한다", async () => {
    apiFetchMock.mockResolvedValueOnce({
      id: "00000000-0000-4000-a000-000000000022",
      status: "unknown",
      email: APPLICATION.email,
      invite_sent_at: null,
    });

    await expect(
      approveWaitlistApplication("00000000-0000-4000-a000-000000000022", "jwt"),
    ).rejects.toThrow();
  });
});

describe("verifyInviteToken direct fetch boundary", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("400과 404는 화면이 처리할 invalid·not-found 결과로 변환한다", async () => {
    const fetchMock = vi
      .fn<(_: RequestInfo | URL, _init?: RequestInit) => Promise<Response>>()
      .mockResolvedValueOnce(new Response(null, { status: 400 }))
      .mockResolvedValueOnce(new Response(null, { status: 404 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(verifyInviteToken("expired")).resolves.toEqual({ kind: "invalid" });
    await expect(verifyInviteToken("missing")).resolves.toEqual({ kind: "not-found" });
  });

  it("직접 fetch는 token을 인코딩하고 undefined status query를 만들지 않는다", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ email: "alice@example.com", status: "invited" }), {
        status: 200,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(verifyInviteToken("a/b ?")).resolves.toEqual({
      kind: "ok",
      email: "alice@example.com",
      status: "invited",
    });

    const url = new URL(String(fetchMock.mock.calls[0]?.[0]));
    expect(url.pathname).toContain("/api/v1/waitlist/invite/a%2Fb%20%3F");
    expect(url.search).not.toContain("undefined");
    expect(fetchMock).toHaveBeenCalledWith(expect.any(String), { cache: "no-store" });
  });

  it("apiFetch는 undefined params를 URL query에서 제외한다", async () => {
    const { apiFetch } =
      await vi.importActual<typeof import("@/lib/api-client")>("@/lib/api-client");
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({}), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await apiFetch("/api/v1/admin/waitlist", {
      method: "GET",
      params: { status: undefined, limit: 0, offset: -1 },
    });

    const url = new URL(String(fetchMock.mock.calls[0]?.[0]));
    expect(url.searchParams.has("status")).toBe(false);
    expect(url.searchParams.get("limit")).toBe("0");
    expect(url.searchParams.get("offset")).toBe("-1");
  });

  it("예상 밖 HTTP 오류와 네트워크 오류는 원문 없는 error 결과로 축소한다", async () => {
    const fetchMock = vi
      .fn<(_: RequestInfo | URL, _init?: RequestInit) => Promise<Response>>()
      .mockResolvedValueOnce(new Response(null, { status: 503 }))
      .mockRejectedValueOnce(new Error("network unavailable"));
    vi.stubGlobal("fetch", fetchMock);

    await expect(verifyInviteToken("server-error")).resolves.toEqual({ kind: "error" });
    await expect(verifyInviteToken("network-error")).resolves.toEqual({ kind: "error" });
  });
});
