"use client";

// Sprint 26 — Live Sessions list + Stop confirm dialog.
// Sprint 33 BL-174 list-only — Empty/Failed/Loading state 통일 (LiveSessionStateView).

import { useState } from "react";
import { AlertCircle, Loader2, Plus } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

import {
  useDeactivateLiveSession,
  useLiveSessionState,
  useLiveSessions,
} from "../hooks";
import { LIVE_SESSION_STATUS_LABEL } from "../labels";
import type { LiveSession } from "../schemas";
import { formatDateTime, formatRealizedPnl } from "../utils";
import { LiveSessionStateView } from "./live-session-state-view";
import { SessionEndedReason } from "./session-ended-reason";

type Props = {
  onSelect?: (session: LiveSession) => void;
  selectedId?: string | null;
};

export function LiveSessionList({ onSelect, selectedId }: Props) {
  const { data, isLoading, error } = useLiveSessions(true);
  const deactivate = useDeactivateLiveSession();
  const [confirmId, setConfirmId] = useState<string | null>(null);

  if (isLoading) {
    return (
      <LiveSessionStateView
        icon={Loader2}
        iconClassName="animate-spin"
        title="로드 중"
        description="라이브 세션 목록을 불러오는 중..."
        testId="live-session-loading"
      />
    );
  }
  if (error) {
    return (
      <LiveSessionStateView
        icon={AlertCircle}
        variant="destructive"
        title="로드 실패"
        description={`라이브 세션 목록 로드 실패: ${error.message}`}
        testId="live-session-error"
      />
    );
  }

  const items = data?.items ?? [];
  const active = items.filter((s) => s.is_active);
  const inactive = items.filter((s) => !s.is_active);

  const handleStop = async () => {
    if (!confirmId) return;
    try {
      await deactivate.mutateAsync(confirmId);
      toast.success("Session 중단됨");
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Stop 실패",
      );
    } finally {
      setConfirmId(null);
    }
  };

  return (
    <>
      {active.length === 0 ? (
        <LiveSessionStateView
          icon={Plus}
          title="활성 세션이 없습니다."
          description="위 폼으로 새 세션을 시작하세요."
          testId="live-session-empty"
        />
      ) : (
        <ul className="space-y-2" data-testid="live-session-list">
          {active.map((s) => (
            <li
              key={s.id}
              className={`flex flex-col gap-1 rounded-md border p-3 sm:flex-row sm:items-center sm:justify-between ${
                selectedId === s.id ? "border-primary" : ""
              }`}
              data-testid={`live-session-${s.id}`}
            >
              <button
                type="button"
                onClick={() => onSelect?.(s)}
                className="text-left"
              >
                <span className="block font-medium">{s.symbol}</span>
                <p className="text-xs text-muted-foreground">
                  {s.interval} · 생성 {formatDateTime(s.created_at)}
                </p>
                <SessionPnlBadge sessionId={s.id} isActive={s.is_active} />
              </button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setConfirmId(s.id)}
                disabled={deactivate.isPending}
                data-testid={`live-session-stop-${s.id}`}
              >
                Stop
              </Button>
            </li>
          ))}
        </ul>
      )}

      <section className="mt-4 border-t pt-4" data-testid="recent-inactive-live-sessions">
        <h4 className="text-sm font-medium">최근 종료된 세션</h4>
        <p className="mt-1 text-xs text-muted-foreground">
          종료된 세션을 선택하면 실행 이력과 성과 대조를 확인할 수 있습니다.
        </p>
        {inactive.length === 0 ? (
          <p className="mt-3 text-sm text-muted-foreground" data-testid="recent-inactive-empty">
            최근 종료된 세션이 없습니다.
          </p>
        ) : (
          <ul className="mt-3 space-y-2" data-testid="recent-inactive-list">
            {inactive.map((s) => (
              <li
                key={s.id}
                className={`flex flex-col gap-1 rounded-md border border-dashed bg-muted/40 p-3 ${
                  selectedId === s.id ? "border-primary" : ""
                }`}
                data-testid={`inactive-live-session-${s.id}`}
              >
                <button type="button" onClick={() => onSelect?.(s)} className="text-left">
                  <span className="flex flex-wrap items-center gap-2 font-medium">
                    {s.symbol}
                    <span className="rounded-sm bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
                      {LIVE_SESSION_STATUS_LABEL.ended.label}
                    </span>
                    <SessionEndedReason
                      reason={s.deactivated_reason}
                      testId={`inactive-live-session-reason-${s.id}`}
                    />
                  </span>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {s.interval} · 종료 {formatDateTime(s.deactivated_at)}
                  </p>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <Dialog
        open={confirmId !== null}
        onOpenChange={(o: boolean) => {
          if (!o) setConfirmId(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>라이브 세션 중단</DialogTitle>
            <DialogDescription>
              이 session 의 자동 trading 이 중단됩니다. 미체결 주문은
              유지됩니다 (수동으로 cancel 또는 close 해주세요).
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setConfirmId(null)}>
              취소
            </Button>
            <Button
              variant="destructive"
              onClick={handleStop}
              disabled={deactivate.isPending}
            >
              중단
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

// 세션별 실현손익 배지 — useLiveSessionState 재사용(queryKey 공유 → 추가 네트워크 0).
// 활성 세션 행에서만 쓰므로 항상 enabled. LESSON-004: primitive dep 전달.
function SessionPnlBadge({
  sessionId,
  isActive,
}: {
  sessionId: string;
  isActive: boolean;
}) {
  const { data: state, isLoading } = useLiveSessionState(sessionId, isActive);
  if (isLoading || !state) {
    return null;
  }
  const { text, tone } = formatRealizedPnl(state.total_realized_pnl);
  const toneClass =
    tone === "profit"
      ? "text-[color:var(--success)]"
      : tone === "loss"
        ? "text-[color:var(--destructive)]"
        : "text-muted-foreground";
  return (
    <p className="mt-1 flex items-center gap-2 font-mono text-xs">
      <span className="text-muted-foreground">PnL</span>
      <span className={toneClass}>{text}</span>
      <span className="text-muted-foreground">
        · {state.total_closed_trades} 청산
      </span>
    </p>
  );
}
