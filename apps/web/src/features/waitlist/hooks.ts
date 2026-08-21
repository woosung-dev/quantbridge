"use client";

// Sprint 11 Phase C: Waitlist React Query 훅.
// - useCreateWaitlist: public 엔드포인트 (token null)
// - useAdminWaitlistList / useApproveWaitlist: Clerk JWT 필수
//
// FE-02 패턴 (query key factory identity = userId) 재사용.

import {
  useMutation,
  useQuery,
  type UseMutationResult,
  type UseQueryResult,
} from "@tanstack/react-query";

import { useAuthCtx, type TokenGetter } from "@/hooks/use-auth-ctx";
import { useInvalidatingMutation, type MutationCallbacks } from "@/hooks/use-invalidating-mutation";

import { approveWaitlistApplication, listAdminWaitlist, submitWaitlist } from "./api";
import { waitlistKeys } from "./query-keys";
import type {
  AdminApproveResponse,
  AdminWaitlistListResponse,
  CreateWaitlistApplication,
  WaitlistApplicationAcceptedResponse,
  WaitlistStatus,
} from "./schemas";

export { waitlistKeys };

function makeAdminListFetcher(
  query: { status?: WaitlistStatus; limit?: number; offset?: number },
  getToken: TokenGetter,
) {
  return async () => {
    const token = await getToken();
    return listAdminWaitlist(query, token);
  };
}

export type { MutationCallbacks };

export function useCreateWaitlist(
  opts: MutationCallbacks<WaitlistApplicationAcceptedResponse> = {},
): UseMutationResult<WaitlistApplicationAcceptedResponse, Error, CreateWaitlistApplication> {
  return useMutation({
    mutationFn: (body: CreateWaitlistApplication) => submitWaitlist(body),
    onSuccess: (data) => opts.onSuccess?.(data),
    onError: (err) => opts.onError?.(err),
  });
}

export function useAdminWaitlistList(query: {
  status?: WaitlistStatus;
  limit?: number;
  offset?: number;
}): UseQueryResult<AdminWaitlistListResponse, Error> {
  const { uid, getToken } = useAuthCtx();
  return useQuery({
    queryKey: waitlistKeys.adminList(uid, query),
    queryFn: makeAdminListFetcher(query, getToken),
  });
}

export function useApproveWaitlist(
  opts: MutationCallbacks<AdminApproveResponse> = {},
): UseMutationResult<AdminApproveResponse, Error, string> {
  return useInvalidatingMutation(
    {
      mutationFn: (id: string, token) => approveWaitlistApplication(id, token),
      invalidateKeys: (uid) => [waitlistKeys.adminLists(uid)],
    },
    opts,
  );
}
