"use client";

// C-1: Kill Switch Active/Error 배너.
// - KS API 오류 → 황색 경고 배너
// - active 이벤트 존재 → destructive 배너 (주문 버튼 비활성화 연동은 OrdersPanel에서 처리)
// - active 없음 → 렌더 안 함

import { AlertTriangle, ShieldAlert } from "lucide-react";
import { useKillSwitchEvents } from "@/features/trading";

// trigger_type → 한국어 레이블 매핑.
// 알 수 없는 값이면 trigger_type 그대로 표시 (fallback).
const KS_TRIGGER_LABELS: Record<string, string> = {
  daily_loss: "일일 손실 한도 초과",
  cumulative_loss: "누적 손실 한도 초과",
  api_error: "거래소 API 오류",
};

export function KillSwitchBanner() {
  const { data, isError } = useKillSwitchEvents();

  // KS API 자체 오류 → 황색 경고
  if (isError) {
    return (
      <div
        role="alert"
        data-testid="ks-error-banner"
        className="flex items-center gap-2 rounded border border-yellow-500 bg-yellow-50 px-4 py-3 text-yellow-800 text-sm"
      >
        <AlertTriangle className="size-4 shrink-0" aria-hidden="true" />
        <span>Kill Switch 상태를 불러오지 못했습니다. 주문 실행 전 상태를 확인하세요.</span>
      </div>
    );
  }

  if (!data) return null;

  const activeEvents = data.items.filter((e) => !e.resolved_at);
  if (activeEvents.length === 0) return null;

  return (
    <div
      role="alert"
      data-testid="ks-active-banner"
      className="flex items-start gap-2 rounded border border-destructive bg-destructive/10 px-4 py-3 text-destructive text-sm"
    >
      <ShieldAlert className="size-4 shrink-0 mt-0.5" aria-hidden="true" />
      <div>
        <p className="font-semibold mb-1">Kill Switch 활성 — 자동 주문이 중지됩니다.</p>
        <ul className="space-y-0.5 list-disc list-inside">
          {activeEvents.map((e) => (
            <li key={e.id}>
              {KS_TRIGGER_LABELS[e.trigger_type] ?? e.trigger_type}
              {" "}
              ({e.trigger_value} / {e.threshold})
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

// KS 상태 기반 주문 버튼 비활성화 여부 hook.
// OrdersPanel / 주문 폼 등에서 임포트해서 사용.
export function useIsOrderDisabledByKs(): boolean {
  const { data, isError } = useKillSwitchEvents();
  if (isError) return true;
  if (!data) return false;
  return data.items.some((e) => !e.resolved_at);
}
