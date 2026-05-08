// 공유 링크 URL 복사 버튼 — 외부 viewer 가 share link 을 다른 사람에게 재전달할 수 있도록
"use client";

import { useState } from "react";
import { toast } from "sonner";

/**
 * 현재 페이지 URL (즉 share/backtests/[token]) 을 클립보드에 복사하는 client 버튼.
 *
 * - 1.6초 동안 check icon stagger 로 시각 피드백
 * - sonner toast 동시 노출 (description = 복사된 URL)
 * - clipboard API 미지원 / 거부 시 toast.error fallback
 * - server token 보안 로직과는 분리 (URL 만 복사, token revoke 검증은 서버 측 유지)
 */
export function ShareCopyLinkButton() {
  const [hasCopied, setHasCopied] = useState(false);

  const handleCopy = async () => {
    if (typeof window === "undefined") return;
    const url = window.location.href;
    try {
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(url);
        toast.success("링크가 복사되었습니다", { description: url });
        setHasCopied(true);
        window.setTimeout(() => setHasCopied(false), 1600);
        return;
      }
      throw new Error("clipboard unavailable");
    } catch {
      toast.error("자동 복사를 못 했습니다", { description: url });
    }
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      data-testid="share-copy-link-button"
      data-copied={hasCopied || undefined}
      aria-label={hasCopied ? "링크 복사 완료" : "공유 링크 복사"}
      className="inline-flex h-8 items-center gap-1.5 rounded-md border border-[color:var(--border)] bg-white px-3 text-xs font-medium text-[color:var(--text-secondary)] shadow-sm transition-all duration-200 ease-out hover:-translate-y-px hover:border-[color:var(--primary)] hover:text-[color:var(--primary)] hover:shadow-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--primary)] data-[copied]:border-[color:var(--success)] data-[copied]:text-[color:var(--success)]"
    >
      {hasCopied ? (
        <>
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            aria-hidden="true"
            className="motion-safe:animate-[copySuccess_280ms_cubic-bezier(0.34,1.56,0.64,1)_both]"
          >
            <polyline points="20 6 9 17 4 12" />
          </svg>
          복사됨
        </>
      ) : (
        <>
          <svg
            width="13"
            height="13"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden="true"
          >
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
          </svg>
          링크 복사
        </>
      )}
    </button>
  );
}
