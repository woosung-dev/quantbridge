import type { ParseError, ParsePreviewResponse } from "@/features/strategy/schemas";
import {
  adviseError,
  adviseWarning,
  describeFunction,
  PINE_FUNCTION_LEXICON,
  type ErrorAdvice,
  type PineFunctionDescription,
  type WarningAdvice,
} from "@/features/strategy/pine-lexicon";

const FUNCTION_CAP = 14;

export type StepSummary = {
  errorCount: number;
  warningCount: number;
  functionCount: number;
  pineVersion: "v4" | "v5";
};

export type ParseStep =
  | { kind: "intro"; summary: StepSummary }
  | {
      kind: "error";
      index: number;
      total: number;
      error: ParseError;
      advice: ErrorAdvice;
    }
  | {
      kind: "warning";
      index: number;
      total: number;
      message: string;
      advice: WarningAdvice;
    }
  | {
      kind: "function";
      index: number;
      total: number;
      name: string;
      description: PineFunctionDescription;
    }
  | {
      kind: "final";
      summary: StepSummary;
      canSave: boolean;
      hiddenFunctionCount: number;
    };

function prioritizeFunctions(fns: readonly string[]): string[] {
  const known: string[] = [];
  const unknown: string[] = [];
  for (const fn of fns) {
    if (fn in PINE_FUNCTION_LEXICON) known.push(fn);
    else unknown.push(fn);
  }
  return [...known, ...unknown];
}

export function buildParseSteps(result: ParsePreviewResponse): ParseStep[] {
  const summary: StepSummary = {
    errorCount: result.errors.length,
    warningCount: result.warnings.length,
    functionCount: result.functions_used.length,
    pineVersion: result.pine_version,
  };

  const prioritized = prioritizeFunctions(result.functions_used);
  const visibleFunctions = prioritized.slice(0, FUNCTION_CAP);
  const hiddenFunctionCount = Math.max(0, prioritized.length - FUNCTION_CAP);

  const errorSteps: ParseStep[] = result.errors.map((error, i) => ({
    kind: "error",
    index: i,
    total: result.errors.length,
    error,
    advice: adviseError(error),
  }));

  const warningSteps: ParseStep[] = result.warnings.map((message, i) => ({
    kind: "warning",
    index: i,
    total: result.warnings.length,
    message,
    advice: adviseWarning(message),
  }));

  const functionSteps: ParseStep[] = visibleFunctions.map((name, i) => ({
    kind: "function",
    index: i,
    total: visibleFunctions.length,
    name,
    description: describeFunction(name),
  }));

  return [
    { kind: "intro", summary },
    ...errorSteps,
    ...warningSteps,
    ...functionSteps,
    {
      kind: "final",
      summary,
      canSave: result.status === "ok",
      hiddenFunctionCount,
    },
  ];
}
