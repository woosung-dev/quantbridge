// Sprint 11 Phase C: Waitlist API — apiFetch + Clerk JWT + Zod 런타임 검증.
// POST /waitlist 는 public (token = null 허용). admin 은 Clerk token 필수.

import { apiFetch } from "@/lib/api-client";

import {
  AdminApproveResponseSchema,
  AdminWaitlistListResponseSchema,
  CreateWaitlistApplicationSchema,
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
