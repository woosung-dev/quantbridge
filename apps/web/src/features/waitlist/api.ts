// Sprint 11 Phase C: Waitlist API — apiFetch + Clerk JWT + Zod 런타임 검증.
// POST /waitlist 는 public (token = null 허용). admin 은 Clerk token 필수.

import { getApiBase } from "@/lib/api-base";
import { apiFetch } from "@/lib/api-client";

import type { InviteFetchResult } from "./invite-view";

import {
  AdminApproveResponseSchema,
  AdminWaitlistListResponseSchema,
  CreateWaitlistApplicationSchema,
  InviteTokenVerifyResponseSchema,
  WaitlistApplicationAcceptedResponseSchema,
  type AdminApproveResponse,
  type AdminWaitlistListResponse,
  type CreateWaitlistApplication,
  type WaitlistApplicationAcceptedResponse,
  type WaitlistStatus,
} from "./schemas";

const WAITLIST_PATH = "/api/v1/waitlist";
const ADMIN_WAITLIST_PATH = "/api/v1/admin/waitlist";

export async function submitWaitlist(
  body: CreateWaitlistApplication,
): Promise<WaitlistApplicationAcceptedResponse> {
  const parsed = CreateWaitlistApplicationSchema.parse(body);
  const raw = await apiFetch<unknown>(WAITLIST_PATH, {
    method: "POST",
    // Public endpoint — no token. Explicit null 로 Authorization 헤더 생략.
    token: null,
    body: parsed,
  });
  return WaitlistApplicationAcceptedResponseSchema.parse(raw);
}

export async function listAdminWaitlist(
  query: { status?: WaitlistStatus; limit?: number; offset?: number },
  token: string | null,
): Promise<AdminWaitlistListResponse> {
  const raw = await apiFetch<unknown>(ADMIN_WAITLIST_PATH, {
    method: "GET",
    token,
    params: {
      status: query.status,
      limit: query.limit ?? 50,
      offset: query.offset ?? 0,
    },
  });
  return AdminWaitlistListResponseSchema.parse(raw);
}

export async function approveWaitlistApplication(
  id: string,
  token: string | null,
): Promise<AdminApproveResponse> {
  const raw = await apiFetch<unknown>(`${ADMIN_WAITLIST_PATH}/${id}/approve`, {
    method: "POST",
    token,
  });
  return AdminApproveResponseSchema.parse(raw);
}

// [BL-072] 초대 토큰 조회 — **공개**(로그인 이전 단계)이고 **SSR 에서** 부른다.
//
// ★`apiFetch` 를 안 쓴다: 그것은 오류를 throw 하는데, 이 화면은 400/404 를 「사용자에게
//   보여줄 갈래」로 다뤄야 하지 예외로 다루면 안 된다(서버 컴포넌트에서 throw 하면
//   `error.tsx` 로 떨어져 「만료된 링크」가 「오류 화면」이 된다).
// ★2026-08-16 codex 적대 리뷰 P3 — 초판은 이 fetch 를 페이지 안에 뒀다(`AGENTS.md` §3 위반).
export async function verifyInviteToken(token: string): Promise<InviteFetchResult> {
  try {
    const res = await fetch(`${getApiBase()}/api/v1/waitlist/invite/${encodeURIComponent(token)}`, {
      cache: "no-store",
    });
    // BE 는 서명 불일치와 만료를 둘 다 400 으로 낸다
    // (`waitlist/exceptions.py` — InviteTokenInvalidError / InviteTokenExpiredError).
    if (res.status === 400) return { kind: "invalid" };
    if (res.status === 404) return { kind: "not-found" };
    if (!res.ok) return { kind: "error" };
    const parsed = InviteTokenVerifyResponseSchema.parse(await res.json());
    return { kind: "ok", email: parsed.email, status: parsed.status };
  } catch {
    return { kind: "error" };
  }
}
