"use client";

// "토큰 부착 mutationFn + onSuccess 에서 invalidate/remove + 콜백 위임" 표준 뮤테이션 래퍼.
// feature hooks 에 반복되던 V2(invalidate)/V3(delete 계 remove 포함) 패턴 전용 —
// setQueryData/sessionStorage 등 부수효과가 있는 뮤테이션(V4)은 흡수하지 않는다(leaky 방지).

import {
  useMutation,
  useQueryClient,
  type MutationKey,
  type QueryKey,
  type UseMutationResult,
} from "@tanstack/react-query";

import { useAuthCtx } from "./use-auth-ctx";

export interface MutationCallbacks<TData, TError = Error> {
  onSuccess?: (data: TData) => void;
  onError?: (error: TError) => void;
}

export interface InvalidatingMutationOptions<TData, TVars> {
  /** React Query mutation 식별 키. */
  mutationKey?: MutationKey;
  /** Clerk 토큰을 두 번째 인자로 받는 API 호출 — `(vars, token) => api(...)`. */
  mutationFn: (vars: TVars, token: string | null) => Promise<TData>;
  /** 성공 시 invalidate 할 queryKey 목록 — uid/응답/변수로 도출. */
  invalidateKeys: (uid: string, data: TData, vars: TVars) => readonly QueryKey[];
  /** 성공 시 캐시에서 제거할 queryKey 목록 (delete 계 뮤테이션용). invalidate 보다 먼저 실행. */
  removeKeys?: (uid: string, data: TData, vars: TVars) => readonly QueryKey[];
}

export function useInvalidatingMutation<TData, TVars>(
  options: InvalidatingMutationOptions<TData, TVars>,
  callbacks: MutationCallbacks<TData> = {},
): UseMutationResult<TData, Error, TVars> {
  const { uid, getToken } = useAuthCtx();
  const qc = useQueryClient();
  return useMutation({
    mutationKey: options.mutationKey,
    mutationFn: async (vars: TVars) => {
      const token = await getToken();
      return options.mutationFn(vars, token);
    },
    onSuccess: (data, vars) => {
      for (const key of options.removeKeys?.(uid, data, vars) ?? []) {
        qc.removeQueries({ queryKey: key });
      }
      for (const key of options.invalidateKeys(uid, data, vars)) {
        void qc.invalidateQueries({ queryKey: key });
      }
      callbacks.onSuccess?.(data);
    },
    onError: (error) => callbacks.onError?.(error),
  });
}
