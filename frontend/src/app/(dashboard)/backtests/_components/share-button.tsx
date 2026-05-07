"use client";
// 백테스트 결과 공유 link 생성·복사·revoke 버튼 — Sprint 41 Worker H

import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  useCreateBacktestShare,
  useRevokeBacktestShare,
} from "@/features/backtest/hooks";

interface ShareButtonProps {
  backtestId: string;
  isEnabled?: boolean; // false 시 disabled (예: queued/running)
}

/**
 * 공유 버튼 — 클릭 시 share_token 발급 + clipboard 복사 + sonner toast.
 * 상태 머신:
 *   idle → click → 토큰 fetch → window.location.origin + path 복사 → "공유 중" 표시
 *   "공유 중" → 취소 → revoke + toast → "공유" 로 복귀
 *
 * LESSON-004/005/006 정합: useState 만 사용, queryKey 안 inline 객체 X.
 */
export function ShareButton({ backtestId, isEnabled = true }: ShareButtonProps) {
  // sharedUrl null = 미생성. NOT null = 활성 share — "취소" 버튼 노출.
  const [sharedUrl, setSharedUrl] = useState<string | null>(null);

  const createShare = useCreateBacktestShare({
    onSuccess: (data) => {
      const fullUrl =
        typeof window !== "undefined"
          ? `${window.location.origin}${data.share_url_path}`
          : data.share_url_path;
      setSharedUrl(fullUrl);
      // clipboard 복사 — 실패해도 toast 는 url 노출 (사용자 manual copy 가능)
      if (typeof navigator !== "undefined" && navigator.clipboard) {
        navigator.clipboard
          .writeText(fullUrl)
          .then(() => {
            toast.success("공유 링크가 복사되었습니다", {
              description: fullUrl,
            });
          })
          .catch(() => {
            toast.success("공유 링크가 생성되었습니다", {
              description: fullUrl,
            });
          });
      } else {
        toast.success("공유 링크가 생성되었습니다", { description: fullUrl });
      }
    },
    onError: (err) => {
      toast.error("공유 링크 생성에 실패했습니다", {
        description: err.message,
      });
    },
  });

  const revokeShare = useRevokeBacktestShare({
    onSuccess: () => {
      setSharedUrl(null);
      toast.success("공유 링크가 해제되었습니다");
    },
    onError: (err) => {
      toast.error("공유 해제에 실패했습니다", { description: err.message });
    },
  });

  const handleCreate = () => createShare.mutate(backtestId);
  const handleRevoke = () => revokeShare.mutate(backtestId);

  if (sharedUrl) {
    return (
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground">공유 중</span>
        <Button
          variant="outline"
          size="sm"
          onClick={handleRevoke}
          disabled={revokeShare.isPending}
        >
          {revokeShare.isPending ? "해제 중…" : "공유 취소"}
        </Button>
      </div>
    );
  }

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={handleCreate}
      disabled={!isEnabled || createShare.isPending}
    >
      {createShare.isPending ? "생성 중…" : "공유"}
    </Button>
  );
}
