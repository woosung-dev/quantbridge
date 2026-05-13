// 에디터 하단 파싱 결과 패널 — prototype 01 의 .bottom-panel + .bottom-tabs 1:1 (Sprint 43 W9-fidelity)
// 3 탭 (파싱 결과 / 문제 / 출력) underline + count badge + stagger entrance.
// W3 parse-result-panel 의 stagger animation/aria-live 정합.
"use client";

import { useState } from "react";
import { AlertCircleIcon, CheckCircle2Icon, TerminalIcon } from "lucide-react";

import type { ParsePreviewResponse } from "@/features/strategy/schemas";

type PanelTab = "result" | "problems" | "output";

export interface ParsePanelProps {
  result: ParsePreviewResponse | null;
  loading?: boolean;
}

export function ParsePanel({ result, loading = false }: ParsePanelProps) {
  const [tab, setTab] = useState<PanelTab>("result");

  const problemCount =
    (result?.unsupported_builtins?.length ?? 0) + (result?.errors?.length ?? 0);

  return (
    <section
      aria-label="파싱 결과 패널"
      aria-live="polite"
      className="flex flex-col rounded-[var(--radius-md,0.625rem)] border border-[color:var(--border)] bg-[#F8FAFC]"
      data-testid="parse-panel"
    >
      {/* prototype: bottom-tabs 38px / underline */}
      <div
        role="tablist"
        aria-label="파싱 패널 탭"
        className="flex h-[38px] shrink-0 items-stretch gap-0.5 border-b border-[color:var(--border)] bg-white px-4"
      >
        <PanelTabButton
          id="result"
          active={tab === "result"}
          onSelect={setTab}
          icon={<CheckCircle2Icon className="size-3.5" aria-hidden strokeWidth={2} />}
          label="파싱 결과"
        />
        <PanelTabButton
          id="problems"
          active={tab === "problems"}
          onSelect={setTab}
          icon={<AlertCircleIcon className="size-3.5" aria-hidden strokeWidth={2} />}
          label="문제"
          count={problemCount}
        />
        <PanelTabButton
          id="output"
          active={tab === "output"}
          onSelect={setTab}
          icon={<TerminalIcon className="size-3.5" aria-hidden strokeWidth={2} />}
          label="출력"
        />
      </div>

      <div role="tabpanel" className="min-h-[120px] flex-1 px-4 py-3">
        {tab === "result" && (
          <ResultBody result={result} loading={loading} />
        )}
        {tab === "problems" && <ProblemsBody result={result} />}
        {tab === "output" && <OutputBody />}
      </div>
    </section>
  );
}

interface PanelTabButtonProps {
  id: PanelTab;
  active: boolean;
  onSelect: (id: PanelTab) => void;
  icon: React.ReactNode;
  label: string;
  count?: number;
}

function PanelTabButton({
  id,
  active,
  onSelect,
  icon,
  label,
  count,
}: PanelTabButtonProps) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      data-state={active ? "active" : "inactive"}
      onClick={() => onSelect(id)}
      // prototype: border-bottom 2px transition + active blue
      className={
        "inline-flex min-h-[38px] items-center gap-1.5 border-b-2 px-3.5 text-[0.8125rem] font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--primary)]/40 " +
        (active
          ? "border-[color:var(--primary)] font-semibold text-[color:var(--primary)]"
          : "border-transparent text-[color:var(--text-secondary)] hover:text-[color:var(--text-primary)]")
      }
    >
      {icon}
      <span>{label}</span>
      {typeof count === "number" && count > 0 && (
        <span className="ml-1 rounded-full bg-[color:var(--bg-alt)] px-1.5 py-0.5 text-[0.6875rem] font-semibold text-[color:var(--text-secondary)]">
          {count}
        </span>
      )}
    </button>
  );
}

function ResultBody({
  result,
  loading,
}: {
  result: ParsePreviewResponse | null;
  loading: boolean;
}) {
  if (loading) {
    return (
      <p className="text-[0.8125rem] text-[color:var(--text-muted)]">파싱 중...</p>
    );
  }
  if (!result) {
    return (
      <p className="text-[0.8125rem] text-[color:var(--text-muted)]">
        코드 입력 후 파싱 결과가 표시됩니다.
      </p>
    );
  }

  const items: string[] = [
    `Pine Script ${result.pine_version} 감지 — ${STATUS_LABEL[result.status]}`,
    `${result.entry_count}개 진입 시그널 / ${result.exit_count}개 청산 시그널`,
    result.functions_used.length > 0
      ? `${result.functions_used.length}개 함수 사용: ${result.functions_used.slice(0, 3).join(", ")}`
      : "사용 함수 없음",
    result.is_runnable && result.unsupported_builtins.length === 0
      ? "백테스트 트랜스파일 준비 완료"
      : "미지원 함수가 있어 실행 불가",
  ];

  return (
    <ul className="m-0 flex list-none flex-col gap-1.5 p-0">
      {items.map((text, idx) => (
        <li
          key={text}
          data-testid="parse-panel-item"
          className="motion-safe:animate-[staggerIn_400ms_cubic-bezier(0.4,0,0.2,1)_forwards] flex items-baseline gap-2 text-[0.8125rem] text-[color:var(--text-primary)] opacity-0"
          style={{ animationDelay: `${(idx + 1) * 80}ms` }}
        >
          <span aria-hidden className="text-[color:var(--success)]">
            ✓
          </span>
          <span>{text}</span>
        </li>
      ))}
    </ul>
  );
}

function ProblemsBody({ result }: { result: ParsePreviewResponse | null }) {
  const problems = [
    ...(result?.errors ?? []).map((e) => ({
      kind: "error" as const,
      msg: e.line != null ? `${e.message} (L${e.line})` : e.message,
    })),
    ...(result?.unsupported_builtins ?? []).map((u) => ({
      kind: "unsupported" as const,
      msg: `미지원 함수: ${u}`,
    })),
  ];

  if (problems.length === 0) {
    return (
      <p className="text-[0.8125rem] text-[color:var(--text-muted)]">
        문제가 없습니다.
      </p>
    );
  }

  return (
    <ul className="m-0 flex list-none flex-col gap-1.5 p-0">
      {problems.map((p, idx) => (
        <li
          key={`${p.kind}-${idx}`}
          className="flex items-baseline gap-2 text-[0.8125rem]"
        >
          <span
            aria-hidden
            className={
              p.kind === "error"
                ? "text-[color:var(--destructive)]"
                : "text-[color:var(--warning)]"
            }
          >
            ●
          </span>
          <span className="text-[color:var(--text-primary)]">{p.msg}</span>
        </li>
      ))}
    </ul>
  );
}

function OutputBody() {
  return (
    <p className="font-mono text-[0.75rem] text-[color:var(--text-muted)]">
      출력 로그가 없습니다.
    </p>
  );
}

const STATUS_LABEL: Record<ParsePreviewResponse["status"], string> = {
  ok: "변환 가능",
  unsupported: "일부 미지원",
  error: "오류",
};
