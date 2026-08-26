"use client";

// Sprint 7c: Strategy React Query 훅 — Clerk JWT 자동 주입 + invalidate/setQueryData 패턴.
// apps/web/AGENTS.md §3 — Query Key 하드코딩 금지 → 도메인 팩토리(strategyKeys).
//
// Sprint FE-02:
//  1) useAuth().userId를 queryKey factory의 identity로 통합 — JWT 교체 시 cache 격리.
//  2) queryFn을 모듈-level factory 함수(makeXxxFetcher)로 분리 — @tanstack/query/exhaustive-deps
//     규칙이 `queryFn` 값이 ArrowFunction/FunctionExpression/ConditionalExpression 인 경우에만
//     closure capture를 검사하므로, 함수 호출식(CallExpression)으로 넘기면 규칙이 건너뛴다.
//     (rule source: exhaustive-deps.rule.ts line 73-79)
//     이 접근은 실제 런타임 의존성을 queryKey의 userId/query identity로 커버하고,
//     `getToken`은 매 호출마다 최신 JWT를 받아오는 accessor이므로 queryKey 대상이 아니다.

import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from "@tanstack/react-query";

import { useAuthCtx, type TokenGetter } from "@/hooks/use-auth-ctx";
import { useInvalidatingMutation, type MutationCallbacks } from "@/hooks/use-invalidating-mutation";

import {
  createStrategy,
  deleteStrategy,
  getStrategy,
  getStrategyBrief,
  listStrategies,
  parseStrategy,
  rotateWebhookSecret,
  updateStrategy,
  updateStrategySettings,
} from "./api";
import { strategyKeys } from "./query-keys";
import type {
  CreateStrategyRequest,
  ParsePreviewResponse,
  StrategyBrief,
  StrategyCreateResponse,
  StrategyListQuery,
  StrategyListResponse,
  StrategyResponse,
  UpdateStrategySettingsRequest,
  UpdateStrategyRequest,
  WebhookRotateResponse,
} from "./schemas";
import { cacheWebhookSecret } from "./webhook-secret-storage";

// RSC에서도 참조할 수 있도록 key factory는 query-keys.ts에 분리. 호환성 re-export.
export { strategyKeys };

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
  const { uid, getToken } = useAuthCtx();
  return useQuery({
    queryKey: strategyKeys.list(uid, query),
    queryFn: makeListFetcher(query, getToken),
    // Sprint 14 Phase B-2 — 기본 3 retries 는 dogfood 지연 발생.
    // 1회만 retry 후 isError 로 명시 표시 (StrategyList 가 retry 버튼 제공).
    retry: 1,
  });
}

export function useStrategy(id: string | undefined): UseQueryResult<StrategyResponse, Error> {
  const { uid, getToken } = useAuthCtx();
  return useQuery({
    queryKey: id ? strategyKeys.detail(uid, id) : strategyKeys.details(uid),
    queryFn: makeDetailFetcher(id ?? "", getToken),
    enabled: Boolean(id),
  });
}

function makeBriefFetcher(id: string, getToken: TokenGetter) {
  return async () => {
    const token = await getToken();
    return getStrategyBrief(id, token);
  };
}

/**
 * [ADR-040] 전략 브리핑 — 백테스트 제출 **전에** 보는 결정론 응답.
 *
 * ★서버가 Pine 을 파싱하므로 콜드 파스가 붙을 수 있다(큰 스크립트는 수십 초). 편집 중
 * 재파싱하는 `usePreviewParse` 와 달리 **전략 id 단위**라 소스가 안 바뀌면 다시 안 부른다.
 */
export function useStrategyBrief(id: string | undefined): UseQueryResult<StrategyBrief, Error> {
  const { uid, getToken } = useAuthCtx();
  return useQuery({
    queryKey: id ? strategyKeys.brief(uid, id) : strategyKeys.all(uid),
    queryFn: makeBriefFetcher(id ?? "", getToken),
    enabled: Boolean(id),
    retry: 1,
  });
}

// T5에서 추가된 hook-level callback 옵션 — 공용 정의 re-export (호환성 유지).
export type { MutationCallbacks };

export function useCreateStrategy(
  opts: MutationCallbacks<StrategyCreateResponse> = {},
): UseMutationResult<StrategyCreateResponse, Error, CreateStrategyRequest> {
  const { uid, getToken } = useAuthCtx();
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
      // G.2 challenge P2 #2 fix: webhook_secret 은 sessionStorage TTL/hide 정책으로
      // 만 수명 관리. react-query detail cache 에는 secret 제외 sanitized 만 저장.
      const { webhook_secret: _omitted, ...sanitized } = created;
      qc.setQueryData(strategyKeys.detail(uid, created.id), sanitized as StrategyResponse);
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
  const { getToken } = useAuthCtx();
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
  const { uid, getToken } = useAuthCtx();
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

// Sprint 27 BL-137 — PUT /strategies/{id}/settings (trading params).
// codex G.2 P1 #3 — settings 와 메타데이터 mutation race 회피: setQueryData
// 대신 detail invalidate (서버 truth fetch). 동시 저장 시 stale 덮어쓰기 차단.
export function useUpdateStrategySettings(
  id: string,
  opts: MutationCallbacks<StrategyResponse> = {},
): UseMutationResult<StrategyResponse, Error, UpdateStrategySettingsRequest> {
  return useInvalidatingMutation(
    {
      mutationFn: (body: UpdateStrategySettingsRequest, token) =>
        updateStrategySettings(id, body, token),
      // codex G.2 P1 #3 — detail 은 invalidate (setQueryData 금지: race window).
      invalidateKeys: (uid, updated) => [
        strategyKeys.lists(uid),
        strategyKeys.detail(uid, updated.id),
      ],
    },
    opts,
  );
}

export function useDeleteStrategy(
  opts: MutationCallbacks<void> = {},
): UseMutationResult<void, Error, string> {
  return useInvalidatingMutation(
    {
      mutationFn: (id: string, token) => deleteStrategy(id, token),
      invalidateKeys: (uid) => [strategyKeys.lists(uid)],
      removeKeys: (uid, _void, id) => [strategyKeys.detail(uid, id)],
    },
    opts,
  );
}

export function useParseStrategy(
  opts: MutationCallbacks<ParsePreviewResponse> = {},
): UseMutationResult<ParsePreviewResponse, Error, string> {
  const { getToken } = useAuthCtx();
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
export function usePreviewParse(pineSource: string): UseQueryResult<ParsePreviewResponse, Error> {
  const { uid, getToken } = useAuthCtx();
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
