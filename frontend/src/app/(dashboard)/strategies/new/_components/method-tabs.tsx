// 전략 입력 방식 탭 — 직접 / 파일 / URL (Sprint 42-polish W3)
// shadcn `<Tabs>` line variant wrapper. 직접만 활성, 나머지는 disabled chip 으로 표시.
// prototype 07: bottom-border underline 활성 표시 + disabled 탭은 흐리게.

"use client";

import { CodeIcon, UploadIcon, LinkIcon } from "lucide-react";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

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
    <Tabs
      value={value}
      onValueChange={(next) => {
        if (typeof next === "string" && (next === "direct" || next === "upload" || next === "url")) {
          onChange(next);
        }
      }}
      className="w-full"
    >
      <TabsList
        variant="line"
        aria-label="입력 방식 선택"
        className="w-full justify-start gap-1 border-b border-[color:var(--border)] bg-transparent p-0"
      >
        {TAB_OPTIONS.map((tab) => {
          const Icon = tab.icon;
          return (
            <TabsTrigger
              key={tab.value}
              value={tab.value}
              disabled={!tab.enabled}
              aria-disabled={!tab.enabled}
              className="h-auto flex-none px-4 py-3 text-sm data-active:font-semibold data-active:text-[color:var(--primary)] data-active:after:bg-[color:var(--primary)] data-active:after:opacity-100"
            >
              <Icon className="size-3.5" aria-hidden />
              <span>{tab.label}</span>
            </TabsTrigger>
          );
        })}
      </TabsList>
    </Tabs>
  );
}
