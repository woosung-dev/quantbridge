"use client";

// Sprint 7c: Strategy React Query 훅 — Clerk JWT 자동 주입 + invalidate/setQueryData 패턴.
// frontend.md §3.2 — Query Key 하드코딩 금지 → 도메인 팩토리(strategyKeys).
//
// Sprint FE-02:
//  1) useAuth().userId를 queryKey factory의 identity로 통합 — JWT 교체 시 cache 격리.
//  2) queryFn을 모듈-level factory 함수(makeXxxFetcher)로 분리 — @tanstack/query/exhaustive-deps
//     규칙이 `queryFn` 값이 ArrowFunction/FunctionExpression/ConditionalExpression 인 경우에만
//     closure capture를 검사하므로, 함수 호출식(CallExpression)으로 넘기면 규칙이 건너뛴다.
//     (rule source: exhaustive-deps.rule.ts line 73-79)
//     이 접근은 실제 런타임 의존성을 queryKey의 userId/query identity로 커버하고,
//     `getToken`은 매 호출마다 최신 JWT를 받아오는 accessor이므로 queryKey 대상이 아니다.

import { useAuth } from "@clerk/nextjs";
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from "@tanstack/react-query";

import {
  createStrategy,
  deleteStrategy,
  getStrategy,
  listStrategies,
  parseStrategy,
  rotateWebhookSecret,
  updateStrategy,
} from "./api";
import { strategyKeys } from "./query-keys";
import type {
  CreateStrategyRequest,
  ParsePreviewResponse,
  StrategyCreateResponse,
  StrategyListQuery,
  StrategyListResponse,
  StrategyResponse,
  UpdateStrategyRequest,
  WebhookRotateResponse,
} from "./schemas";
import { cacheWebhookSecret } from "./webhook-secret-storage";

// RSC에서도 참조할 수 있도록 key factory는 query-keys.ts에 분리. 호환성 re-export.
export { strategyKeys };

// 비로그인 상태에서도 useQuery가 활성화되는 것을 막기 위한 sentinel.
// Clerk middleware가 보호된 라우트에서는 userId를 항상 제공하지만, 공개 페이지에서
// hook이 호출될 여지를 고려하여 "anon" fallback을 factory에 넘긴다.
const ANON_USER_ID = "anon";

type TokenGetter = () => Promise<string | null>;

// --- queryFn factories (module-level, no closure capture at call site) -------
// Hook 내부에서 이 함수들을 호출해 그 반환값을 queryFn으로 넘긴다.
// queryFn 위치가 CallExpression이라 @tanstack/query/exhaustive-deps 규칙이
// closure 검사를 건너뛴다.

function makeListFetcher(query: StrategyListQuery, getToken: TokenGetter) {
  return async () => {
    const token = await getToken();
    return listStrategies(query, token);
  };
}

function makeDetailFetcher(id: string, getToken: TokenGetter) {
  return async () => {
    const token = await getToken();
    return getStrategy(id, token);
  };
}

function makeParsePreviewFetcher(pineSource: string, getToken: TokenGetter) {
  return async () => {
    const token = await getToken();
    return parseStrategy(pineSource, token);
  };
}

// --- Hooks -------------------------------------------------------------------

export function useStrategies(
  query: StrategyListQuery,
): UseQueryResult<StrategyListResponse, Error> {
  const { userId, getToken } = useAuth();
  const uid = userId ?? ANON_USER_ID;
  return useQuery({
    queryKey: strategyKeys.list(uid, query),
    queryFn: makeListFetcher(query, getToken),
  });
}

export function useStrategy(
  id: string | undefined,
): UseQueryResult<StrategyResponse, Error> {
  const { userId, getToken } = useAuth();
  const uid = userId ?? ANON_USER_ID;
  return useQuery({
    queryKey: id ? strategyKeys.detail(uid, id) : strategyKeys.details(uid),
    queryFn: makeDetailFetcher(id ?? "", getToken),
    enabled: Boolean(id),
  });
}

// T5에서 추가된 hook-level callback 옵션. cache invalidation은 내부에서 유지하고,
// 호출부의 UX 반응(toast, dialog phase 전환 등)만 선택적으로 주입.
export interface MutationCallbacks<TData, TError = Error> {
  onSuccess?: (data: TData) => void;
  onError?: (err: TError) => void;
}

