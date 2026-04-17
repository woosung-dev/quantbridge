"use client";

// Sprint 7c T5: 2-phase 삭제 다이얼로그 — confirm → archive-fallback.
// DELETE 409 (`strategy_has_backtests`) 감지 시 archive 제안으로 phase 전환.

import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useDeleteStrategy, useUpdateStrategy } from "@/features/strategy/hooks";
import { isStrategyHasBacktestsError } from "@/features/strategy/utils";

export function DeleteDialog(props: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  strategyId: string;
  strategyName: string;
  onDone: () => void;
  onArchived: () => void;
}) {
  const [phase, setPhase] = useState<"confirm" | "archive-fallback">("confirm");
  const del = useDeleteStrategy({
    onSuccess: props.onDone,
    onError: (err) => {
      if (isStrategyHasBacktestsError(err)) {
        setPhase("archive-fallback");
      }
    },
  });
  const update = useUpdateStrategy(props.strategyId, {
    onSuccess: props.onArchived,
  });

  return (
    <Dialog
      open={props.open}
      onOpenChange={(o) => {
        props.onOpenChange(o);
        if (!o) setPhase("confirm");
      }}
    >
      <DialogContent>
        {phase === "confirm" ? (
          <>
            <DialogHeader>
              <DialogTitle>&ldquo;{props.strategyName}&rdquo;를 삭제할까요?</DialogTitle>
              <DialogDescription>
                되돌릴 수 없습니다. 이 전략과 연관된 백테스트가 있으면 삭제 대신 보관을 제안합니다.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="ghost" onClick={() => props.onOpenChange(false)}>
                취소
              </Button>
              <Button
                variant="destructive"
                disabled={del.isPending}
                onClick={() => del.mutate(props.strategyId)}
              >
                {del.isPending ? "삭제 중..." : "삭제"}
              </Button>
            </DialogFooter>
          </>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>삭제할 수 없습니다</DialogTitle>
              <DialogDescription>
                이 전략에 연관된 백테스트가 있습니다. 대신 <strong>보관</strong>하면
                목록에서 숨기지만 백테스트 기록은 유지됩니다.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="ghost" onClick={() => props.onOpenChange(false)}>
                취소
              </Button>
              <Button
                disabled={update.isPending}
                onClick={() => update.mutate({ is_archived: true })}
              >
                {update.isPending ? "보관 중..." : "보관"}
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
