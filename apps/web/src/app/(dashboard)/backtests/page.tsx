// 백테스트 목록 페이지 (/backtests, Server Component) — 세션 JWT 로 React Query 를
// 서버에서 prefetch(PAGE_SIZE=20) 한 뒤 HydrationBoundary 로 BacktestList 에 hydrate.
import type { Metadata } from "next";
import {
  HydrationBoundary,
  QueryClient,
  dehydrate,
} from "@tanstack/react-query";

import { getServerAuth } from "@/lib/auth-server";
import { listBacktests } from "@/features/backtest/api";
import { buildBacktestListQuery } from "@/features/backtest/list-query";
import { backtestKeys, type BacktestListQuery } from "@/features/backtest/query-keys";

import { BacktestList } from "@/features/backtest/components/backtest-list";

export const metadata: Metadata = {
  title: "백테스트",
};

function makePrefetchListFetcher(query: BacktestListQuery, token: string) {
  return () => listBacktests(query, token);
}

export default async function BacktestsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  // ★prefetch 키는 `BacktestList` 가 URL 에서 만드는 키와 **글자 하나까지 같아야 한다**.
  //   종전에는 여기서 `{limit, offset}` 만 넣어 정렬 축이 빠졌고, 그래서 hydrate 된 캐시를
  //   클라이언트가 못 써서 같은 목록이 SSR 과 브라우저에서 각각 한 번씩 나갔다([BL-786]).
  //   두 곳이 같은 생성자를 부르게 해 다시 어긋날 수 없게 한다.
  const params = await searchParams;
  const orderByParam = Array.isArray(params.order_by) ? params.order_by[0] : params.order_by;
  const orderParam = Array.isArray(params.order) ? params.order[0] : params.order;
  const query = buildBacktestListQuery(orderByParam, orderParam);
  const queryClient = new QueryClient();

  const { userId, token } = await getServerAuth();
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
