import { BacktestCreatedResponseSchema } from "@/features/backtest/schemas";
import { LiveSessionSchema } from "@/features/live-sessions/schemas";
import { apiFetch } from "@/lib/api-client";
import type { CodeExecutionPolicy } from "./research-contract";

import {
  CodeStrategyListSchema,
  CodeDemoRequestSchema,
  CodeStrategySchema,
  SaveCodeStrategySchema,
  GenerateCodeStrategyRequestSchema,
  GenerateCodeStrategyResponseSchema,
  type SaveCodeStrategy,
  type CodeDemoRequest,
  type GenerateCodeStrategyRequest,
} from "./code-schemas";

const CODE_PATH = "/api/v1/strategies/code";

export async function generateCodeStrategy(
  body: GenerateCodeStrategyRequest,
  token: string | null,
) {
  return GenerateCodeStrategyResponseSchema.parse(
    await apiFetch<unknown>(`${CODE_PATH}/generate`, {
      method: "POST",
      token,
      body: GenerateCodeStrategyRequestSchema.parse(body),
    }),
  );
}

export async function listCodeStrategies(token: string | null, offset = 0) {
  const path = offset === 0 ? CODE_PATH : `${CODE_PATH}?limit=20&offset=${offset}`;
  return CodeStrategyListSchema.parse(await apiFetch<unknown>(path, { token }));
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
    strategy_version_id: string;
    execution_policy?: CodeExecutionPolicy;
    fees_pct?: number;
    maker_fee_pct?: number;
    slippage_pct?: number;
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
        execution_policy: body.execution_policy ?? "code_v1",
        ...(body.execution_policy === "code_research_v1"
          ? {
              fees_pct: body.fees_pct ?? 0.0002,
              maker_fee_pct: body.maker_fee_pct ?? 0.0001,
              slippage_pct: body.slippage_pct ?? 0.0001,
            }
          : {}),
        fill_timing: "next_bar_open",
        leverage: "1",
        include_funding: true,
      },
    }),
  );
}
