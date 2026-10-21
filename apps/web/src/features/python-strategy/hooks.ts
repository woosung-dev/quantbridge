"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuthCtx, type TokenGetter } from "@/hooks/use-auth-ctx";
import { useInvalidatingMutation } from "@/hooks/use-invalidating-mutation";
import { makeRefetchInterval, makeStatusPoll } from "@/lib/query-poll";
import { ApiError } from "@/lib/api-client";
import {
  cancelPythonRun,
  getPythonCapabilities,
  getPythonRun,
  listPythonRuns,
  listPythonStrategies,
  savePythonStrategy,
  startPythonBacktest,
} from "./api";
import { pythonStrategyKeys } from "./query-keys";
import {
  PythonBacktestRequestSchema,
  PythonStrategyBodySchema,
  type PythonBacktestBody,
  type PythonBacktestDraft,
  type PythonRun,
  type PythonStrategy,
  type PythonStrategyBody,
  type PythonStrategyDraft,
} from "./schemas";

export const pythonRunPoll = makeStatusPoll<PythonRun>(
  (run) => run.status,
  new Set(["completed", "failed", "cancelled"]),
  2_000,
);
export const pythonRunListPoll = makeRefetchInterval<{ items: PythonRun[] }>((data) =>
  data?.items.some((run) => run.status === "pending" || run.status === "running") ? 2_000 : false,
);

function makeFetcher<T>(fetcher: (token: string | null) => Promise<T>, getToken: TokenGetter) {
  return async () => fetcher(await getToken());
}

export function usePythonLab() {
  const { uid, getToken } = useAuthCtx();
  const queryClient = useQueryClient();
  const [strategy, setStrategy] = useState<PythonStrategy | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const capabilities = useQuery({
    queryKey: pythonStrategyKeys.capabilities(uid),
    queryFn: makeFetcher(getPythonCapabilities, getToken),
    retry: 1,
  });
  const strategies = useQuery({
    queryKey: pythonStrategyKeys.list(uid),
    queryFn: makeFetcher(listPythonStrategies, getToken),
    retry: 1,
  });
  const history = useQuery({
    queryKey: pythonStrategyKeys.runs(uid, strategy?.id ?? "none"),
    queryFn: makeFetcher((token) => listPythonRuns(strategy?.id ?? "", token), getToken),
    enabled: strategy !== null,
    refetchInterval: pythonRunListPoll,
  });
  const run = useQuery({
    queryKey: pythonStrategyKeys.run(uid, runId ?? "none"),
    queryFn: makeFetcher((token) => getPythonRun(runId ?? "", token), getToken),
    enabled: runId !== null,
    refetchInterval: pythonRunPoll,
    refetchIntervalInBackground: false,
  });
  const save = useInvalidatingMutation(
    {
      mutationFn: ({ id, body }: { id: string | null; body: PythonStrategyBody }, token) =>
        savePythonStrategy(id, body, token),
      invalidateKeys: (userId) => [pythonStrategyKeys.list(userId)],
    },
    { onSuccess: setStrategy },
  );
  const start = useInvalidatingMutation(
    {
      mutationFn: ({ id, body }: { id: string; body: PythonBacktestBody }, token) =>
        startPythonBacktest(id, body, token),
      invalidateKeys: (userId, result) => [pythonStrategyKeys.runs(userId, result.strategy_id)],
    },
    {
      onSuccess: (result) => setRunId(result.id),
      onError: (error) => {
        if (error instanceof ApiError && error.code === "python_strategy_version_conflict") {
          void queryClient.invalidateQueries({ queryKey: pythonStrategyKeys.list(uid) });
        }
      },
    },
  );
  const cancel = useInvalidatingMutation({
    mutationFn: cancelPythonRun,
    invalidateKeys: (userId, result) => [
      pythonStrategyKeys.run(userId, result.id),
      pythonStrategyKeys.runs(userId, result.strategy_id),
    ],
  });

  function selectStrategy(selected: PythonStrategy | null) {
    setStrategy(selected);
    setRunId(null);
    save.reset();
    start.reset();
    cancel.reset();
  }

  return {
    strategy,
    capabilities,
    strategies,
    history,
    run,
    save,
    start,
    cancel,
    selectStrategy,
    selectRun: setRunId,
    saveDraft: (draft: PythonStrategyDraft) =>
      save.mutate({ id: strategy?.id ?? null, body: PythonStrategyBodySchema.parse(draft) }),
    startRun: (draft: PythonBacktestDraft) => {
      if (strategy)
        start.mutate({
          id: strategy.id,
          body: {
            ...PythonBacktestRequestSchema.parse(draft),
            expected_version_id: strategy.version_id,
          },
        });
    },
  };
}
