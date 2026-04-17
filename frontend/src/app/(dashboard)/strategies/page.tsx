import type { Metadata } from "next";
import { auth } from "@clerk/nextjs/server";
import {
  HydrationBoundary,
  QueryClient,
  dehydrate,
} from "@tanstack/react-query";

import { listStrategies } from "@/features/strategy/api";
import { strategyKeys } from "@/features/strategy/query-keys";
import type { ParseStatus, StrategyListQuery } from "@/features/strategy/schemas";
import { StrategyList } from "./_components/strategy-list";

export const metadata: Metadata = {
  title: "전략 | QuantBridge",
};

const PAGE_SIZE = 20;

function parseStatusOrUndefined(v?: string): ParseStatus | undefined {
  return v === "ok" || v === "unsupported" || v === "error" ? v : undefined;
}

export default async function StrategiesPage({
  searchParams,
}: {
  // Next 16 App Router — searchParams는 Promise. StrategyList 클라이언트 필터와 동일 key 체계.
  searchParams: Promise<{
    parse_status?: string;
    archived?: string;
    page?: string;
  }>;
}) {
  const sp = await searchParams;
  const archived = sp.archived === "true";
  const parseStatus = parseStatusOrUndefined(sp.parse_status);
  const page = Math.max(0, Number(sp.page ?? "0") || 0);

  const query: StrategyListQuery = {
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
    is_archived: archived,
  };
  if (parseStatus) query.parse_status = parseStatus;

  const queryClient = new QueryClient();

  // 서버 prefetch는 URL 쿼리 그대로 반영하여 client query key와 일치시킨다.
  // proxy.ts가 이 라우트를 보호하므로 익명 접근은 여기까지 오지 않음.
  const { getToken } = await auth();
  const token = await getToken();

  if (token) {
    try {
      await queryClient.prefetchQuery({
        queryKey: strategyKeys.list(query),
        queryFn: () => listStrategies(query, token),
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
