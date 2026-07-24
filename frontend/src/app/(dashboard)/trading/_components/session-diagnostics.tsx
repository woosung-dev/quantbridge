"use client";

// 코크핏 §08의 알림 규칙·실시간 스트림 진단을 실제 계약으로 렌더한다.
import { useState, type ReactNode } from "react";
import {
  AlertTriangleIcon,
  BellIcon,
  ClockIcon,
  RefreshCwIcon,
  WifiIcon,
} from "lucide-react";

import { StateBox } from "@/components/state-box";
import { AlertRuleForm } from "@/features/alert-rules/components/alert-rule-form";
import { formatThresholdPercent } from "@/features/alert-rules/format";
import { useAlertRules, useDeactivateAlertRule } from "@/features/alert-rules/hooks";
import type { AlertRule, AlertRuleType } from "@/features/alert-rules/schemas";
import type { LiveSession } from "@/features/live-sessions/schemas";
import {
  selectLastRealtimeEventTs,
  selectRealtimeStatus,
  useRealtimeStore,
} from "@/features/realtime/store";

export type DiagnosticState = "loading" | "error" | "empty" | "ok";

const STATE_ARIA: Record<DiagnosticState, string> = {
  loading: "불러오는 중",
  error: "불러오기 실패",
  empty: "비어 있음",
  ok: "정상",
};

const RULE_TYPE_LABEL: Record<AlertRuleType, string> = {
  loss_limit: "손실 한도",
  watchdog: "워치독",
};

export interface DiagnosticCardProps {
  title: string;
  subtitle: string;
  state: DiagnosticState;
  heading: string;
  body: string;
  /** error 상태에서 노출하는 실제 엔드포인트 + 상태코드. */
  code?: string;
  /** error/empty/ok 상태 아이콘. */
  icon: ReactNode;
  /** 상태 설명 아래에 두는 실제 동작 버튼 또는 인라인 폼. */
  action?: ReactNode;
}

/** 4상태(로딩/에러/빈/정상)를 렌더하는 진단 카드 프리미티브. */
export function DiagnosticCard({
  title,
  subtitle,
  state,
  heading,
  body,
  code,
  icon,
  action,
}: DiagnosticCardProps) {
  return (
    <article
      className="card diag"
      aria-label={`${title}, ${STATE_ARIA[state]}`}
      aria-busy={state === "loading" || undefined}
      data-testid={`diag-${state}`}
    >
      <div className="card-head">
        <div>
          <h3 className="card-title">{title}</h3>
          <p className="card-sub">{subtitle}</p>
        </div>
      </div>
      <div className="card-body">
        {state === "loading" ? (
          <>
            <div className="sk" style={{ height: 96 }} aria-hidden="true" />
            <div className="sk sk-line" style={{ width: "72%" }} aria-hidden="true" />
            <p className="state-note">
              <ClockIcon aria-hidden="true" />
              {body}
            </p>
          </>
        ) : (
          <StateBox
            tone={state === "error" ? "failed" : "neutral"}
            icon={state === "error" ? <AlertTriangleIcon /> : icon}
            title={heading}
            body={body}
            code={state === "error" && code ? code : undefined}
          >
            {action}
          </StateBox>
        )}
      </div>
    </article>
  );
}

function ruleSummary(rule: AlertRule): string {
  const threshold = rule.threshold_percent
    ? ` ${formatThresholdPercent(rule.threshold_percent)}%`
    : "";
  return `${RULE_TYPE_LABEL[rule.rule_type]}${threshold} · ${rule.channel}`;
}

