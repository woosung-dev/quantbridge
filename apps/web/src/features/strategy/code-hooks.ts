"use client";

import { useMutation, useQueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useAuthCtx } from "@/hooks/use-auth-ctx";

import { listCodeStrategies, saveCodeStrategy, submitCodeBacktest } from "./code-api";
import {
  CodePeriodSchema,
  SaveCodeStrategySchema,
  codeStrategyKeys,
  type CodeLanguage,
  type CodeStrategy,
} from "./code-schemas";

type Draft = {
  name: string;
  language: CodeLanguage;
  source: string;
  params: string;
  warmup: number;
  symbol: string;
  timeframe: "1h" | "4h" | "1d";
  allocation: number;
};
const newDraft = (): Draft => ({
  name: "",
  language: "python",
  source: "",
  params: "{}",
  warmup: 200,
  symbol: "BTC/USDT",
  timeframe: "1h",
  allocation: 10,
});
function fromSaved(item: CodeStrategy): Draft {
  return {
    name: item.name,
    language: item.version.language,
    source: item.version.source_code,
    params: JSON.stringify(item.version.params, null, 2),
    warmup: item.version.warmup_bars,
    symbol: item.symbol ?? "BTC/USDT",
    timeframe: item.timeframe === "4h" || item.timeframe === "1d" ? item.timeframe : "1h",
    allocation: item.settings?.position_size_pct ?? 10,
  };
}
function defaultPeriod() {
  const end = new Date();
  const start = new Date(end);
  start.setUTCDate(start.getUTCDate() - 30);
  return {
    start: start.toISOString().slice(0, 10),
    end: end.toISOString().slice(0, 10),
    capital: "10000",
  };
}

export function useCodeWorkspace() {
  const { uid, getToken } = useAuthCtx();
  const router = useRouter();
  const client = useQueryClient();
  const listing = useSuspenseQuery({
    queryKey: codeStrategyKeys.list(uid),
    queryFn: async () => listCodeStrategies(await getToken()),
  });
  const [draft, setDraft] = useState(newDraft);
  const [selected, setSelected] = useState<CodeStrategy | null>(null);
  const [period, setPeriod] = useState(defaultPeriod);
  const dirty = selected === null || JSON.stringify(draft) !== JSON.stringify(fromSaved(selected));
  const save = useMutation({
    mutationFn: async () => {
      const body = SaveCodeStrategySchema.parse({
        name: draft.name,
        symbol: draft.symbol,
        timeframe: draft.timeframe,
        code: {
          schema_version: 1,
          execution_policy: "code_v1",
          language: draft.language,
          source_code: draft.source,
          warmup_bars: draft.warmup,
          params: JSON.parse(draft.params),
          provenance: selected?.version.provenance ?? { origin: "manual_editor" },
        },
        settings: {
          schema_version: 1,
          leverage: 1,
          margin_mode: "cross",
          position_size_pct: draft.allocation,
          fill_timing: "next_bar_open",
        },
      });
      return saveCodeStrategy(selected?.id ?? null, body, await getToken());
    },
    onSuccess: async (item) => {
      setSelected(item);
      setDraft(fromSaved(item));
      await client.invalidateQueries({ queryKey: codeStrategyKeys.list(uid) });
    },
  });
  const backtest = useMutation({
    mutationFn: async () => {
      if (dirty || !selected) throw new Error("변경한 코드를 먼저 저장하세요.");
      const dates = CodePeriodSchema.parse(period);
      return submitCodeBacktest(
        {
          strategy_id: selected.id,
          symbol: draft.symbol,
          timeframe: draft.timeframe,
          period_start: `${dates.start}T00:00:00Z`,
          period_end: `${dates.end}T00:00:00Z`,
          initial_capital: dates.capital,
          position_size_pct: draft.allocation,
        },
        await getToken(),
      );
    },
    onSuccess: (result) => router.push(`/backtests/${result.backtest_id}`),
  });
  const busy = save.isPending || backtest.isPending;
  return {
    draft,
    selected,
    period,
    dirty,
    busy,
    save,
    backtest,
    items: listing.data.items,
    change: (patch: Partial<Draft>) => setDraft((previous) => ({ ...previous, ...patch })),
    changePeriod: (patch: Partial<typeof period>) =>
      setPeriod((previous) => ({ ...previous, ...patch })),
    load: (item: CodeStrategy) => {
      setSelected(item);
      setDraft(fromSaved(item));
      save.reset();
      backtest.reset();
    },
    reset: () => {
      setSelected(null);
      setDraft(newDraft());
      save.reset();
      backtest.reset();
    },
  };
}
