"use client";

// Sprint 11 Phase C — Public waitlist signup form.
// 5 필드 + 법무 고지 체크박스 필수. Zod resolver + react-hook-form.

import { useState } from "react";
import Link from "next/link";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod/v4";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useCreateWaitlist } from "@/features/waitlist/hooks";
import {
  CreateWaitlistApplicationSchema,
  type CreateWaitlistApplication,
} from "@/features/waitlist/schemas";

// 폼 로컬 스키마 — 법무 동의 체크박스 추가 (서버로 전송하지는 않음)
const FormSchema = CreateWaitlistApplicationSchema.extend({
  legalConsent: z
    .boolean()
    .refine((v) => v === true, "You must accept the legal notice to continue"),
});
type FormValues = z.infer<typeof FormSchema>;

type SubscriptionOpt = { value: CreateWaitlistApplication["tv_subscription"]; label: string };
type CapitalOpt = { value: CreateWaitlistApplication["exchange_capital"]; label: string };
type ExperienceOpt = { value: CreateWaitlistApplication["pine_experience"]; label: string };

const SUBSCRIPTION_OPTIONS: SubscriptionOpt[] = [
  { value: "pro", label: "Pro" },
  { value: "pro_plus", label: "Pro+" },
  { value: "premium", label: "Premium" },
];

const CAPITAL_OPTIONS: CapitalOpt[] = [
  { value: "under_1k", label: "Under $1,000" },
  { value: "1k_to_10k", label: "$1,000 ~ $10,000" },
  { value: "10k_to_100k", label: "$10,000 ~ $100,000" },
  { value: "over_100k", label: "Over $100,000" },
];

const EXPERIENCE_OPTIONS: ExperienceOpt[] = [
  { value: "none", label: "None" },
  { value: "beginner", label: "Beginner" },
  { value: "intermediate", label: "Intermediate" },
  { value: "expert", label: "Expert" },
];

export default function WaitlistPage() {
  const [submitted, setSubmitted] = useState(false);

  const form = useForm<FormValues>({
    resolver: zodResolver(FormSchema),
    defaultValues: {
      email: "",
      tv_subscription: "pro_plus",
      exchange_capital: "1k_to_10k",
      pine_experience: "beginner",
      existing_tool: "",
      pain_point: "",
      legalConsent: false,
    },
  });

  const create = useCreateWaitlist({
    onSuccess: () => {
      setSubmitted(true);
    },
    onError: (err) => {
      // 409 (duplicate) 는 그대로 안내, 그 외는 generic toast.
      const message = err instanceof Error ? err.message : "Submission failed";
      toast.error(message);
    },
  });

  const onSubmit = form.handleSubmit((values) => {
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { legalConsent, ...payload } = values;
    create.mutate({
      ...payload,
      // 빈 문자열은 null 로 정규화 — BE 는 optional.
      existing_tool: payload.existing_tool?.trim() ? payload.existing_tool.trim() : null,
    });
  });

  if (submitted) {
    return (
      <main
        id="main-content"
        className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-[680px] flex-col gap-6 px-6 py-14"
      >
        <h1 className="font-display text-3xl font-extrabold tracking-tight">
          You&apos;re on the list
        </h1>
        <p className="text-sm text-[color:var(--text-secondary)]">
          Thanks for signing up. We review applications manually to keep the Beta group
          tight. You&apos;ll receive an invite email when it&apos;s your turn.
        </p>
        <p className="text-sm text-[color:var(--text-secondary)]">
          Typical wait time: <strong>1-2 weeks</strong>. Check your inbox (and spam folder)
          for a message from <code>waitlist@quantbridge.app</code>.
        </p>
        <Link
          href="/"
          className="inline-block text-sm text-[color:var(--accent)] underline underline-offset-4"
        >
          ← Back to homepage
        </Link>
      </main>
    );
  }

  return (
    <main
      id="main-content"
      className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-[680px] flex-col gap-6 px-6 py-14"
    >
      <header className="space-y-3">
        <h1 className="font-display text-3xl font-extrabold tracking-tight">
          Request Beta Access
        </h1>
        <p className="text-sm text-[color:var(--text-secondary)]">
          QuantBridge Beta is invite-only while we stabilize the platform. Tell us about
          your setup and what you&apos;re trying to solve — we&apos;ll send an invite when
          your profile matches the current batch.
        </p>
      </header>

      <form onSubmit={onSubmit} className="space-y-5" noValidate>
        <div className="space-y-1.5">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            {...form.register("email")}
          />
          {form.formState.errors.email?.message ? (
            <p className="text-xs text-red-600">{form.formState.errors.email.message}</p>
          ) : null}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="tv_subscription">TradingView Subscription</Label>
          <select
            id="tv_subscription"
            className="h-10 w-full rounded-md border border-[color:var(--border)] bg-transparent px-3 text-sm"
            {...form.register("tv_subscription")}
          >
            {SUBSCRIPTION_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <p className="text-xs text-[color:var(--text-tertiary)]">
            Pro+ or higher is required for webhook alert delivery.
          </p>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="exchange_capital">Exchange Capital</Label>
          <select
            id="exchange_capital"
            className="h-10 w-full rounded-md border border-[color:var(--border)] bg-transparent px-3 text-sm"
            {...form.register("exchange_capital")}
          >
            {CAPITAL_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="pine_experience">Pine Script Experience</Label>
          <select
            id="pine_experience"
            className="h-10 w-full rounded-md border border-[color:var(--border)] bg-transparent px-3 text-sm"
            {...form.register("pine_experience")}
          >
            {EXPERIENCE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="existing_tool">
            Current Automation Tool <span className="text-xs text-[color:var(--text-tertiary)]">(optional)</span>
          </Label>
          <Input
            id="existing_tool"
            type="text"
            maxLength={120}
            placeholder="e.g. 3Commas, Trading Connector, none"
            {...form.register("existing_tool")}
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="pain_point">What problem do you want QuantBridge to solve?</Label>
          <Textarea
            id="pain_point"
            rows={4}
            maxLength={1000}
            placeholder="e.g. I'm manually copy-pasting alerts to my exchange; missed fills at night…"
            {...form.register("pain_point")}
          />
          {form.formState.errors.pain_point?.message ? (
            <p className="text-xs text-red-600">
              {form.formState.errors.pain_point.message}
            </p>
          ) : null}
        </div>

        <div className="flex items-start gap-3 rounded-md border border-[color:var(--border)] bg-amber-50 p-3">
          <input
            id="legalConsent"
            type="checkbox"
            className="mt-1 h-4 w-4"
            {...form.register("legalConsent")}
          />
          <div className="flex-1 space-y-1">
            <Label htmlFor="legalConsent" className="text-sm">
              법무 임시 고지 동의 / Legal acknowledgement
            </Label>
            <p className="text-xs text-[color:var(--text-secondary)]">
              I understand QuantBridge Beta is not investment advice and crypto derivatives
              trading can result in total loss of capital. I agree to the{" "}
              <Link href="/terms" className="underline">
                Terms
              </Link>
              ,{" "}
              <Link href="/privacy" className="underline">
                Privacy
              </Link>
              , and{" "}
              <Link href="/disclaimer" className="underline">
                Disclaimer
              </Link>
              .
            </p>
            {form.formState.errors.legalConsent?.message ? (
              <p className="text-xs text-red-600">
                {form.formState.errors.legalConsent.message}
              </p>
            ) : null}
          </div>
        </div>

        <Button type="submit" disabled={create.isPending} className="w-full">
          {create.isPending ? "Submitting…" : "Request Beta Access"}
        </Button>
      </form>
    </main>
  );
}
