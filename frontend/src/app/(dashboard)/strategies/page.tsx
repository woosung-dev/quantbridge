// 전략 목록 페이지 (/strategies, Server Component) — Clerk 토큰으로 React Query 를
// 서버에서 prefetch(archived 제외, PAGE_SIZE=20) 후 HydrationBoundary 로 StrategyList 에 hydrate.
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
  title: "전략",
};

const PAGE_SIZE = 20;

// Sprint FE-02: queryFn을 모듈-level factory로 분리 (@tanstack/query/exhaustive-deps 우회).
// token은 매 요청의 auth accessor 결과라 queryKey identity에 포함하지 않는다.
function makePrefetchListFetcher(query: StrategyListQuery, token: string) {
  return () => listStrategies(query, token);
}

export default async function StrategiesPage() {
  // C 이식(screen-06) — parse_status 필터는 client-side(현재 페이지 한정)라 서버 쿼리는
  // 페이지네이션 고정값만 쓴다. client hook(useStrategies)과 동일한 queryKey 를 위해 같은 query.
  const query: StrategyListQuery = {
    limit: PAGE_SIZE,
    offset: 0,
    is_archived: false,
    order_by: "updated_at",
    order: "desc",
  };

  const queryClient = new QueryClient();

  // proxy.ts가 이 라우트를 보호하므로 익명 접근은 여기까지 오지 않음.
  // queryKey factory가 userId를 요구 — client hook과 동일한 uid 사용.
  const { userId, getToken } = await auth();
  const token = await getToken();
  const uid = userId ?? "anon";

  if (token) {
    try {
      await queryClient.prefetchQuery({
        queryKey: strategyKeys.list(uid, query),
        queryFn: makePrefetchListFetcher(query, token),
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
