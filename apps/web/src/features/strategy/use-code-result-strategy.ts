"use client";

import { useQuery } from "@tanstack/react-query";
import { useAuthCtx } from "@/hooks/use-auth-ctx";
import { getCodeResultStrategy } from "./code-result-api";
import { strategyKeys } from "./query-keys";

export function useCodeResultStrategy(id: string) {
  const { uid, getToken } = useAuthCtx();
  return useQuery({
    queryKey: strategyKeys.codeResultDetail(uid, id),
    queryFn: async () => getCodeResultStrategy(id, await getToken()),
    retry: 1,
  });
}
