"use client";
// 503 점검 페이지의 "다시 시도" 버튼 — 정적 라우트라 리로드로 헬스 상태를 다시 확인한다.
// 자동 재시도는 없고 사용자가 눌러야 재요청한다(§4.7 · screen-13 503 규약). page.tsx 는
// 서버 컴포넌트로 유지하고 상호작용만 이 말단 클라이언트 컴포넌트로 분리한다.

import { RefreshCwIcon } from "lucide-react";

export function MaintenanceRetryButton() {
  return (
    <button
      type="button"
      className="btn btn-primary"
      data-testid="maintenance-retry-button"
      onClick={() => window.location.reload()}
    >
      <RefreshCwIcon aria-hidden="true" />
      다시 시도
    </button>
  );
}