function AlertRulesDiagnostic({ session }: { session: LiveSession | null }) {
  const [formOpen, setFormOpen] = useState(false);
  const rules = useAlertRules(session?.id ?? null);
  const deactivateRule = useDeactivateAlertRule(session?.id ?? "");

  if (!session) {
    return (
      <DiagnosticCard
        title="알림 규칙"
        subtitle="이 세션에만 적용됩니다."
        state="empty"
        icon={<BellIcon />}
        heading="알림 규칙을 기다리고 있습니다."
        body="세션을 선택하면 이 세션의 알림 규칙을 확인합니다."
      />
    );
  }
  if (rules.isLoading) {
    return (
      <DiagnosticCard
        title="알림 규칙"
        subtitle="이 세션에만 적용됩니다."
        state="loading"
        icon={<BellIcon />}
        heading="알림 규칙을 불러오는 중입니다."
        body="이 세션의 알림 규칙을 확인하고 있습니다."
      />
    );
  }
  if (rules.isError) {
    return (
      <DiagnosticCard
        title="알림 규칙"
        subtitle="이 세션에만 적용됩니다."
        state="error"
        icon={<BellIcon />}
        heading="알림 규칙을 불러오지 못했습니다."
        body="잠시 후 다시 시도해주세요."
        action={
          <button className="btn btn-ghost" type="button" onClick={() => void rules.refetch()}>
            <RefreshCwIcon aria-hidden="true" />
            다시 시도
          </button>
        }
      />
    );
  }
  const items = rules.data?.items ?? [];
  const activeRuleTypes = items.map((rule) => rule.rule_type);
  if (items.length === 0) {
    return (
      <DiagnosticCard
        title="알림 규칙"
        subtitle="이 세션에만 적용됩니다."
        state="empty"
        icon={<BellIcon />}
        heading="알림 규칙이 없습니다."
        body="손실 한도 접근이나 워치독 중단을 알림으로 받을 수 있습니다."
        action={
          <>
            <button
              className="btn btn-ghost"
              type="button"
              onClick={() => setFormOpen((open) => !open)}
            >
              {formOpen ? "알림 규칙 만들기 닫기" : "알림 규칙 만들기"}
            </button>
            {formOpen ? (
              <AlertRuleForm
                sessionId={session.id}
                activeRuleTypes={activeRuleTypes}
                onSuccess={() => setFormOpen(false)}
              />
            ) : null}
          </>
        }
      />
    );
  }
  return (
    <DiagnosticCard
      title="알림 규칙"
      subtitle="이 세션에만 적용됩니다."
      state="ok"
      icon={<BellIcon />}
      heading={`규칙 ${items.length}개 활성`}
      body="저장된 활성 규칙입니다."
      action={
        <div className="mt-3 space-y-2">
          {items.map((rule) => (
            <div className="flex items-center justify-between gap-2" key={rule.id}>
              <span>{ruleSummary(rule)}</span>
              <button
                className="btn btn-ghost"
                type="button"
                disabled={deactivateRule.isPending}
                onClick={() => deactivateRule.mutate(rule.id)}
              >
                해제
              </button>
            </div>
          ))}
          <button
            className="btn btn-ghost"
            type="button"
            onClick={() => setFormOpen((open) => !open)}
          >
            {formOpen ? "알림 규칙 만들기 닫기" : "알림 규칙 만들기"}
          </button>
          {formOpen ? (
            <AlertRuleForm
              sessionId={session.id}
              activeRuleTypes={activeRuleTypes}
              onSuccess={() => setFormOpen(false)}
            />
          ) : null}
        </div>
      }
    />
  );
}

function relativeEventTime(lastEventTs: number | null): string {
  if (lastEventTs === null) return "이벤트 대기 중";
  const seconds = Math.max(0, Math.floor(Date.now() / 1000) - lastEventTs);
  if (seconds < 60) return "방금 전 이벤트";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}분 전 이벤트`;
  return `${Math.floor(seconds / 3600)}시간 전 이벤트`;
}

function RealtimeDiagnostic() {
  const status = useRealtimeStore(selectRealtimeStatus);
  const lastEventTs = useRealtimeStore(selectLastRealtimeEventTs);
  const pollingNote = "폴링 스냅샷이 정합성 기준이며 스트림은 갱신 힌트입니다.";

  if (status === "authed") {
    return (
      <DiagnosticCard
        title="실시간 가격 스트림"
        subtitle="WebSocket 시세 구독"
        state="ok"
        icon={<WifiIcon />}
        heading="실시간 스트림 연결됨"
        body={`${relativeEventTime(lastEventTs)} · ${pollingNote}`}
      />
    );
  }
  if (status === "connecting") {
    return (
      <DiagnosticCard
        title="실시간 가격 스트림"
        subtitle="WebSocket 시세 구독"
        state="loading"
        icon={<WifiIcon />}
        heading="실시간 스트림에 연결하는 중입니다."
        body={`실시간 스트림에 연결하고 있습니다. ${pollingNote}`}
      />
    );
  }
  if (status === "closed") {
    return (
      <DiagnosticCard
        title="실시간 가격 스트림"
        subtitle="WebSocket 시세 구독"
        state="error"
        icon={<WifiIcon />}
        heading="실시간 스트림 연결이 끊겼습니다."
        body={pollingNote}
        action={
          <button className="btn btn-ghost" type="button" onClick={() => window.location.reload()}>
            페이지 새로고침
          </button>
        }
      />
    );
  }
  return (
    <DiagnosticCard
      title="실시간 가격 스트림"
      subtitle="WebSocket 시세 구독"
      state="empty"
      icon={<WifiIcon />}
      heading="실시간 스트림이 설정되지 않았습니다."
      body={`NEXT_PUBLIC_WS_URL을 설정하면 연결합니다. ${pollingNote}`}
    />
  );
}

/** 선택된 라이브 세션의 §08 진단 2종을 표시한다. */
export function SessionDiagnostics({ session }: { session: LiveSession | null }) {
  return (
    <div className="diag-row">
      <AlertRulesDiagnostic session={session} />
      <RealtimeDiagnostic />
    </div>
  );
}
