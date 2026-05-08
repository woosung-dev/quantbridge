"use client";

// Kill Switch 2단계 확인 모달 — INTERACTION_SPEC.md §03 의무 (Sprint 43-W12).
// 1단계: danger 경고 + 청산 영향 명시 + "다음" 버튼.
// 2단계: 사용자가 "KILL" 정확히 타이핑해야 실행 활성화 + 감사 로그 메시지.
// prototype 03 dark `.btn-kill` (rgba(248,113,113,0.3) shadow) → light `var(--destructive)` 솔리드.
//
// 내부 단계/입력 상태는 ModalBody (open=true 일 때만 mount) 안에 캡슐화.
// 모달이 닫히면 base-ui Dialog 가 unmount → state 자동 초기화 (effect-set-state 회피).

import { useEffect, useId, useState } from "react";
import { ShieldAlert, Square } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface KillSwitchModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  // 부모가 실제 청산 API 호출 + 감사 로그 기록을 책임 (props 분리로 모달은 UI 만).
  onConfirm: () => Promise<void> | void;
  isExecuting?: boolean;
  activeSessionsCount?: number;
}

const REQUIRED_PHRASE = "KILL";

export function KillSwitchModal({
  open,
  onOpenChange,
  onConfirm,
  isExecuting = false,
  activeSessionsCount = 0,
}: KillSwitchModalProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        {open ? (
          <ModalBody
            onCancel={() => onOpenChange(false)}
            onConfirm={onConfirm}
            isExecuting={isExecuting}
            activeSessionsCount={activeSessionsCount}
          />
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

function ModalBody({
  onCancel,
  onConfirm,
  isExecuting,
  activeSessionsCount,
}: {
  onCancel: () => void;
  onConfirm: () => Promise<void> | void;
  isExecuting: boolean;
  activeSessionsCount: number;
}) {
  const [step, setStep] = useState<1 | 2>(1);
  const [typed, setTyped] = useState("");
  const inputId = useId();

  // 2단계 진입 시 입력 필드 자동 포커스 (외부 시스템 = DOM 동기화, setState 없음).
  useEffect(() => {
    if (step !== 2) return;
    const timer = setTimeout(() => {
      const el = document.getElementById(inputId);
      if (el instanceof HTMLInputElement) el.focus();
    }, 50);
    return () => clearTimeout(timer);
  }, [step, inputId]);

  const isPhraseMatch = typed === REQUIRED_PHRASE;

  const handleConfirm = async () => {
    if (!isPhraseMatch || isExecuting) return;
    await onConfirm();
  };

  return (
    <>
      <DialogHeader>
        <div className="flex items-center gap-3">
          <span
            className="grid size-10 shrink-0 place-items-center rounded-[var(--radius-md)] bg-[color:var(--destructive-light)] text-[color:var(--destructive)]"
            aria-hidden="true"
          >
            <ShieldAlert className="size-5" />
          </span>
          <DialogTitle className="text-[color:var(--destructive)]">
            긴급 정지 — 전체 청산
          </DialogTitle>
        </div>
        <DialogDescription className="pt-2 text-[color:var(--text-muted)]">
          {step === 1
            ? `현재 활성 세션 ${activeSessionsCount}개의 모든 포지션을 시장가로 즉시 청산하고, 모든 봇을 강제 중지합니다. 이 작업은 되돌릴 수 없으며 감사 로그에 기록됩니다.`
            : "확인을 위해 아래 입력란에 정확히 'KILL' 을 타이핑하세요. 30초 쿨다운이 적용됩니다."}
        </DialogDescription>
      </DialogHeader>

      {step === 2 ? (
        <div className="space-y-2 pt-1">
          <label
            htmlFor={inputId}
            className="text-sm font-medium text-[color:var(--foreground)]"
          >
            확인 문구 입력
          </label>
          <Input
            id={inputId}
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
            placeholder="KILL"
            autoComplete="off"
            spellCheck={false}
            data-testid="kill-confirm-input"
            aria-label="KILL 확인 문구 입력"
            className="font-mono uppercase tracking-[0.3em]"
          />
          <p
            className="font-mono text-xs text-[color:var(--text-muted)]"
            aria-live="polite"
          >
            {isPhraseMatch
              ? "확인 완료 — 실행 가능"
              : "정확히 'KILL' 을 입력하세요"}
          </p>
        </div>
      ) : null}

      <DialogFooter className="gap-2">
        <Button
          type="button"
          variant="outline"
          onClick={onCancel}
          disabled={isExecuting}
        >
          취소
        </Button>
        {step === 1 ? (
          <Button
            type="button"
            variant="destructive"
            onClick={() => setStep(2)}
            data-testid="kill-step1-next"
          >
            다음 — 확인 단계
          </Button>
        ) : (
          <Button
            type="button"
            variant="destructive"
            onClick={handleConfirm}
            disabled={!isPhraseMatch || isExecuting}
            data-testid="kill-confirm-execute"
            className="gap-2"
          >
            <Square className="size-3.5" aria-hidden="true" />
            {isExecuting ? "실행 중..." : "KILL ALL 실행"}
          </Button>
        )}
      </DialogFooter>
    </>
  );
}
