"use client";

// Sprint 11 Phase C: Waitlist React Query 훅.
// - useCreateWaitlist: public 엔드포인트 (token null)
// - useAdminWaitlistList / useApproveWaitlist: Clerk JWT 필수
//
// FE-02 패턴 (query key factory identity = userId) 재사용.

import { useAuth } from "@clerk/nextjs";
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from "@tanstack/react-query";

import {
  approveWaitlistApplication,
  listAdminWaitlist,
  submitWaitlist,
} from "./api";
import { waitlistKeys } from "./query-keys";
import type {
  AdminApproveResponse,
  AdminWaitlistListResponse,
  CreateWaitlistApplication,
  WaitlistApplicationAcceptedResponse,
  WaitlistStatus,
} from "./schemas";

export { waitlistKeys };

const ANON_USER_ID = "anon";

type TokenGetter = () => Promise<string | null>;

function makeAdminListFetcher(
  query: { status?: WaitlistStatus; limit?: number; offset?: number },
  getToken: TokenGetter,
) {
  return async () => {
    const token = await getToken();
    return listAdminWaitlist(query, token);
  };
}

export interface MutationCallbacks<TData, TError = Error> {
  onSuccess?: (data: TData) => void;
  onError?: (err: TError) => void;
}

export function useCreateWaitlist(
  opts: MutationCallbacks<WaitlistApplicationAcceptedResponse> = {},
): UseMutationResult<
  WaitlistApplicationAcceptedResponse,
  Error,
  CreateWaitlistApplication
> {
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
  const { userId, getToken } = useAuth();
  const uid = userId ?? ANON_USER_ID;
  return useQuery({
    queryKey: waitlistKeys.adminList(uid, query),
    queryFn: makeAdminListFetcher(query, getToken),
  });
}

export function useApproveWaitlist(
  opts: MutationCallbacks<AdminApproveResponse> = {},
): UseMutationResult<AdminApproveResponse, Error, string> {
  const { userId, getToken } = useAuth();
  const uid = userId ?? ANON_USER_ID;
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const token = await getToken();
      return approveWaitlistApplication(id, token);
    },
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: waitlistKeys.adminLists(uid) });
      opts.onSuccess?.(data);
    },
    onError: (err) => opts.onError?.(err),
  });
}
