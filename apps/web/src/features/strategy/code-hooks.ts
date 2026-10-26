"use client";

import {
  useMutation,
  usePrefetchQuery,
  useQueryClient,
  useSuspenseQuery,
} from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useMemo, useRef, useState } from "react";

import { useAuthCtx } from "@/hooks/use-auth-ctx";
import { ResearchExecutionSchema } from "./research-contract";
import { getCodeResultStrategy } from "./code-result-api";
import { useExchangeAccounts } from "@/features/trading/hooks";
import { listExchangeAccounts } from "@/features/trading/api";
import { tradingKeys } from "@/features/trading/query-keys";
import { liveSessionKeys } from "@/features/live-sessions/query-keys";

import {
  generateCodeStrategy,
  listCodeStrategies,
  saveCodeStrategy,
  submitCodeBacktest,
  submitCodeDemo,
} from "./code-api";
import {
  CodePeriodSchema,
  GenerateCodeStrategyRequestSchema,
  SaveCodeStrategySchema,
  codeStrategyKeys,
  type CodeLanguage,
  type CodeSnapshot,
  type CodeStrategy,
  type GenerateCodeStrategyResponse,
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

function canonicalParams(params: unknown): string | undefined {
  return JSON.stringify(params, (_key, value: unknown) =>
    value && typeof value === "object" && !Array.isArray(value)
      ? Object.fromEntries(
          Object.entries(value).sort(([left], [right]) => left.localeCompare(right)),
        )
      : value,
  );
}

function sameCode(draft: Draft, snapshot: CodeSnapshot): boolean {
  return (
    draft.source === snapshot.source_code &&
    draft.language === snapshot.language &&
    draft.warmup === snapshot.warmup_bars &&
    canonicalParams(JSON.parse(draft.params)) === canonicalParams(snapshot.params)
  );
}

export function useCodeWorkspace(initialStrategyId?: string) {
  const { uid, getToken } = useAuthCtx();
  const router = useRouter();
  const client = useQueryClient();
  // 목록 Suspense가 계정 조회를 가로막지 않도록 동일 캐시 키로 먼저 시작한다.
  usePrefetchQuery({
    queryKey: tradingKeys.exchangeAccounts(uid),
    queryFn: async () => listExchangeAccounts(await getToken()),
    retry: 1,
  });
  const [offset, setOffset] = useState(0);
  const listing = useSuspenseQuery({
    queryKey: codeStrategyKeys.page(uid, offset, initialStrategyId),
    queryFn: async () => {
      const token = await getToken();
      const page = await listCodeStrategies(token, offset);
      const selection =
        page.items.find((item) => item.id === initialStrategyId) ??
        (initialStrategyId ? await getCodeResultStrategy(initialStrategyId, token) : null);
      return { ...page, ...(initialStrategyId ? { selection } : {}) };
    },
  });
  const initial = listing.data.selection ?? null;
  const [draft, setDraft] = useState(() => (initial ? fromSaved(initial) : newDraft()));
  const [selected, setSelected] = useState<CodeStrategy | null>(initial);
  const savedDraft = useMemo(() => (selected ? fromSaved(selected) : null), [selected]);
  const [preview, setPreview] = useState<GenerateCodeStrategyResponse | null>(null);
  const [generated, setGenerated] = useState<CodeSnapshot | null>(null);
  const [generationRevision, setGenerationRevision] = useState(0);
  const generationEpoch = useRef(0);
  const generation = useMutation({
    retry: false,
    mutationFn: async (request: {
      prompt: string;
      warmup: number;
      params: string;
      epoch: number;
    }) =>
      generateCodeStrategy(
        GenerateCodeStrategyRequestSchema.parse({
          prompt: request.prompt,
          warmup_bars: request.warmup,
          params: JSON.parse(request.params),
        }),
        await getToken(),
      ),
    onSuccess: (result, request) => {
      if (generationEpoch.current === request.epoch) setPreview(result);
    },
  });
  const clearGeneration = () => {
    generationEpoch.current += 1;
    generation.reset();
    setPreview(null);
    setGenerated(null);
    setGenerationRevision((revision) => revision + 1);
  };
  const accounts = useExchangeAccounts();
  const demoAccounts = (accounts.data ?? []).filter(
    (account) =>
      account.exchange === "bybit" && account.mode === "demo" && account.read_only === false,
  );
  const [accountId, setAccountId] = useState("");
  const [period, setPeriod] = useState(defaultPeriod);
  const dirty =
    savedDraft === null ||
    draft.name !== savedDraft.name ||
    draft.language !== savedDraft.language ||
    draft.source !== savedDraft.source ||
    draft.params !== savedDraft.params ||
    draft.warmup !== savedDraft.warmup ||
    draft.symbol !== savedDraft.symbol ||
    draft.timeframe !== savedDraft.timeframe ||
    draft.allocation !== savedDraft.allocation;
  // 화면과 action이 같은 검토 대상·거부 이유를 사용한다. 목록 갱신으로 버전을 교체하지 않는다.
  const reviewed = dirty ? null : selected;
  const researchExecution =
    selected?.version.execution_policy === "code_research_v1"
      ? ResearchExecutionSchema.parse(selected.version.provenance.research_execution)
      : null;
  const saveBlockReason =
    researchExecution &&
    savedDraft &&
    (draft.source !== savedDraft.source ||
      draft.language !== savedDraft.language ||
      draft.params !== savedDraft.params ||
      draft.warmup !== savedDraft.warmup)
      ? "연구 원문·입력 변경은 새 코드에서 작성하세요. 기존 검증 근거는 재사용하지 않습니다."
      : null;
  const backtestBlockReason = reviewed ? null : "변경한 코드를 먼저 저장하세요.";
  const demoBlockReason = researchExecution
    ? "연구 실행 정책은 데모 자동매매를 지원하지 않습니다."
    : !reviewed || draft.timeframe !== "1h"
      ? "저장한 1시간 전략을 선택하세요."
      : !demoAccounts.some((account) => account.id === accountId)
        ? "주문 권한이 확인된 Bybit Demo 계정을 선택하세요."
        : null;
  const canBacktest = backtestBlockReason === null;
  const canDemo = demoBlockReason === null;
  const save = useMutation({
    mutationFn: async () => {
      if (saveBlockReason) throw new Error(saveBlockReason);
      const body = SaveCodeStrategySchema.parse({
        name: draft.name,
        symbol: draft.symbol,
        timeframe: draft.timeframe,
        code: {
          schema_version: 1,
          execution_policy: selected?.version.execution_policy ?? "code_v1",
          language: draft.language,
          source_code: draft.source,
          warmup_bars: draft.warmup,
          params: JSON.parse(draft.params),
          provenance:
            generated && sameCode(draft, generated)
              ? generated.provenance
              : selected && sameCode(draft, selected.version)
                ? selected.version.provenance
                : { origin: "manual_editor", parent_version_id: selected?.version.id ?? null },
        },
        settings: {
          ...selected?.settings,
          schema_version: 1,
          leverage: 1,
          margin_mode: selected?.settings?.margin_mode ?? "cross",
          position_size_pct: draft.allocation,
          fill_timing: "next_bar_open",
        },
      });
      return saveCodeStrategy(selected?.id ?? null, body, await getToken());
    },
    onSuccess: async (item) => {
      setSelected(item);
      setDraft(fromSaved(item));
      setGenerated(null);
      await client.invalidateQueries({ queryKey: codeStrategyKeys.list(uid) });
    },
  });
  const backtest = useMutation({
    mutationFn: async () => {
      if (!canBacktest) throw new Error(backtestBlockReason!);
      const dates = CodePeriodSchema.parse(period);
      return submitCodeBacktest(
        {
          strategy_id: reviewed!.id,
          strategy_version_id: reviewed!.version.id,
          execution_policy: reviewed!.version.execution_policy,
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
  const demo = useMutation({
    mutationFn: async () => {
      if (!canDemo) throw new Error(demoBlockReason!);
      return submitCodeDemo(
        {
          strategy_id: reviewed!.id,
          strategy_version_id: reviewed!.version.id,
          exchange_account_id: accountId,
          source_policy: "code_v1",
          symbol: draft.symbol,
          interval: "1h",
        },
        await getToken(),
      );
    },
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: liveSessionKeys.all(uid) });
      router.push("/trading");
    },
  });
  const busy = save.isPending || backtest.isPending || demo.isPending;
  return {
    draft,
    selected,
    period,
    dirty,
    busy,
    canBacktest,
    canDemo,
    researchExecution,
    saveBlockReason,
    backtestBlockReason,
    demoBlockReason,
    preview,
    hasAppliedPreview: generated !== null,
    generation,
    generationRevision,
    generate: (prompt: string) => {
      generationEpoch.current += 1;
      setPreview(null);
      generation.mutate({
        prompt,
        warmup: draft.warmup,
        params: draft.params,
        epoch: generationEpoch.current,
      });
    },
    applyPreview: () => {
      if (!preview || busy) return;
      const code = preview.code;
      setDraft((previous) => ({
        ...previous,
        source: code.source_code,
        language: code.language,
        warmup: code.warmup_bars,
        params: JSON.stringify(code.params, null, 2),
      }));
      setGenerated(code);
      setPreview(null);
      generation.reset();
      save.reset();
      backtest.reset();
      demo.reset();
    },
    save,
    backtest,
    demo,
    accounts,
    demoAccounts,
    accountId,
    setAccountId,
    items: listing.data.items,
    total: listing.data.total,
    offset,
    setOffset,
    change: (patch: Partial<Draft>) => setDraft((previous) => ({ ...previous, ...patch })),
    changePeriod: (patch: Partial<typeof period>) =>
      setPeriod((previous) => ({ ...previous, ...patch })),
    load: (item: CodeStrategy) => {
      clearGeneration();
      setSelected(item);
      setDraft(fromSaved(item));
      save.reset();
      backtest.reset();
      demo.reset();
    },
    reset: () => {
      clearGeneration();
      setSelected(null);
      setDraft(newDraft());
      save.reset();
      backtest.reset();
      demo.reset();
    },
  };
}
