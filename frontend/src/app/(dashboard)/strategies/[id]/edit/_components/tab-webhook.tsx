"use client";

// Sprint 13 Phase A.2: Strategy Webhook 패널 — Webhook URL 표시 + Secret Rotate UI.
//
// dogfood Day 1 발견 — webhook 외부 등록 + secret 표시 UI 부재로 dogfood 사용자가
// trading 시작 entry 자체 못 잡음. 이 탭이 정식 entry 추가.
//
// Sprint 6 broken bug fix 후 (BE WebhookSecretService.rotate() 가 commit 호출),
// rotate 응답의 plaintext 가 실제로 DB 영구 저장됨. frontend 가 sessionStorage 캐시.
//
// LESSON-004 준수: rotate response data 를 useEffect dep 로 사용 X — onSuccess 콜백
// 직접 처리 (cacheWebhookSecret + setState scalar).

import { useState, useSyncExternalStore } from "react";
import { CheckIcon, CopyIcon, EyeOffIcon, RefreshCwIcon, TriangleAlertIcon } from "lucide-react";
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
import { useRotateWebhookSecret } from "@/features/strategy/hooks";
import {
  clearWebhookSecret,
  readWebhookSecret,
  subscribeWebhookSecret,
} from "@/features/strategy/webhook-secret-storage";
import { getApiBase } from "@/lib/api-base";

type TabWebhookProps = {
  strategyId: string;
};

function buildWebhookUrl(strategyId: string): string {
  // Phase B 가 token (HMAC-SHA256 hex) 을 동적으로 추가. 표시용 URL 은 placeholder.
  // Sprint 14 Phase B-3 — getApiBase helper 통합 (3 곳 일관성).
  return `${getApiBase()}/api/v1/webhooks/${strategyId}?token={HMAC}`;
}

