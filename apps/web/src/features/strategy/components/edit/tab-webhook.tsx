"use client";

// Webhook 관리 — C 디자인 언어 이식 (screen-08 보존 기능). 프로토타입 screen-08 은 webhook 을
// 그리지 않지만, 생성 직후 1회 노출되는 secret 표시와 rotate 는 실기능이라 C 카드로 보존한다.
// secret 은 sessionStorage(external store)로만 수명 관리한다(LESSON-004, useSyncExternalStore).

import { useState, useSyncExternalStore } from "react";
import { CheckIcon, CopyIcon, EyeOffIcon, RefreshCwIcon, TriangleAlertIcon } from "lucide-react";
import { toast } from "sonner";

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
import { getWebhookBaseUrl } from "@/lib/webhook-base";

type TabWebhookProps = {
  strategyId: string;
};

function buildWebhookUrl(strategyId: string): string {
  const { url } = getWebhookBaseUrl();
  return `${url}/api/v1/webhooks/${strategyId}?token={HMAC}`;
}

export function TabWebhook({ strategyId }: TabWebhookProps) {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const displayedSecret = useSyncExternalStore<string | null>(
    subscribeWebhookSecret,
    () => readWebhookSecret(strategyId),
    () => null,
  );
  const [copiedField, setCopiedField] = useState<"url" | "secret" | null>(null);

  const webhookUrl = buildWebhookUrl(strategyId);

  const rotate = useRotateWebhookSecret(strategyId, {
    onSuccess: () => {
      setConfirmOpen(false);
      toast.success("새 webhook secret 을 발급했습니다");
    },
    onError: (err) => toast.error(`회전 실패: ${err.message}`),
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
  };

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <h3 className="card-title">Webhook</h3>
          <p className="card-sub">
            TradingView alert 또는 외부 시스템이 이 URL 로 신호를 보냅니다.
          </p>
        </div>
      </div>
      <div className="card-body">
        <div className="field">
          <span className="field-label">Webhook URL</span>
          <div className="webhook-row">
            <code className="webhook-code">{webhookUrl}</code>
            <button
              className="btn btn-ghost btn-xs"
              type="button"
              aria-label="URL 복사"
              onClick={() => handleCopy(webhookUrl, "url")}
            >
              {copiedField === "url" ? (
                <CheckIcon aria-hidden="true" />
              ) : (
                <CopyIcon aria-hidden="true" />
              )}
              복사
            </button>
          </div>
          <span className="field-hint">
            {`{HMAC}`} 자리에는 secret 과 body 로 만든 HMAC-SHA256 토큰을 채웁니다. URL 이 외부에
            노출됐다면 즉시 secret 을 회전하세요.
          </span>
        </div>

        {displayedSecret ? (
          <div className="webhook-secret" data-testid="webhook-secret-amber-card">
            <p className="webhook-secret-warn">
              <TriangleAlertIcon aria-hidden="true" />이 secret 은 한 번만 표시됩니다. 닫으면 다시
              조회할 수 없습니다.
            </p>
            <div className="webhook-row">
              <code className="webhook-code" data-testid="webhook-secret-plaintext">
                {displayedSecret}
              </code>
              <button
                className="btn btn-ghost btn-xs"
                type="button"
                aria-label="Secret 복사"
                onClick={() => handleCopy(displayedSecret, "secret")}
              >
                {copiedField === "secret" ? (
                  <CheckIcon aria-hidden="true" />
                ) : (
                  <CopyIcon aria-hidden="true" />
                )}
                복사
              </button>
              <button
                className="btn btn-ghost btn-xs"
                type="button"
                aria-label="Secret 숨기기"
                onClick={handleHideSecret}
              >
                <EyeOffIcon aria-hidden="true" />
                숨기기
              </button>
            </div>
          </div>
        ) : (
          <p className="field-hint" style={{ marginTop: "16px" }}>
            Secret 값은 발급이나 회전 직후에만 한 번 표시됩니다. 외부 webhook 에 다시 등록하려면
            아래에서 회전하세요.
          </p>
        )}

        <div className="form-actions">
          <button
            className="btn"
            type="button"
            onClick={() => setConfirmOpen(true)}
            disabled={rotate.isPending}
            aria-label="webhook secret 회전"
          >
            <RefreshCwIcon aria-hidden="true" />
            Secret 회전
          </button>
        </div>
      </div>

      {/* 회전 확인 Dialog */}
      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Webhook Secret 회전</DialogTitle>
            <DialogDescription>
              기존 secret 은 5분 유예 뒤 무효화됩니다. TradingView 등 외부 webhook 의 secret 도 함께
              다시 설정해야 합니다.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <button className="btn btn-ghost" type="button" onClick={() => setConfirmOpen(false)}>
              취소
            </button>
            <button
              className="btn btn-primary"
              type="button"
              onClick={() => rotate.mutate()}
              disabled={rotate.isPending}
              aria-label="회전 확정"
            >
              {rotate.isPending ? "회전 중" : "확정"}
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
