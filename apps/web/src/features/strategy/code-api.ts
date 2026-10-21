import { BacktestCreatedResponseSchema } from "@/features/backtest/schemas";
import { LiveSessionSchema } from "@/features/live-sessions/schemas";
import { apiFetch } from "@/lib/api-client";

import {
  CodeStrategyListSchema,
  CodeDemoRequestSchema,
  CodeStrategySchema,
  SaveCodeStrategySchema,
  type SaveCodeStrategy,
  type CodeDemoRequest,
} from "./code-schemas";

const CODE_PATH = "/api/v1/strategies/code";

export async function listCodeStrategies(token: string | null) {
  return CodeStrategyListSchema.parse(await apiFetch<unknown>(CODE_PATH, { token }));
}

export async function submitCodeDemo(body: CodeDemoRequest, token: string | null) {
  return LiveSessionSchema.parse(
    await apiFetch<unknown>("/api/v1/live-sessions", {
      method: "POST",
      token,
      body: CodeDemoRequestSchema.parse(body),
    }),
  );
}

export async function saveCodeStrategy(
  id: string | null,
  body: SaveCodeStrategy,
  token: string | null,
) {
  const request = SaveCodeStrategySchema.parse(body);
  return CodeStrategySchema.parse(
    await apiFetch<unknown>(id ? `${CODE_PATH}/${id}` : CODE_PATH, {
      method: id ? "PUT" : "POST",
      token,
      body: request,
    }),
  );
}

export async function submitCodeBacktest(
  body: {
    strategy_id: string;
    symbol: string;
    timeframe: string;
    period_start: string;
    period_end: string;
    initial_capital: string;
    position_size_pct: number;
  },
  token: string | null,
) {
  return BacktestCreatedResponseSchema.parse(
    await apiFetch<unknown>("/api/v1/backtests", {
      method: "POST",
      token,
      body: {
        ...body,
        execution_policy: "code_v1",
        fill_timing: "next_bar_open",
        leverage: "1",
        include_funding: true,
      },
    }),
  );
}
