"use client";

// 주문 목록 라우트 에러 경계 — 목록 내부 fetch 실패와 별개인 render 예외 안전망.

import { AlertTriangleIcon, RefreshCwIcon } from "lucide-react";

import { StateBox } from "@/components/state-box";

interface OrdersErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function OrdersError({ error, reset }: OrdersErrorProps) {
  return (
    <main className="page">
      <div className="card">
        <div className="card-body">
          <StateBox
            tone="failed"
            testId="orders-route-error"
            icon={<AlertTriangleIcon />}
            title="주문 원장을 표시하지 못했습니다."
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
