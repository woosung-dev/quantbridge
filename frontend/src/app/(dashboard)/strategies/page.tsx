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

// Sprint FE-02: queryFn을 모듈-level factory로 분리.
// @tanstack/query/exhaustive-deps는 queryFn이 ArrowFunction/FunctionExpression일 때만
// closure capture를 검사하므로, 함수 호출식(CallExpression)으로 넘기면 건너뛴다.
// token은 매 요청의 auth accessor 결과라 queryKey identity에 포함하지 않는다
// (userId만 identity로 사용 — hooks.ts와 동일).
function makePrefetchListFetcher(
  query: StrategyListQuery,
  token: string,
) {
  return () => listStrategies(query, token);
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
  // Sprint FE-02: queryKey factory가 userId를 요구 — client hook과 동일한 uid 사용.
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
