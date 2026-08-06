"use client";

// 백테스트 목록 라우트 에러 경계 (S5) — C 디자인 언어. render-time 예외를 catch 하고
// reset 으로 재시도한다 (.claude/rules/frontend.md §6). 목록 내부의 fetch 실패는
// BacktestList 가 자체 state-box 로 처리하므로, 여기는 그 위의 render 예외 안전망이다.

import { AlertTriangleIcon, RefreshCwIcon } from "lucide-react";

import { StateBox } from "@/components/state-box";

interface BacktestsErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function BacktestsError({ error, reset }: BacktestsErrorProps) {
  return (
    <main className="page">
      <div className="card">
        <div className="card-body">
          <StateBox
            tone="failed"
            testId="backtests-route-error"
            icon={<AlertTriangleIcon />}
            title="백테스트 목록을 표시하지 못했습니다."
            body={
              error.message ||
              "예상치 못한 오류가 발생했습니다. 다시 시도하거나 잠시 후 새로고침해 주세요."
            }
            code={error.digest ? `ref: ${error.digest}` : undefined}
          >
            <button className="btn btn-primary" type="button" onClick={reset}>
              <RefreshCwIcon aria-hidden="true" />
              다시 시도
            </button>
          </StateBox>
        </div>
      </div>
    </main>
  );
}
