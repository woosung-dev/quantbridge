// 폼 422/4xx/5xx 에러를 inline 카드로 표준 표시하는 공통 컴포넌트.
// backtest-form 의 unsupported_builtins + friendly_message 카드 패턴을 추출 (Sprint 41 E).
// 다른 폼 (test-order, exchange-account 등) 에서도 ApiError 를 그대로 넘겨 재사용.
// Sprint 44 W C3: icon (warning/error) + 간격 정합 + slide-down entrance (qb-form-slide-down 200ms).
// pine-compat-experiment: indicatorCode prop 추가 — unsupported 케이스에 AI 변환 CTA 노출.

import Link from "next/link";
import { TriangleAlertIcon, OctagonXIcon } from "lucide-react";

import { ConvertWithAIButton } from "@/features/backtest/components/ConvertWithAIButton";
import type { ConvertIndicatorResponse } from "@/features/backtest/schemas";

import {
  getUnsupportedBuiltinHints,
  type UnsupportedBuiltinHint,
} from "@/lib/unsupported-builtin-hints";
import { cn } from "@/lib/utils";

export type FormErrorInlineProps = {
  /** ApiError 또는 어떤 unknown 에러. null/undefined 면 렌더 X. */
  error?: unknown;
  /** "ADR-003 supported list 참조 — strategy 편집" 링크 노출용 (unsupported_builtins case). */
  editStrategyHref?: string | null;
  /** data-testid 접두어 (default = "form-error"). 기존 testid 보존용. */
  testIdPrefix?: string;
  className?: string;
  /** Pine Script 소스 코드. 지정 시 unsupported 카드에 AI 변환 CTA 노출. */
  indicatorCode?: string | null;
  /** AI 변환 성공 콜백. indicatorCode 지정 시 필수. */
  onConverted?: (result: ConvertIndicatorResponse) => void;
};

type Parsed = {
  kind: "unsupported" | "general";
  friendlyMessage: string | null;
  hints: UnsupportedBuiltinHint[];
  fallbackMessage: string;
};

function parseError(err: unknown): Parsed | null {
  if (err == null) return null;

  // 문자열 메시지 단독 케이스.
  if (typeof err === "string" && err.length > 0) {
    return {
      kind: "general",
      friendlyMessage: null,
      hints: [],
      fallbackMessage: err,
    };
  }

  // duck-typing: ApiError 인스턴스 + Object.assign(new Error, {status, detail}) 둘 다 허용.
  // (테스트 페이로드 호환 + production ApiError 호환)
  if (typeof err !== "object") return null;
  const errObj = err as { status?: unknown; detail?: unknown; message?: unknown };
  const status = typeof errObj.status === "number" ? errObj.status : null;
  const message =
    typeof errObj.message === "string" && errObj.message.length > 0
      ? errObj.message
      : null;
  const fallback = message || (status != null ? `요청 실패 (${status})` : "요청 실패");

  if (status === 422) {
    // ApiError.detail = readErrorBody 결과 = { detail: { code, detail, unsupported_builtins, friendly_message } }.
    const detailBag = errObj.detail as
      | {
          detail?: {
            unsupported_builtins?: unknown;
            degraded_calls?: unknown;
            friendly_message?: unknown;
          };
        }
      | undefined;
    const inner = detailBag?.detail;
    const list = inner?.unsupported_builtins ?? inner?.degraded_calls;
    const fm =
      inner && typeof inner.friendly_message === "string" && inner.friendly_message.length > 0
        ? inner.friendly_message
        : null;
    if (
      Array.isArray(list) &&
      list.length > 0 &&
      list.every((x) => typeof x === "string")
    ) {
      return {
        kind: "unsupported",
        friendlyMessage: fm,
        hints: getUnsupportedBuiltinHints(list as string[]),
        fallbackMessage: fallback,
      };
    }
    return {
      kind: "general",
      friendlyMessage: fm,
      hints: [],
      fallbackMessage: fm ?? fallback,
    };
  }

  // status 없음 + Error 인스턴스 → message 추출, 그 외 → null.
  if (status == null && !(err instanceof Error)) return null;

  return {
    kind: "general",
    friendlyMessage: null,
    hints: [],
    fallbackMessage: fallback,
  };
}

export function FormErrorInline({
  error,
  editStrategyHref,
  testIdPrefix = "form-error",
  className,
  indicatorCode,
  onConverted,
}: FormErrorInlineProps) {
  const parsed = parseError(error);
  if (!parsed) return null;

  if (parsed.kind === "unsupported") {
    return (
      <div
        role="alert"
        data-testid={`${testIdPrefix}-unsupported-card`}
        className={cn(
          "qb-form-slide-down overflow-hidden rounded-md border border-amber-300 bg-amber-50 p-3 text-sm dark:border-amber-700 dark:bg-amber-950",
          className,
        )}
      >
        <div className="mb-1 flex items-start gap-2">
          <TriangleAlertIcon
            aria-hidden="true"
            className="mt-0.5 size-4 shrink-0 text-amber-700 dark:text-amber-300"
          />
          <p className="font-semibold leading-snug text-amber-900 dark:text-amber-200">
            이 strategy 는 미지원 builtin 을 포함합니다
          </p>
        </div>
        {parsed.friendlyMessage ? (
          <p
            className="mb-2 pl-6 text-xs leading-relaxed text-amber-900 dark:text-amber-200"
            data-testid={`${testIdPrefix}-friendly-message`}
          >
            {parsed.friendlyMessage}
          </p>
        ) : null}
        <ul className="list-inside list-disc space-y-1 pl-6 text-xs leading-relaxed text-amber-800 dark:text-amber-300">
          {parsed.hints.map((h) => (
            <li key={h.name}>
              <span className="font-mono">{h.name}</span> — {h.hint}
            </li>
          ))}
        </ul>
        <div className="mt-2 ml-6 flex flex-wrap items-center gap-2">
          {editStrategyHref ? (
            <Link
              href={editStrategyHref}
              className="inline-block text-xs text-amber-900 underline transition-opacity duration-150 hover:opacity-80 dark:text-amber-200"
              data-testid={`${testIdPrefix}-edit-strategy-link`}
            >
              ADR-003 supported list 참조 — strategy 편집 →
            </Link>
          ) : null}
          {indicatorCode && onConverted ? (
            <ConvertWithAIButton
              indicatorCode={indicatorCode}
              onConverted={onConverted}
            />
          ) : null}
        </div>
      </div>
    );
  }

  return (
    <p
      className={cn(
        "qb-form-slide-down flex items-start gap-1.5 text-sm leading-snug text-destructive",
        className,
      )}
      role="alert"
      data-testid={`${testIdPrefix}-server-error`}
    >
      <OctagonXIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
      <span>{parsed.fallbackMessage}</span>
    </p>
  );
}
