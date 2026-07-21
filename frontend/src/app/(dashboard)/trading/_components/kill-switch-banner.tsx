"use client";

// 킬 스위치 경고 배너 — C 디자인 언어 이식 (S8). S7 이 /dashboard 에서 useKillSwitchEvents
// 경고 노출을 제거했으므로 안전 경고가 사라지지 않게 /trading 코크핏 최상단에서 재도입한다.
// - KS API 오류 → 황색 경고 배너(ks-error-banner)
// - active 이벤트 존재 → destructive 배너(ks-active-banner) + trigger 라벨 목록
// - active 없음 → 미렌더 (정상 상태는 §02 킬 스위치 패널이 담당)

import { AlertTriangleIcon, ShieldAlertIcon } from "lucide-react";

import { KILL_SWITCH_LABEL } from "@/features/trading/labels";
import { useKillSwitchEvents } from "@/features/trading";

// trigger_type → 한국어 레이블. 알 수 없는 값이면 원문 그대로 (fallback).
const KS_TRIGGER_LABELS: Record<string, string> = {
  daily_loss: "일일 손실 한도 초과",
  cumulative_loss: "누적 손실 한도 초과",
  api_error: "거래소 API 오류",
};

export function KillSwitchBanner() {
  const { data, isError } = useKillSwitchEvents();

  // KS API 자체 오류 → 황색 경고.
  if (isError) {
    return (
      <div
        role="alert"
        aria-live="assertive"
        data-testid="ks-error-banner"
        className="ks-banner ks-banner-warn"
      >
        <span className="ks-banner-icon" aria-hidden="true">
          <AlertTriangleIcon />
        </span>
        <p className="ks-banner-body">
          {KILL_SWITCH_LABEL.feature} 상태를 불러오지 못했습니다. 주문 실행 전 상태를 확인하세요.
        </p>
      </div>
    );
  }

  if (!data) return null;

  const activeEvents = data.items.filter((e) => !e.resolved_at);
  if (activeEvents.length === 0) return null;

  return (
    <div
      role="alert"
      aria-live="assertive"
      data-testid="ks-active-banner"
      className="ks-banner ks-banner-danger"
    >
      <span className="ks-banner-icon" aria-hidden="true">
        <ShieldAlertIcon />
      </span>
      <div className="ks-banner-main">
        <p className="ks-banner-title">
          {KILL_SWITCH_LABEL.feature} 활성. 자동 주문이 중지됩니다.
        </p>
        <ul className="ks-banner-list mono">
          {activeEvents.map((e) => (
            <li key={e.id}>
              <span className="ks-banner-trigger">
                {KS_TRIGGER_LABELS[e.trigger_type] ?? e.trigger_type}
              </span>
              <span className="dim">
                {" "}
                ({e.trigger_value} / {e.threshold})
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
