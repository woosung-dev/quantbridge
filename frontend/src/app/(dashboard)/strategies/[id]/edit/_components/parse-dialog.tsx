"use client";

import { useMemo, useRef, useState } from "react";
import { ChevronLeftIcon, ChevronRightIcon, XIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { ParsePreviewResponse } from "@/features/strategy/schemas";
import { buildParseSteps, type ParseStep } from "./parse-dialog-steps";

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  result: ParsePreviewResponse;
  onSave: () => void;
};

export function ParseDialog({ open, onOpenChange, result, onSave }: Props) {
  const steps = useMemo(() => buildParseSteps(result), [result]);
  const [index, setIndex] = useState(0);
  const savedRef = useRef(false);

  // BUG-A 가드: index가 steps 길이를 초과하면 render에서 clamp.
  // NOTE: useEffect로 setIndex(0) 리셋은 result 참조가 살짝만 흔들려도 무한 렌더 루프를
  //       유발하므로 금지 (react-hooks/set-state-in-effect 경고 그대로 존중).
  //       result가 축소되면 clamp-only로 마지막 유효 step에 머물고, 사용자가 "이전" 또는
  //       모달 재오픈(resetOnOpen)으로 복귀. 계산상 UX 손실 적음, CPU 안정성 확보.
  const clampedIndex = Math.min(index, steps.length - 1);
  const step: ParseStep = steps[clampedIndex] ?? steps[0]!;
  const isFirst = clampedIndex === 0;
  const isLast = clampedIndex === steps.length - 1;

  const handleNext = () => setIndex((i) => Math.min(i + 1, steps.length - 1));
  const handlePrev = () => setIndex((i) => Math.max(i - 1, 0));
  const handleSave = () => {
    if (savedRef.current) return;
    savedRef.current = true;
    onSave();
    onOpenChange(false);
  };
  const handleReturn = () => onOpenChange(false);

  const resetOnOpen = (next: boolean) => {
    if (next) {
      setIndex(0);
      savedRef.current = false;
    }
    onOpenChange(next);
  };

  return (
    <Dialog open={open} onOpenChange={resetOnOpen}>
      <DialogContent className="w-[calc(100vw-2rem)] sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{renderTitle(step)}</DialogTitle>
          <DialogDescription>
            {clampedIndex + 1} / {steps.length} 단계
          </DialogDescription>
        </DialogHeader>
        <div className="py-3" aria-live="polite">
          <StepBody step={step} />
        </div>
        <DialogFooter className="gap-2">
          {isLast ? (
            <>
              <Button variant="ghost" onClick={handleReturn}>
                <XIcon className="mr-1 size-4" />
                닫기
              </Button>
              <Button
                onClick={handleSave}
                disabled={step.kind === "final" ? !step.canSave : false}
              >
                이 전략 저장
              </Button>
            </>
          ) : (
            <>
              <Button variant="ghost" onClick={handlePrev} disabled={isFirst}>
                <ChevronLeftIcon className="mr-1 size-4" />
                이전
              </Button>
              <Button onClick={handleNext}>
                다음
                <ChevronRightIcon className="ml-1 size-4" />
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function renderTitle(step: ParseStep): string {
  switch (step.kind) {
    case "intro":
      return "파싱 결과를 함께 살펴볼게요";
    case "error":
      return `에러 ${step.index + 1}/${step.total}`;
    case "warning":
      return `경고 ${step.index + 1}/${step.total}`;
    case "function":
      return `감지된 함수 ${step.index + 1}/${step.total}`;
    case "final":
      return step.canSave ? "저장할까요?" : "에러 해결 후 다시 시도";
  }
}

function StepBody({ step }: { step: ParseStep }) {
  switch (step.kind) {
    case "intro": {
      const { errorCount, warningCount, functionCount, pineVersion } = step.summary;
      return (
        <div className="space-y-2 text-sm">
          <p>
            Pine <Badge variant="secondary">{pineVersion}</Badge> 스크립트 파싱 결과:
          </p>
          <ul className="ml-4 list-disc space-y-1">
            <li>에러 {errorCount}건</li>
            <li>경고 {warningCount}건</li>
            <li>감지된 함수 {functionCount}개</li>
          </ul>
          <p className="text-xs text-[color:var(--text-muted)]">
            다음을 눌러 하나씩 확인해보세요.
          </p>
        </div>
      );
    }
    case "error":
      return (
        <div className="space-y-2 text-sm">
          <p className="font-mono text-xs">
            {step.error.line !== null && (
              <span className="mr-1">L{step.error.line}:</span>
            )}
            <span className="text-[color:var(--destructive)]">
              [{step.error.code}]
            </span>{" "}
            {step.error.message}
          </p>
          <p className="mt-2">
            <span className="font-bold">원인: </span>
            {step.advice.what}
          </p>
          <p>
            <span className="font-bold">조치: </span>
            {step.advice.action}
          </p>
        </div>
      );
    case "warning":
      return (
        <div className="space-y-2 text-sm">
          <p className="font-mono text-xs">{step.message}</p>
          <p>
            <span className="font-bold">원인: </span>
            {step.advice.what}
          </p>
          <p>
            <span className="font-bold">조치: </span>
            {step.advice.action}
          </p>
        </div>
      );
    case "function":
      return (
        <div className="space-y-2 text-sm">
          <p className="font-mono text-base">{step.name}</p>
          <p className="font-bold">{step.description.summary}</p>
          <p>{step.description.purpose}</p>
          {step.description.example && (
            <pre className="mt-2 overflow-x-auto rounded bg-[color:var(--bg-alt)] p-2 font-mono text-xs">
              {step.description.example}
            </pre>
          )}
        </div>
      );
    case "final": {
      if (!step.canSave) {
        const { errorCount } = step.summary;
        const msg =
          errorCount > 0
            ? `에러가 ${errorCount}건 있습니다. 코드로 돌아가 수정한 뒤 다시 시도해주세요.`
            : "이 스크립트는 지원되지 않는 기능을 포함하고 있어 저장할 수 없습니다. 코드를 수정한 뒤 다시 시도해주세요.";
        return <p className="text-sm">{msg}</p>;
      }
      return (
        <div className="space-y-2 text-sm">
          <p>파싱 결과를 확인하셨습니다. 이 전략을 저장할까요?</p>
          {step.hiddenFunctionCount > 0 && (
            <p className="text-xs text-[color:var(--text-muted)]">
              (총 {step.summary.functionCount}개 중 {step.hiddenFunctionCount}개는 요약에서 생략)
            </p>
          )}
        </div>
      );
    }
  }
}
