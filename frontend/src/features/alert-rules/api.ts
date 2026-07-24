// 세션 알림 규칙 API 호출을 한곳에 모은다.
import { apiFetch } from "@/lib/api-client";

import {
  AlertRuleListResponseSchema,
  AlertRuleSchema,
  type AlertRule,
  type AlertRuleCreateRequest,
} from "./schemas";

function alertRulesPath(sessionId: string): string {
  return `/api/v1/live-sessions/${sessionId}/alert-rules`;
}

export async function listAlertRules(
  sessionId: string,
  token: string | null,
): Promise<{ items: AlertRule[]; total: number }> {
  const raw = await apiFetch<unknown>(alertRulesPath(sessionId), {
    method: "GET",
    token,
  });
  return AlertRuleListResponseSchema.parse(raw);
}

export async function createAlertRule(
  sessionId: string,
  request: AlertRuleCreateRequest,
  token: string | null,
): Promise<AlertRule> {
  const raw = await apiFetch<unknown>(alertRulesPath(sessionId), {
    method: "POST",
    token,
    body: request,
  });
  return AlertRuleSchema.parse(raw);
}

export async function deactivateAlertRule(
  sessionId: string,
  ruleId: string,
  token: string | null,
): Promise<void> {
  await apiFetch<void>(`${alertRulesPath(sessionId)}/${ruleId}`, {
    method: "DELETE",
    token,
  });
}
