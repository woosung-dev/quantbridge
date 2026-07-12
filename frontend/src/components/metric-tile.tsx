// 지표 타일 공통 프리미티브 — uppercase label + mono tabular value(tone) + 선택 sub.
// 페이지마다 StatCard/MetricCard/SummaryMetric 으로 재구현되던 shape 의 SSOT (Skeleton BL-206 전례).
// 구조가 다른 타일(아이콘/live 도트/strip 셀 등)은 흡수 대상이 아니다 — 억지 통합 금지.

import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export type MetricTileTone = "pos" | "neg" | "warn" | "neutral";

const TONE_CLASSES: Record<MetricTileTone, string> = {
  // 금융 양수/음수는 차트와 동일한 bullish/bearish 토큰으로 통일.
  pos: "text-bullish",
  neg: "text-bearish",
  warn: "text-[color:var(--warning)]",
  neutral: "text-foreground",
};

const SIZE_CLASSES = {
  xs: "text-base",
  sm: "text-lg",
  md: "text-xl",
  lg: "text-2xl",
} as const;

export interface MetricTileProps {
  label: string;
  value: ReactNode;
  /** 값 아래 보조 텍스트. */
  sub?: ReactNode;
  tone?: MetricTileTone;
  /** 값 폰트 크기 — 기본 md(text-xl). */
  size?: keyof typeof SIZE_CLASSES;
  /** card = 테두리 카드(기본) / bare = 컨테이너 스타일 없음(호출측 레이아웃 안에 배치). */
  variant?: "card" | "bare";
  /** 값 요소 data-testid — 기존 사이트별 테스트 셀렉터 유지용. */
  valueTestId?: string;
  /** 컨테이너 추가 클래스 (entrance 애니메이션 등). */
  className?: string;
}

export function MetricTile({
  label,
  value,
  sub,
  tone = "neutral",
  size = "md",
  variant = "card",
  valueTestId,
  className,
}: MetricTileProps) {
  return (
    <div
      className={cn(
        variant === "card" && "rounded-lg border bg-card px-4 py-3",
        className,
      )}
    >
      <div className="font-mono text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
        {label}
      </div>
      <div
        className={cn(
          "font-mono font-bold leading-tight tabular-nums",
          SIZE_CLASSES[size],
          TONE_CLASSES[tone],
        )}
        data-testid={valueTestId}
      >
        {value}
      </div>
      {sub ? (
        <div className="mt-1 text-xs text-muted-foreground">{sub}</div>
      ) : null}
    </div>
  );
}