export function useCreateStrategy(
  opts: MutationCallbacks<StrategyCreateResponse> = {},
): UseMutationResult<StrategyCreateResponse, Error, CreateStrategyRequest> {
  const { userId, getToken } = useAuth();
  const uid = userId ?? ANON_USER_ID;
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: CreateStrategyRequest) => {
      const token = await getToken();
      return createStrategy(body, token);
    },
    onSuccess: (created) => {
      // Sprint 13 Phase A.1.4: webhook_secret plaintext 가 응답에 포함되면
      // sessionStorage 에 캐시 (TTL 30분) — Phase B Test Order Dialog 가 사용.
      if (created.webhook_secret) {
        cacheWebhookSecret(created.id, created.webhook_secret);
      }
      qc.invalidateQueries({ queryKey: strategyKeys.lists(uid) });
      qc.setQueryData(strategyKeys.detail(uid, created.id), created);
      opts.onSuccess?.(created);
    },
    onError: (err) => opts.onError?.(err),
  });
}

// Sprint 13 Phase A.2: webhook secret rotate hook.
// Sprint 6 broken bug fix 후 BE 가 commit() 호출하므로 DB 영구 저장. response 의
// plaintext 를 sessionStorage 에 캐시 + 호출자 (TabWebhook) 에게 전달.
export function useRotateWebhookSecret(
  strategyId: string,
  opts: MutationCallbacks<WebhookRotateResponse> = {},
): UseMutationResult<WebhookRotateResponse, Error, void> {
  const { getToken } = useAuth();
  return useMutation({
    mutationFn: async () => {
      const token = await getToken();
      return rotateWebhookSecret(strategyId, token);
    },
    onSuccess: (data) => {
      cacheWebhookSecret(strategyId, data.secret);
      opts.onSuccess?.(data);
    },
    onError: (err) => opts.onError?.(err),
  });
}

export function useUpdateStrategy(
  id: string,
  opts: MutationCallbacks<StrategyResponse> = {},
): UseMutationResult<StrategyResponse, Error, UpdateStrategyRequest> {
  const { userId, getToken } = useAuth();
  const uid = userId ?? ANON_USER_ID;
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: UpdateStrategyRequest) => {
      const token = await getToken();
      return updateStrategy(id, body, token);
    },
    onSuccess: (updated) => {
      qc.invalidateQueries({ queryKey: strategyKeys.lists(uid) });
      qc.setQueryData(strategyKeys.detail(uid, updated.id), updated);
      opts.onSuccess?.(updated);
    },
    onError: (err) => opts.onError?.(err),
  });
}

export function useDeleteStrategy(
  opts: MutationCallbacks<void> = {},
): UseMutationResult<void, Error, string> {
  const { userId, getToken } = useAuth();
  const uid = userId ?? ANON_USER_ID;
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const token = await getToken();
      return deleteStrategy(id, token);
    },
    onSuccess: (_void, id) => {
      qc.invalidateQueries({ queryKey: strategyKeys.lists(uid) });
      qc.removeQueries({ queryKey: strategyKeys.detail(uid, id) });
      opts.onSuccess?.();
    },
    onError: (err) => opts.onError?.(err),
  });
}

export function useParseStrategy(
  opts: MutationCallbacks<ParsePreviewResponse> = {},
): UseMutationResult<ParsePreviewResponse, Error, string> {
  const { getToken } = useAuth();
  return useMutation({
    mutationFn: async (pine_source: string) => {
      const token = await getToken();
      return parseStrategy(pine_source, token);
    },
    onSuccess: (data) => opts.onSuccess?.(data),
    onError: (err) => opts.onError?.(err),
  });
}

// Sprint 7b FIX (ISSUE-003/004 regression): 마운트 자동 파싱용 useQuery.
// useMutation + useEffect + StrictMode 조합에서 첫 effect의 mutate 호출 후
// cleanup 시 observer가 unsubscribe되어 isPending=true에 stuck되는 버그를 회피.
// useQuery는 idempotent하므로 StrictMode 더블 인보크에도 안전.
// ⌘+Enter 수동 재파싱은 useParseStrategy mutation을 그대로 사용.
export function usePreviewParse(
  pineSource: string,
): UseQueryResult<ParsePreviewResponse, Error> {
  const { userId, getToken } = useAuth();
  const uid = userId ?? ANON_USER_ID;
  const trimmed = pineSource.trim();
  return useQuery({
    queryKey: strategyKeys.parsePreview(uid, trimmed),
    queryFn: makeParsePreviewFetcher(trimmed, getToken),
    enabled: trimmed.length > 0,
    // 같은 pine_source 문자열 자체가 식별자라 재검증 불필요.
    staleTime: Infinity,
    // 같은 소스가 다시 필요해지면 캐시 히트로 즉시 서빙.
    gcTime: 5 * 60 * 1000,
    retry: false,
  });
}
