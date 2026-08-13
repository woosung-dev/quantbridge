// Precision Instrument 시그니처 — 계측 눈금(tick ruler) 장식 컴포넌트 + 섹션 경계 룰
//
// 렌더는 globals.css 의 .qb-ruler-x/-y 2층 repeating-gradient. 순수 장식이라
// aria-hidden 고정. 남용 금지 — 섹션 헤더/키 스탯 스트립 등 구조적 경계에만.

import { cn } from "@/lib/utils";

type TickRulerProps = {
  orientation?: "horizontal" | "vertical";
  className?: string;
};

export function TickRuler({
  orientation = "horizontal",
  className,
}: TickRulerProps) {
  return (
    <div
      aria-hidden="true"
      data-slot="tick-ruler"
      className={cn(
        orientation === "horizontal" ? "qb-ruler-x w-full" : "qb-ruler-y h-full",
        className,
      )}
    />
  );
}

type SectionRuleProps = {
  /** mono uppercase 터미널 레이블. 생략 시 눈금만. */
  label?: string;
  className?: string;
};

/** 섹션 헤더 경계 — mono 레이블 + 우측으로 흐르는 계측 눈금. */
export function SectionRule({ label, className }: SectionRuleProps) {
  return (
    <div className={cn("flex items-end gap-3", className)}>
      {label && (
        <span className="font-mono text-[11px] font-medium tracking-[0.14em] text-muted-foreground uppercase">
          {label}
        </span>
      )}
      <TickRuler className="mb-[3px] min-w-0 flex-1" />
    </div>
  );
}
