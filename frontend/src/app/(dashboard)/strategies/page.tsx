import type { Metadata } from "next";
import { auth } from "@clerk/nextjs/server";
import {
  HydrationBoundary,
  QueryClient,
  dehydrate,
} from "@tanstack/react-query";

import { listStrategies } from "@/features/strategy/api";
import { strategyKeys } from "@/features/strategy/query-keys";
import type { StrategyListQuery } from "@/features/strategy/schemas";
import { StrategyList } from "./_components/strategy-list";

export const metadata: Metadata = {
  title: "전략 | QuantBridge",
};

// StrategyList의 초기 렌더 query와 동일해야 캐시 히트.
const INITIAL_QUERY: StrategyListQuery = {
  limit: 20,
  offset: 0,
  is_archived: false,
};

export default async function StrategiesPage() {
  const queryClient = new QueryClient();

  // 서버에서 Clerk 토큰 획득 → 서버 prefetch.
  // proxy.ts가 이 라우트를 보호하므로 익명 접근은 여기까지 오지 않음.
  const { getToken } = await auth();
  const token = await getToken();

  if (token) {
    try {
      await queryClient.prefetchQuery({
        queryKey: strategyKeys.list(INITIAL_QUERY),
        queryFn: () => listStrategies(INITIAL_QUERY, token),
      });
    } catch {
      // prefetch 실패는 silent degrade — 클라이언트 측에서 재시도.
    }
  }

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <StrategyList />
    </HydrationBoundary>
  );
}
