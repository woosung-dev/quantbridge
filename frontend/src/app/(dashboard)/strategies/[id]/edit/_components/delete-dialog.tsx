"use client";

// Sprint 7c T5: 2-phase 삭제 다이얼로그 — confirm → archive-fallback.
// DELETE 409 (`strategy_has_backtests`) 감지 시 archive 제안으로 phase 전환.
// Sprint FE-E: <768px 에서 bottom sheet 로 자동 전환 (thumb-reach 최적화).

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
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { useMediaQuery } from "@/hooks/use-media-query";
import { useDeleteStrategy, useUpdateStrategy } from "@/features/strategy/hooks";
import { isStrategyHasBacktestsError } from "@/features/strategy/utils";

type DeleteDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  strategyId: string;
  strategyName: string;
  onDone: () => void;
  onArchived: () => void;
};

type Phase = "confirm" | "archive-fallback";

type BodyProps = {
  phase: Phase;
  strategyName: string;
  deleteIsPending: boolean;
  archiveIsPending: boolean;
  onCancel: () => void;
  onDelete: () => void;
  onArchive: () => void;
  // thumb-reach: 하단 시트에서는 컬럼 스택 + 주 동작이 아래.
  // 데스크톱 Dialog 는 row 푸터 (기존 동작 유지).
  variant: "sheet" | "dialog";
};

function Body({
  phase,
  strategyName,
  deleteIsPending,
  archiveIsPending,
  onCancel,
  onDelete,
  onArchive,
  variant,
}: BodyProps) {
  const HeaderEl = variant === "sheet" ? SheetHeader : DialogHeader;
  const TitleEl = variant === "sheet" ? SheetTitle : DialogTitle;
  const DescriptionEl = variant === "sheet" ? SheetDescription : DialogDescription;
  const FooterEl = variant === "sheet" ? SheetFooter : DialogFooter;

  if (phase === "confirm") {
    return (
      <>
        <HeaderEl>
          <TitleEl>&ldquo;{strategyName}&rdquo;를 삭제할까요?</TitleEl>
          <DescriptionEl>
            되돌릴 수 없습니다. 이 전략과 연관된 백테스트가 있으면 삭제 대신 보관을 제안합니다.
          </DescriptionEl>
        </HeaderEl>
        <FooterEl>
          <Button variant="ghost" onClick={onCancel}>
            취소
          </Button>
          <Button variant="destructive" disabled={deleteIsPending} onClick={onDelete}>
            {deleteIsPending ? "삭제 중..." : "삭제"}
          </Button>
        </FooterEl>
      </>
    );
  }

  return (
    <>
      <HeaderEl>
        <TitleEl>삭제할 수 없습니다</TitleEl>
        <DescriptionEl>
          이 전략에 연관된 백테스트가 있습니다. 대신 <strong>보관</strong>하면 목록에서
          숨기지만 백테스트 기록은 유지됩니다.
        </DescriptionEl>
      </HeaderEl>
      <FooterEl>
        <Button variant="ghost" onClick={onCancel}>
          취소
        </Button>
        <Button disabled={archiveIsPending} onClick={onArchive}>
          {archiveIsPending ? "보관 중..." : "보관"}
        </Button>
      </FooterEl>
    </>
  );
}

export function DeleteDialog(props: DeleteDialogProps) {
  const [phase, setPhase] = useState<Phase>("confirm");
  const isMobile = useMediaQuery("(max-width: 767px)");
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

  const handleOpenChange = (open: boolean) => {
    props.onOpenChange(open);
    if (!open) setPhase("confirm");
  };

  const body = (
    <Body
      phase={phase}
      strategyName={props.strategyName}
      deleteIsPending={del.isPending}
      archiveIsPending={update.isPending}
      onCancel={() => props.onOpenChange(false)}
      onDelete={() => del.mutate(props.strategyId)}
      onArchive={() => update.mutate({ is_archived: true })}
      variant={isMobile ? "sheet" : "dialog"}
    />
  );

  if (isMobile) {
    return (
      <Sheet open={props.open} onOpenChange={handleOpenChange}>
        <SheetContent>{body}</SheetContent>
      </Sheet>
    );
  }

  return (
    <Dialog open={props.open} onOpenChange={handleOpenChange}>
      <DialogContent>{body}</DialogContent>
    </Dialog>
  );
}
