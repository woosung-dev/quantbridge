// Sprint 7c T4 Step 1 — 입력 방식 선택.
// Pass 4 AI Slop #2: symmetric 3-card grid → asymmetric 1 primary full-card + 2 chip row.
// Sprint 42-polish W3: prototype 07 매칭 — MethodTabs (직접/파일/URL) 상단 탭 추가.
// Sprint 44 W F2: primary card hover translate-y / chip subtle hover / "다음 단계" press feedback.

import { CodeIcon, UploadIcon, LinkIcon, ChevronRightIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { MethodTabs } from "./method-tabs";

export function StepMethod(props: {
  method: "direct" | "upload" | "url";
  onMethodChange: (m: "direct" | "upload" | "url") => void;
  onNext: () => void;
}) {
  return (
    <div>
      <h2 className="mb-1 font-display text-lg font-semibold">어떻게 전략을 등록할까요?</h2>
      <p className="mb-4 text-xs text-[color:var(--text-muted)]">
        현재는 직접 입력만 지원합니다.
      </p>

      {/* prototype 07: 입력 방식 탭 (직접만 활성) */}
      <div className="mb-5">
        <MethodTabs value={props.method} onChange={props.onMethodChange} />
      </div>

      {/* Active 옵션: full-width primary card — Sprint 44 W F2: hover -translate-y + shadow ramp */}
      <button
        type="button"
        onClick={() => props.onMethodChange("direct")}
        aria-pressed={props.method === "direct"}
        className="group flex w-full items-center gap-4 rounded-[var(--radius-md)] border-2 border-[color:var(--primary)] bg-[color:var(--primary-light)] p-5 text-left transition-[border-color,box-shadow,transform] duration-200 ease-out hover:border-[color:var(--primary-hover)] motion-safe:hover:-translate-y-px hover:shadow-[0_4px_14px_rgba(37,99,235,0.10)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--primary)]/25"
      >
        <CodeIcon className="size-8 text-[color:var(--primary)]" strokeWidth={1.5} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="break-keep font-semibold text-[color:var(--text-primary)]">
              Pine Script 직접 입력
            </span>
            <Badge variant="secondary" className="text-[0.65rem]">권장</Badge>
          </div>
          <p className="mt-0.5 break-keep text-xs text-[color:var(--text-secondary)]">
            TradingView에서 코드를 복사해 붙여넣습니다. 실시간 파싱으로 즉시 확인.
          </p>
        </div>
        <ChevronRightIcon className="size-5 text-[color:var(--primary)] transition group-hover:translate-x-0.5" />
      </button>

      {/* Disabled 옵션: 1줄 chip row */}
      <div className="mt-4 flex flex-wrap items-center gap-2 text-xs text-[color:var(--text-muted)]">
        <span>곧 지원:</span>
        <span className="inline-flex items-center gap-1 rounded-full border border-[color:var(--border)] px-2 py-1">
          <UploadIcon className="size-3" />.pine 파일 업로드
        </span>
        <span className="inline-flex items-center gap-1 rounded-full border border-[color:var(--border)] px-2 py-1">
          <LinkIcon className="size-3" />TradingView URL
        </span>
        <span className="text-[0.65rem] opacity-70">Sprint 7d+</span>
      </div>

      <div className="mt-8 flex justify-end">
        <Button onClick={props.onNext}>다음 단계 →</Button>
      </div>
    </div>
  );
}
