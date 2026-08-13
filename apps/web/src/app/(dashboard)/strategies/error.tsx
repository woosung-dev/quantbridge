"use client";

// 전략 라우트 에러 바운더리 — C 디자인 언어(screen-06) StateBox. Next.js App Router 규약.
// prefetch/streaming 중 throw된 에러를 이 경계에서 포착.

import { useEffect } from "react";
import { AlertTriangleIcon, RefreshCwIcon } from "lucide-react";

import { StateBox } from "@/components/state-box";

export default function StrategiesError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[StrategiesError]", error);
  }, [error]);

  return (
    <main className="page">
      <section className="card">
        <div className="card-body">
          <StateBox
            tone="failed"
            testId="strategies-route-error"
            icon={<AlertTriangleIcon />}
            title="전략 목록을 불러오지 못했습니다."
            body="네트워크 또는 인증 문제가 있을 수 있습니다."
            code={error.digest ? `ref: ${error.digest}` : undefined}
          >
            <button className="btn btn-ghost" type="button" onClick={reset}>
              <RefreshCwIcon aria-hidden="true" />
              다시 시도
            </button>
          </StateBox>
        </div>
      </section>
    </main>
  );
}
