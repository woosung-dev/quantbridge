// 백테스트 목록 페이지 (/backtests, Server Component) — Clerk 토큰으로 React Query 를
// 서버에서 prefetch(PAGE_SIZE=20) 한 뒤 HydrationBoundary 로 BacktestList 에 hydrate.
import type { Metadata } from "next";
import { auth } from "@clerk/nextjs/server";
import {
  HydrationBoundary,
  QueryClient,
  dehydrate,
} from "@tanstack/react-query";

import { listBacktests } from "@/features/backtest/api";
import { backtestKeys } from "@/features/backtest/query-keys";

import { BacktestList } from "@/app/(dashboard)/backtests/_components/backtest-list";

export const metadata: Metadata = {
  title: "백테스트",
};

const PAGE_SIZE = 20;

function makePrefetchListFetcher(
  query: { limit: number; offset: number },
  token: string,
) {
  return () => listBacktests(query, token);
}

export default async function BacktestsPage() {
  const query = { limit: PAGE_SIZE, offset: 0 };
  const queryClient = new QueryClient();

  const { userId, getToken } = await auth();
  const token = await getToken();
  const uid = userId ?? "anon";

  if (token) {
    try {
      await queryClient.prefetchQuery({
        queryKey: backtestKeys.list(uid, query),
        queryFn: makePrefetchListFetcher(query, token),
      });
    } catch {
      // silent degrade — 클라이언트 측 재시도.
    }
  }

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <BacktestList />
    </HydrationBoundary>
  );
}
