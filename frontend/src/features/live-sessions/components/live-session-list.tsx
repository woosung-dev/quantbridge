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

import { useDeactivateLiveSession, useLiveSessions } from "../hooks";
import type { LiveSession } from "../schemas";
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
        description="Live Session 목록을 불러오는 중..."
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
        description={`Live Session 목록 로드 실패: ${error.message}`}
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
        title="활성 Live Session 이 없습니다"
        description="위 form 으로 새 session 을 시작하세요."
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
              <h3 className="font-medium">{s.symbol}</h3>
              <p className="text-xs text-muted-foreground">
                {s.interval} · created: {new Date(s.created_at).toLocaleString()}
              </p>
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
            <DialogTitle>Live Session 중단</DialogTitle>
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
