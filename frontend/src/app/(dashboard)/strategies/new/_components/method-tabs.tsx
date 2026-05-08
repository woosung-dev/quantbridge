// 전략 입력 방식 탭 — 직접 / 파일 / URL (Sprint 42-polish W3-fidelity + Sprint 44 W F2)
// shadcn `<Tabs>` 의 `line` variant 가 `flex-1` + `after:bottom-[-5px]` 강제로 prototype 의
// content-width 탭 + `border-bottom: 2px solid primary` underline 과 비주얼 mismatch 발생.
// fidelity 우선 → raw <button role="tab"> + Tailwind 직접 underline 으로 교체 (shadcn fallback).
// prototype 07: `.method-tabs` 컨테이너 `border-bottom: 1px solid border` + 각 탭 hover/active
// `border-bottom: 2px solid primary`. disabled 탭은 opacity 0.55 + cursor-not-allowed.
// Sprint 44 W F2: underline indicator 200ms ease-out + hover 시 underline preview (primary/30).

"use client";

import { CodeIcon, UploadIcon, LinkIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export type StrategyInputMethod = "direct" | "upload" | "url";

interface MethodTabsProps {
  value: StrategyInputMethod;
  onChange: (value: StrategyInputMethod) => void;
}

const TAB_OPTIONS: ReadonlyArray<{
  value: StrategyInputMethod;
  label: string;
  icon: typeof CodeIcon;
  enabled: boolean;
}> = [
  { value: "direct", label: "Pine Script 직접 입력", icon: CodeIcon, enabled: true },
  { value: "upload", label: "파일 업로드", icon: UploadIcon, enabled: false },
  { value: "url", label: "TV URL 가져오기", icon: LinkIcon, enabled: false },
] as const;

export function MethodTabs({ value, onChange }: MethodTabsProps) {
  return (
    <div
      role="tablist"
      aria-label="입력 방식 선택"
      className="flex gap-1 border-b border-[color:var(--border)]"
    >
      {TAB_OPTIONS.map((tab) => {
        const Icon = tab.icon;
        const isActive = value === tab.value;
        const isDisabled = !tab.enabled;
        return (
          <button
            key={tab.value}
            type="button"
            role="tab"
            aria-selected={isActive}
            aria-disabled={isDisabled}
            disabled={isDisabled}
            onClick={() => {
              if (!isDisabled) onChange(tab.value);
            }}
            className={cn(
              // prototype 07 method-tab base + Sprint 44 W F2: indicator slide + hover underline preview
              "-mb-px inline-flex items-center gap-2 px-[18px] py-3 text-sm transition-[color,border-color] duration-200 ease-out",
              "border-b-2 border-transparent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--primary)]/20 focus-visible:rounded-sm",
              isActive
                ? "cursor-pointer border-[color:var(--primary)] font-semibold text-[color:var(--primary)] hover:text-[color:var(--primary-hover)]"
                : "font-medium text-[color:var(--text-muted)] hover:border-[color:var(--primary)]/30 hover:text-[color:var(--text-secondary)]",
              isDisabled && "cursor-not-allowed opacity-55 hover:border-transparent hover:text-[color:var(--text-muted)]",
            )}
          >
            <Icon className="size-3.5 shrink-0" aria-hidden />
            <span>{tab.label}</span>
          </button>
        );
      })}
    </div>
  );
}
