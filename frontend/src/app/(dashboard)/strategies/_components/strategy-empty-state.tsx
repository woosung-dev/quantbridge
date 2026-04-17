import Link from "next/link";
import { CodeIcon, PlusIcon } from "lucide-react";
import { Button } from "@/components/ui/button";

export function StrategyEmptyState() {
  return (
    <div className="mx-auto max-w-md rounded-[var(--radius-lg)] border border-dashed border-[color:var(--border-dark)] bg-white p-10 text-center">
      <div className="mx-auto mb-4 grid size-14 place-items-center rounded-full bg-[color:var(--primary-light)] text-[color:var(--primary)]">
        <CodeIcon className="size-7" strokeWidth={1.5} />
      </div>
      <h2 className="font-display text-lg font-semibold text-[color:var(--text-primary)]">
        첫 전략을 만들어보세요
      </h2>
      <p className="mt-2 text-sm text-[color:var(--text-secondary)]">
        TradingView에서 작성한 Pine Script를 붙여넣거나, 미리 준비된 템플릿에서 시작할 수 있습니다.
      </p>
      <div className="mt-6 flex justify-center gap-2">
        <Button render={<Link href="/strategies/new" />}>
          <PlusIcon className="size-4" />새 전략 만들기
        </Button>
        <Button variant="outline" disabled>템플릿 둘러보기 (Sprint 7d+)</Button>
      </div>
    </div>
  );
}
