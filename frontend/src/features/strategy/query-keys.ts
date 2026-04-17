// 서버/클라이언트 공용 query key factory.
// hooks.ts는 "use client"이므로 RSC에서 직접 import 시 제약 → 여기를 pure module로 분리.
// frontend.md §3.2 — Query Key 하드코딩 금지.

import type { StrategyListQuery } from "./schemas";

export const strategyKeys = {
  all: ["strategies"] as const,
  lists: () => [...strategyKeys.all, "list"] as const,
  list: (query: StrategyListQuery) => [...strategyKeys.lists(), query] as const,
  details: () => [...strategyKeys.all, "detail"] as const,
  detail: (id: string) => [...strategyKeys.details(), id] as const,
  parse: () => [...strategyKeys.all, "parse"] as const,
  // Sprint 7b FIX: 마운트 자동 파싱용 — useQuery 기반 (StrictMode-safe idempotent).
  // 소스 전체를 key로 쓰면 같은 코드에 대한 중복 파싱 방지.
  parsePreview: (pineSource: string) =>
    [...strategyKeys.parse(), "preview", pineSource] as const,
};
