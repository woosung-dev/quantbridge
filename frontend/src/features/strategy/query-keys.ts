// 서버/클라이언트 공용 query key factory.
// hooks.ts는 "use client"이므로 RSC에서 직접 import 시 제약 → 여기를 pure module로 분리.
// frontend.md §3.2 — Query Key 하드코딩 금지.
//
// Sprint FE-02: factory 시그니처에 `userId` identity 추가 (Clerk JWT 교체 시 cache 격리).
// 모든 호출부는 `useAuth().userId ?? "anon"` 를 맨 앞 인자로 넘긴다.

import type { StrategyListQuery } from "./schemas";

export const strategyKeys = {
  all: (userId: string) => ["strategies", userId] as const,
  lists: (userId: string) => [...strategyKeys.all(userId), "list"] as const,
  list: (userId: string, query: StrategyListQuery) =>
    [...strategyKeys.lists(userId), query] as const,
  details: (userId: string) =>
    [...strategyKeys.all(userId), "detail"] as const,
  detail: (userId: string, id: string) =>
    [...strategyKeys.details(userId), id] as const,
  parse: (userId: string) => [...strategyKeys.all(userId), "parse"] as const,
  // Sprint 7b FIX: 마운트 자동 파싱용 — useQuery 기반 (StrictMode-safe idempotent).
  // 소스 전체를 key로 쓰면 같은 코드에 대한 중복 파싱 방지.
  parsePreview: (userId: string, pineSource: string) =>
    [...strategyKeys.parse(userId), "preview", pineSource] as const,
};
