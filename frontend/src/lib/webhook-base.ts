// Webhook URL base — Sprint 60 S3 BL-268 (env 분기, dev 시 명시 배지)
//
// production 에서는 NEXT_PUBLIC_WEBHOOK_BASE_URL (별도 도메인 권장, 예: https://hooks.quantbridge.app)
// dev 에서는 NEXT_PUBLIC_API_URL fallback + isDev 플래그 노출 → UI 가 "dev only" 배지 표시.

import { getApiBase } from "./api-base";

export interface WebhookBaseInfo {
  url: string;
  isDev: boolean;
}

export function getWebhookBaseUrl(): WebhookBaseInfo {
  const explicit = process.env.NEXT_PUBLIC_WEBHOOK_BASE_URL;
  if (explicit && explicit.trim().length > 0) {
    return { url: explicit.replace(/\/+$/, ""), isDev: false };
  }
  // fallback: NEXT_PUBLIC_API_URL (dev 환경) → isDev 표시
  const apiBase = getApiBase();
  const isDev =
    apiBase.includes("localhost") ||
    apiBase.includes("127.0.0.1") ||
    apiBase.startsWith("http://");
  return { url: apiBase, isDev };
}
