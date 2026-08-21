"use client";

// Optimizer 제출 공통 상태 훅 — errMsg + mutateAsync 호출 + 사용자향 에러 변환.
// raw 백엔드 에러는 노출하지 않는다(내부 용어 유출 차단) — 콘솔에만 기술 상세.

import { useState } from "react";

import type { CreateOptimizationRunRequest, OptimizationRunResponse } from "../schemas";

const GENERIC_ERROR_MSG =
  "최적화 실행에 실패했습니다. 입력값을 확인하거나 잠시 후 다시 시도해 주세요.";

export function useOptimizerSubmit(opts: {
  mutateAsync: (body: CreateOptimizationRunRequest) => Promise<OptimizationRunResponse>;
  /** console.error 태그 — "grid search submit failed" 등. */
  logTag: string;
  onSuccess?: (runId: string) => void;
}) {
  const [errMsg, setErrMsg] = useState<string | null>(null);

  const submitBody = async (body: CreateOptimizationRunRequest) => {
    setErrMsg(null);
    try {
      const created = await opts.mutateAsync(body);
      opts.onSuccess?.(created.id);
    } catch (e) {
      console.error(opts.logTag, e);
      setErrMsg(GENERIC_ERROR_MSG);
    }
  };

  return { errMsg, setErrMsg, submitBody };
}
