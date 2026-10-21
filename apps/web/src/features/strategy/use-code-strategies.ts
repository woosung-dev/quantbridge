"use client";

import { useQuery } from "@tanstack/react-query";
import { useAuthCtx, type TokenGetter } from "@/hooks/use-auth-ctx";
import { listCodeStrategies } from "./code-api";
import { codeStrategyKeys } from "./code-schemas";

function makeFetcher(getToken: TokenGetter) {
  return async () => listCodeStrategies(await getToken());
}

export function useCodeStrategies() {
  const { uid, userId, getToken } = useAuthCtx();
  return useQuery({
    queryKey: codeStrategyKeys.list(uid),
    queryFn: makeFetcher(getToken),
    enabled: Boolean(userId),
  });
}
