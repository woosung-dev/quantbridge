import type { Metadata } from "next";
import { auth } from "@clerk/nextjs/server";
import {
  HydrationBoundary,
  QueryClient,
  dehydrate,
} from "@tanstack/react-query";

import { listBacktests } from "@/features/backtest/api";
import { backtestKeys } from "@/features/backtest/query-keys";

import { BacktestList } from "./_components/backtest-list";

export const metadata: Metadata = {
  title: "백테스트 | QuantBridge",
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
