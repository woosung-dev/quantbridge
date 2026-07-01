"use client";

// Kill Switch 배너 (Sprint 43-W12 polish — light 통일 + status pulse).
// - KS API 오류 → 황색 경고 배너 + warn pulse
// - active 이벤트 존재 → destructive 배너 + danger pulse + 강조 outline
// - active 없음 → 렌더 안 함 (정상 status 는 KPI 카드에서 표시)

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

  // KS API 자체 오류 → 황색 경고 (light 톤 + warn pulse)
  if (isError) {
    return (
      <div
        role="alert"
        aria-live="assertive"
        data-testid="ks-error-banner"
        className="flex items-center gap-3 rounded-[var(--radius-md)] border border-warning bg-warning-subtle px-4 py-3 text-sm text-warning shadow-card"
      >
        <span className="grid size-8 shrink-0 place-items-center rounded-md bg-warning/15 text-warning">
          <AlertTriangle className="size-4 animate-pulse" aria-hidden="true" />
        </span>
        <span className="font-medium">
          Kill Switch 상태를 불러오지 못했습니다. 주문 실행 전 상태를 확인하세요.
        </span>
      </div>
    );
  }

  if (!data) return null;

  const activeEvents = data.items.filter((e) => !e.resolved_at);
  if (activeEvents.length === 0) return null;

  // prototype 03 dark `rgba(248,113,113,0.08)` → light `var(--destructive-light)` (#FEE2E2)
  return (
    <div
      role="alert"
      aria-live="assertive"
      data-testid="ks-active-banner"
      className="relative flex items-start gap-3 overflow-hidden rounded-[var(--radius-md)] border border-destructive bg-destructive-light px-4 py-3 text-sm text-destructive shadow-card"
    >
      <span
        className="absolute inset-y-0 left-0 w-1 bg-destructive"
        aria-hidden="true"
      />
      <span className="grid size-9 shrink-0 place-items-center rounded-md bg-destructive/15">
        <ShieldAlert
          className="size-5 animate-pulse text-destructive"
          aria-hidden="true"
        />
      </span>
      <div className="min-w-0 flex-1">
        <p className="mb-1 font-semibold tracking-tight">
          Kill Switch 활성 — 자동 주문이 중지됩니다.
        </p>
        <ul className="list-inside list-disc space-y-0.5 font-mono text-xs">
          {activeEvents.map((e) => (
            <li key={e.id}>
              <span className="font-semibold">
                {KS_TRIGGER_LABELS[e.trigger_type] ?? e.trigger_type}
              </span>
              <span className="ml-1 text-destructive/80">
                ({e.trigger_value} / {e.threshold})
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
