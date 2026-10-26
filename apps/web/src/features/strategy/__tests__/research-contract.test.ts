import { describe, expect, it } from "vitest";

import { CreateBacktestRequestSchema, BacktestDetailSchema } from "@/features/backtest/schemas";
import { CodeSnapshotSchema } from "../code-schemas";
import { ResearchExecutionSchema } from "../research-contract";

const research = {
  contract_version: 1,
  exit_policy: "signal_only_v1",
  reentry_policy: "close_then_reenter_v1",
  signal_mode: "shared_events",
  signal_mapping_hash: "a".repeat(64),
} as const;
const code = {
  schema_version: 1,
  execution_policy: "code_research_v1",
  language: "python",
  source_code: "source",
  warmup_bars: 200,
  params: {},
  provenance: { research_execution: research },
} as const;

describe("연구 정책 응답과 재실행 계약", () => {
  it("연구 코드는 엄격한 정책을 요구하고 기존 코드는 추가 입력 없이 허용한다", () => {
    expect(CodeSnapshotSchema.parse(code)).toEqual(code);
    expect(CodeSnapshotSchema.safeParse({ ...code, provenance: {} }).success).toBe(false);
    expect(ResearchExecutionSchema.safeParse({ ...research, extra: 1 }).success).toBe(false);
    expect(ResearchExecutionSchema.safeParse({ ...research, contract_version: true }).success).toBe(
      false,
    );
    expect(
      CodeSnapshotSchema.safeParse({ ...code, execution_policy: "code_v1", provenance: {} })
        .success,
    ).toBe(true);
  });

  it("백테스트 재실행 요청은 연구 정책과 불변 버전 핀을 제거하지 않는다", () => {
    const request = CreateBacktestRequestSchema.parse({
      strategy_id: "11111111-1111-4111-8111-111111111111",
      strategy_version_id: "22222222-2222-4222-8222-222222222222",
      execution_policy: "code_research_v1",
      symbol: "BTC/USDT",
      timeframe: "1h",
      period_start: "2024-01-01T00:00:00Z",
      period_end: "2025-01-01T00:00:00Z",
      initial_capital: 10000,
      fill_timing: "next_bar_open",
    });
    expect(request.execution_policy).toBe("code_research_v1");
    expect(request.strategy_version_id).toBe("22222222-2222-4222-8222-222222222222");
  });

  it("상세 응답은 연구 계약과 실행 당시 버전 ID를 보존한다", () => {
    const response = BacktestDetailSchema.parse({
      id: "33333333-3333-4333-8333-333333333333",
      strategy_id: "11111111-1111-4111-8111-111111111111",
      strategy_version_id: "22222222-2222-4222-8222-222222222222",
      symbol: "BTC/USDT",
      timeframe: "1h",
      period_start: "2024-01-01T00:00:00Z",
      period_end: "2025-01-01T00:00:00Z",
      created_at: "2026-10-26T00:00:00Z",
      completed_at: null,
      status: "queued",
      initial_capital: "10000",
      config: { execution_policy: "code_research_v1", research_execution: research },
    });
    expect(response.config?.research_execution).toEqual(research);
    expect(response.strategy_version_id).toBe("22222222-2222-4222-8222-222222222222");
  });
});
