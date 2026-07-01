// 코크핏 KPI 카드 — 좌측 톤 액센트 스트라이프 + mono 값 + footer 슬롯(P&L Tape 등)
"use client";

import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

type Tone = "primary" | "bullish" | "bearish" | "success" | "destructive" | "neutral";

const TONE_ACCENT: Record<Tone, string> = {
  primary: "before:bg-primary",
  bullish: "before:bg-bullish",
  bearish: "before:bg-bearish",
  success: "before:bg-success",
  destructive: "before:bg-destructive",
  neutral: "before:bg-border-dark",
};

const TONE_VALUE: Record<Tone, string> = {
  primary: "text-foreground",
  bullish: "text-bullish",
  bearish: "text-bearish",
  success: "text-success",
  destructive: "text-destructive",
  neutral: "text-foreground",
};

interface Props {
  label: string;
  value: ReactNode;
  tone?: Tone;
  icon?: ReactNode;
  sublabel?: string;
  live?: boolean;
  /** 카드 하단 슬롯 (P&L Tape 등). */
  footer?: ReactNode;
  className?: string;
}

export function CockpitKpiCard({
  label,
  value,
  tone = "neutral",
  icon,
  sublabel,
  live,
  footer,
  className,
}: Props) {
  return (
    <div
      className={cn(
        "qb-metric-card relative min-w-0 overflow-hidden rounded-[var(--radius-lg)] border border-border bg-card p-4 pl-5 shadow-card",
        "before:absolute before:inset-y-0 before:left-0 before:w-[3px]",
        TONE_ACCENT[tone],
        className,
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="truncate text-[0.7rem] font-semibold uppercase tracking-wide text-muted-foreground">
          {label}
        </span>
        {icon ? (
          <span className="text-muted-foreground" aria-hidden="true">
            {icon}
          </span>
        ) : null}
      </div>
      <p
        className={cn(
          "mt-2.5 font-mono text-[1.6rem] font-bold leading-none tabular-nums tracking-tight",
          TONE_VALUE[tone],
        )}
      >
        {value}
      </p>
      {sublabel ? (
        <p className="mt-2 flex items-center gap-1.5 font-mono text-[0.72rem] text-muted-foreground">
          {live ? (
            <span
              className="inline-block size-1.5 rounded-full bg-success shadow-[0_0_6px_var(--success)]"
              aria-hidden="true"
            />
          ) : null}
          {sublabel}
        </p>
      ) : null}
      {footer ? <div className="mt-3">{footer}</div> : null}
    </div>
  );
}
