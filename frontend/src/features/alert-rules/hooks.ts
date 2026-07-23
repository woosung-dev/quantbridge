"use client";

// 세션 알림 규칙의 조회와 변경 후 무효화를 제공한다.
import {
  useQuery,
  type UseMutationResult,
  type UseQueryResult,
} from "@tanstack/react-query";

import { useAuthCtx, type TokenGetter } from "@/hooks/use-auth-ctx";
import { useInvalidatingMutation } from "@/hooks/use-invalidating-mutation";

import { createAlertRule, deactivateAlertRule, listAlertRules } from "./api";
import { alertRuleKeys } from "./query-keys";
import type { AlertRule, AlertRuleCreateRequest } from "./schemas";

function makeListFetcher(sessionId: string, getToken: TokenGetter) {
  return async () => listAlertRules(sessionId, await getToken());
}

export function useAlertRules(
  sessionId: string | null,
): UseQueryResult<{ items: AlertRule[]; total: number }, Error> {
  const { uid, getToken } = useAuthCtx();
  return useQuery({
    queryKey: alertRuleKeys.list(uid, sessionId ?? ""),
    queryFn: makeListFetcher(sessionId ?? "", getToken),
    enabled: Boolean(sessionId),
  });
}

export function useCreateAlertRule(
  sessionId: string,
): UseMutationResult<AlertRule, Error, AlertRuleCreateRequest> {
  return useInvalidatingMutation({
    mutationFn: (request, token) => createAlertRule(sessionId, request, token),
    invalidateKeys: (uid) => [alertRuleKeys.list(uid, sessionId)],
  });
}

export function useDeactivateAlertRule(
  sessionId: string,
): UseMutationResult<void, Error, string> {
  return useInvalidatingMutation({
    mutationFn: (ruleId, token) => deactivateAlertRule(sessionId, ruleId, token),
    invalidateKeys: (uid) => [alertRuleKeys.list(uid, sessionId)],
  });
}
