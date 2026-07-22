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
import type { LiveSession } from "../schemas";
import { formatDateTime, formatRealizedPnl } from "../utils";
import { LiveSessionStateView } from "./live-session-state-view";

type Props = {
  onSelect?: (session: LiveSession) => void;
  selectedId?: string | null;
};

export function LiveSessionList({ onSelect, selectedId }: Props) {
  const { data, isLoading, error } = useLiveSessions();
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

  if (active.length === 0) {
    return (
      <LiveSessionStateView
        icon={Plus}
        title="활성 세션이 없습니다."
        description="위 폼으로 새 세션을 시작하세요."
        testId="live-session-empty"
      />
    );
  }

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
// 리스트는 is_active 세션만 표시하므로 항상 enabled. LESSON-004: primitive dep 전달.
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