export function TabWebhook({ strategyId }: TabWebhookProps) {
  const [confirmOpen, setConfirmOpen] = useState(false);
  // Sprint 14 Phase A — useSyncExternalStore 패턴 (Day 2 Pain #2 hydration race fix).
  // sessionStorage 를 external store 로 추상화 — server snapshot 은 항상 null (SSR
  // 단계 prerender 가 amber card 미렌더 보장), client snapshot 은 mount 후 read.
  // cacheWebhookSecret/clearWebhookSecret 가 notify() 호출하면 구독 컴포넌트 자동
  // re-render → rotate / hide / 다른 탭 변경에도 반응. LESSON-004 의
  // react-hooks/set-state-in-effect 차단을 회피 (React 공식 external state hook).
  const displayedSecret = useSyncExternalStore<string | null>(
    subscribeWebhookSecret,
    () => readWebhookSecret(strategyId),
    () => null,
  );
  const [copiedField, setCopiedField] = useState<"url" | "secret" | null>(null);

  const webhookUrl = buildWebhookUrl(strategyId);

  const rotate = useRotateWebhookSecret(strategyId, {
    onSuccess: () => {
      // hooks.ts onSuccess 가 cacheWebhookSecret 호출 → notify() →
      // useSyncExternalStore 가 새 snapshot 읽어 자동 re-render. setState 불필요.
      setConfirmOpen(false);
      toast.success("새 webhook secret 발급됨");
    },
    onError: (err) => {
      toast.error(`Rotate 실패: ${err.message}`);
    },
  });

  const handleCopy = async (text: string, field: "url" | "secret") => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(field);
      setTimeout(() => setCopiedField(null), 2000);
    } catch {
      toast.error("클립보드 복사 실패");
    }
  };

  const handleHideSecret = () => {
    clearWebhookSecret(strategyId);
    // notify() → useSyncExternalStore 가 새 snapshot 읽어 null 반영, amber card 자동 사라짐.
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Webhook URL Card */}
      <section className="rounded-[var(--radius-lg)] border border-[color:var(--border)] bg-[color:var(--bg-alt)] p-5">
        <h2 className="font-display text-base font-semibold">Webhook URL</h2>
        <p className="mt-1 text-xs text-[color:var(--text-muted)]">
          TradingView alert 또는 외부 시스템에서 이 URL 로 webhook 발송. {`{HMAC}`} 자리에는
          HMAC-SHA256 hex 토큰 (secret + body) 을 채워야 합니다.
        </p>
        <div className="mt-3 flex items-center gap-2">
          <code className="flex-1 break-all rounded-md bg-[color:var(--bg-primary)] px-3 py-2 font-mono text-xs">
            {webhookUrl}
          </code>
          <Button
            variant="outline"
            size="icon"
            aria-label="URL 복사"
            onClick={() => handleCopy(webhookUrl, "url")}
          >
            {copiedField === "url" ? (
              <CheckIcon className="size-4 text-[color:var(--success)]" />
            ) : (
              <CopyIcon className="size-4" />
            )}
          </Button>
        </div>
        <p className="mt-3 flex items-start gap-1.5 text-xs text-[color:var(--text-muted)]">
          <TriangleAlertIcon className="mt-0.5 size-3.5 flex-shrink-0 text-[color:var(--warning)]" />
          외부에 URL 이 노출됐다면 즉시 secret rotation 필수.
        </p>
      </section>

      {/* Secret Card */}
      <section className="rounded-[var(--radius-lg)] border border-[color:var(--border)] bg-[color:var(--bg-alt)] p-5">
        <h2 className="font-display text-base font-semibold">Webhook Secret</h2>

        {displayedSecret ? (
          <div
            data-testid="webhook-secret-amber-card"
            className="mt-3 rounded-md border border-amber-300 bg-amber-50 p-4 dark:border-amber-700 dark:bg-amber-950/40"
          >
            <p className="flex items-start gap-1.5 text-xs font-medium text-amber-900 dark:text-amber-200">
              <TriangleAlertIcon className="mt-0.5 size-4 flex-shrink-0" />
              이 secret 은 한 번만 표시됩니다. 닫으면 다시 조회할 수 없습니다.
            </p>
            <div className="mt-3 flex items-center gap-2">
              <code
                data-testid="webhook-secret-plaintext"
                className="flex-1 break-all rounded-md bg-white px-3 py-2 font-mono text-xs dark:bg-amber-900/20"
              >
                {displayedSecret}
              </code>
              <Button
                variant="outline"
                size="icon"
                aria-label="Secret 복사"
                onClick={() => handleCopy(displayedSecret, "secret")}
              >
                {copiedField === "secret" ? (
                  <CheckIcon className="size-4 text-[color:var(--success)]" />
                ) : (
                  <CopyIcon className="size-4" />
                )}
              </Button>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Secret 숨기기"
                onClick={handleHideSecret}
              >
                <EyeOffIcon className="size-4" />
              </Button>
            </div>
          </div>
        ) : (
          <p className="mt-2 text-xs text-[color:var(--text-muted)]">
            Secret 값은 발급/회전 직후에만 1회 표시됩니다. 외부 webhook 에 다시 등록하려면
            아래 버튼으로 회전하세요.
          </p>
        )}

        <div className="mt-4 flex justify-end">
          <Button
            variant="outline"
            onClick={() => setConfirmOpen(true)}
            disabled={rotate.isPending}
            aria-label="webhook secret 회전"
          >
            <RefreshCwIcon className="size-4" />
            Secret Rotate
          </Button>
        </div>
      </section>

      {/* Rotate Confirm Dialog */}
      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Webhook Secret 회전</DialogTitle>
            <DialogDescription>
              기존 secret 은 5분 grace period 후 무효화됩니다. TradingView 등 외부 webhook 의
              secret 도 함께 재설정 필수입니다.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setConfirmOpen(false)}>
              취소
            </Button>
            <Button
              onClick={() => rotate.mutate()}
              disabled={rotate.isPending}
              aria-label="rotate 확정"
            >
              {rotate.isPending ? "회전 중..." : "확정"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
