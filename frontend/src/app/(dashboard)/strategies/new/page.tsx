"use client";

// Sprint 7c T4: /strategies/new — 3-step wizard + localStorage draft 복원 Dialog.
// Sprint FE-C: Clerk userId 별 localStorage scoping — draft 가 계정 전환 시 누출되지 않도록.

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { toast } from "sonner";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useCreateStrategy } from "@/features/strategy/hooks";
import type {
  CreateStrategyRequest,
  ParsePreviewResponse,
} from "@/features/strategy/schemas";
import { handleMutationError } from "@/features/strategy/error-handler";
import {
  clearOtherUsersDrafts,
  clearWizardDraft,
  useAutoSaveDraft,
  useDraftSnapshot,
} from "@/features/strategy/draft";

import { WizardStepper } from "./_components/wizard-stepper";
import { StepMethod } from "./_components/step-method";
import { StepCode } from "./_components/step-code";
import { StepMetadata } from "./_components/step-metadata";

type Step = 1 | 2 | 3;
type Method = "direct" | "upload" | "url";

export default function NewStrategyPage() {
  const router = useRouter();
  const { userId } = useAuth();
  const [step, setStep] = useState<Step>(1);
  const [method, setMethod] = useState<Method>("direct");
  const [pineSource, setPineSource] = useState("");
  const [lastParse, setLastParse] = useState<ParsePreviewResponse | null>(null);

  // Draft 복원 — Sprint FE-C: setState-in-effect 없이 localStorage 를 render-time 에 derive.
  // LESSON-004 정책: react-hooks/set-state-in-effect 규칙은 disable 하지 않는다.
  const availableDraft = useDraftSnapshot(userId);
  const [promptDismissed, setPromptDismissed] = useState(false);
  const shouldPromptRestore =
    !promptDismissed &&
    availableDraft !== null &&
    (availableDraft.pineSource.trim().length > 0 || Boolean(availableDraft.metadata.name));

  // 계정 전환 대비 — 다른 userId 의 잔여 draft 를 best-effort 로 정리.
  useEffect(() => {
    if (!userId) return;
    clearOtherUsersDrafts(userId);
  }, [userId]);

  // auto-save (500ms debounce, primitive deps로 무한 루프 회피)
  useAutoSaveDraft(userId, {
    method,
    pineSource,
    metadata: {}, // Sprint 7c: form values는 persist하지 않음 (StepMetadata 내부 form 상태)
  });

  const create = useCreateStrategy();

  const handleSubmit = (meta: Omit<CreateStrategyRequest, "pine_source">) => {
    create.mutate(
      { ...meta, pine_source: pineSource },
      {
        onSuccess: (data) => {
          clearWizardDraft(userId);
          toast.success(`"${data.name}" 전략이 생성되었습니다`);
          // Sprint 14 Phase A C안: webhook tab 으로 직접 진입 — sessionStorage 캐시 된
          // 1회 표시 plaintext 가 EditorView 새 mount + TabWebhook useEffect read 로
          // 즉시 amber card 에 노출. 사용자가 webhook 탭 직접 클릭 안 해도 됨.
          router.push(`/strategies/${data.id}/edit?tab=webhook`);
        },
        onError: (err) => {
          handleMutationError(err);
        },
      },
    );
  };

  const handleRestore = () => {
    if (availableDraft) {
      setMethod(availableDraft.method);
      setPineSource(availableDraft.pineSource);
      setStep(availableDraft.pineSource.trim().length > 0 ? 2 : 1);
    }
    setPromptDismissed(true);
  };

  const handleDiscardDraft = () => {
    clearWizardDraft(userId);
    setPromptDismissed(true);
  };

  return (
    <div className="mx-auto max-w-[900px] px-6 py-8">
      <header className="mb-6">
        <h1 className="font-display text-2xl font-bold">새 전략 만들기</h1>
        <p className="text-sm text-[color:var(--text-secondary)]">
          Pine Script 전략 등록
        </p>
      </header>

      <WizardStepper current={step} />

      {/*
        Sprint 44 W F2: step key 별 motion-safe slide-left + fade entrance.
        prefers-reduced-motion 시 globals.css 가 일괄 disable.
      */}
      <section
        key={`step-${step}`}
        data-testid="wizard-step-section"
        className="motion-safe:animate-[wizardSlideIn_250ms_cubic-bezier(0.4,0,0.2,1)_both] mt-6 rounded-[var(--radius-lg)] border border-[color:var(--border)] bg-white p-8 shadow-[var(--card-shadow)]"
      >
        {step === 1 && (
          <StepMethod
            method={method}
            onMethodChange={setMethod}
            onNext={() => setStep(2)}
          />
        )}
        {step === 2 && (
          <StepCode
            pineSource={pineSource}
            onPineSourceChange={setPineSource}
            onParsed={setLastParse}
            onBack={() => setStep(1)}
            onNext={() => setStep(3)}
          />
        )}
        {step === 3 && (
          <StepMetadata
            lastParse={lastParse}
            submitting={create.isPending}
            onBack={() => setStep(2)}
            onSubmit={handleSubmit}
          />
        )}
      </section>

      {/* Draft 복원 Dialog */}
      <Dialog
        open={shouldPromptRestore}
        onOpenChange={(open) => {
          if (!open) setPromptDismissed(true);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>이어서 작성하시겠어요?</DialogTitle>
            <DialogDescription>
              {availableDraft &&
                `${new Date(availableDraft.savedAt).toLocaleString("ko-KR")}에 작성 중이던 초안이 있습니다.`}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="ghost" onClick={handleDiscardDraft}>
              새로 시작
            </Button>
            <Button onClick={handleRestore}>이어서 작성</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
