"use client";

// Sprint 7c T4: /strategies/new — 3-step wizard + localStorage draft 복원 Dialog.
// Pass 4 Copy Cut: 헤더 sub 문구 축약. useCreateStrategy mutate에 inline onSuccess/onError 전달.

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
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
  clearWizardDraft,
  loadWizardDraft,
  useAutoSaveDraft,
  type WizardDraft,
} from "@/features/strategy/draft";

import { WizardStepper } from "./_components/wizard-stepper";
import { StepMethod } from "./_components/step-method";
import { StepCode } from "./_components/step-code";
import { StepMetadata } from "./_components/step-metadata";

type Step = 1 | 2 | 3;
type Method = "direct" | "upload" | "url";

export default function NewStrategyPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>(1);
  const [method, setMethod] = useState<Method>("direct");
  const [pineSource, setPineSource] = useState("");
  const [lastParse, setLastParse] = useState<ParsePreviewResponse | null>(null);

  // Draft 복원 관련 state
  const [restorePromptOpen, setRestorePromptOpen] = useState(false);
  const [availableDraft, setAvailableDraft] = useState<WizardDraft | null>(null);

  // mount 시 localStorage draft 존재 체크 → 복원 프롬프트.
  // localStorage는 client-only 외부 저장소이므로 effect 내 setState는 안전한 동기화 패턴.
  // (SSR hydration mismatch 회피 목적으로 useState lazy init 대신 effect 사용.)
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    const d = loadWizardDraft();
    if (d && (d.pineSource.trim().length > 0 || d.metadata.name)) {
      setAvailableDraft(d);
      setRestorePromptOpen(true);
    }
  }, []);
  /* eslint-enable react-hooks/set-state-in-effect */

  // auto-save (500ms debounce, primitive deps로 무한 루프 회피)
  useAutoSaveDraft({
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
          clearWizardDraft();
          toast.success(`"${data.name}" 전략이 생성되었습니다`);
          router.push(`/strategies/${data.id}/edit`);
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
    setRestorePromptOpen(false);
  };

  const handleDiscardDraft = () => {
    clearWizardDraft();
    setAvailableDraft(null);
    setRestorePromptOpen(false);
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

      <section className="mt-6 rounded-[var(--radius-lg)] border border-[color:var(--border)] bg-white p-8 shadow-[var(--card-shadow)]">
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
      <Dialog open={restorePromptOpen} onOpenChange={setRestorePromptOpen}>
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
