"use client";

// context7 TanStack Query 공식 SSR 패턴 — isServer 분기 + 브라우저 싱글톤.
// useState 초기화는 Suspense boundary 없이 서버 렌더링 시 client 리셋 위험 (공식 주석 근거).

import {
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import type { ReactNode } from "react";

// TanStack v5: `isServer` export가 deprecated → `typeof window` 패턴으로 판별.
const isServerEnv = typeof window === "undefined";

function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // SSR 시 즉시 refetch 방지 (context7 권장 ≥ 0). QuantBridge 표준 60s.
        staleTime: 60 * 1000,
        gcTime: 5 * 60 * 1000,
        retry: 1,
        refetchOnWindowFocus: false,
      },
      mutations: {
        retry: 0,
      },
    },
  });
}

let browserQueryClient: QueryClient | undefined = undefined;

function getQueryClient(): QueryClient {
  if (isServerEnv) {
    // 서버: 매 요청마다 새 client (요청 간 격리)
    return makeQueryClient();
  }
  // 브라우저: 싱글톤. React Suspend 시 client 재생성 방지.
  if (!browserQueryClient) browserQueryClient = makeQueryClient();
  return browserQueryClient;
}

export function QueryProvider({ children }: { children: ReactNode }) {
  const queryClient = getQueryClient();

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {process.env.NODE_ENV === "development" && (
        <ReactQueryDevtools initialIsOpen={false} />
      )}
    </QueryClientProvider>
  );
}
