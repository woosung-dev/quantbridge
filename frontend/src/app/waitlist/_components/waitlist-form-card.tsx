"use client";

// Sprint 43 W13 — /waitlist 폼 카드 (Zod+RHF visual polish, 기존 로직 보존)
// design source: ui-ux-pro-max master "form card" + DESIGN.md border/text 토큰

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
    .refine((v) => v === true, "약관에 동의해주세요"),
});
type FormValues = z.infer<typeof FormSchema>;

type SubscriptionOpt = {
  value: CreateWaitlistApplication["tv_subscription"];
  label: string;
};
type CapitalOpt = {
  value: CreateWaitlistApplication["exchange_capital"];
  label: string;
};
type ExperienceOpt = {
  value: CreateWaitlistApplication["pine_experience"];
  label: string;
};

const SUBSCRIPTION_OPTIONS: SubscriptionOpt[] = [
  { value: "pro", label: "Pro" },
  { value: "pro_plus", label: "Pro+" },
  { value: "premium", label: "Premium" },
];

const CAPITAL_OPTIONS: CapitalOpt[] = [
  { value: "under_1k", label: "$1,000 미만" },
  { value: "1k_to_10k", label: "$1,000 ~ $10,000" },
  { value: "10k_to_100k", label: "$10,000 ~ $100,000" },
  { value: "over_100k", label: "$100,000 초과" },
];

const EXPERIENCE_OPTIONS: ExperienceOpt[] = [
  { value: "none", label: "없음" },
  { value: "beginner", label: "초급" },
  { value: "intermediate", label: "중급" },
  { value: "expert", label: "전문가" },
];

const SELECT_BASE_CLASS =
  "h-10 w-full rounded-md border border-[color:var(--border)] bg-white px-3 text-sm text-[color:var(--text-primary)] transition-colors hover:border-[color:var(--border-dark)] focus:border-[color:var(--accent-amber)] focus:outline-none focus:ring-2 focus:ring-[color:var(--accent-amber)]/20";

export function WaitlistFormCard() {
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
      existing_tool: payload.existing_tool?.trim()
        ? payload.existing_tool.trim()
        : null,
    });
  });

  if (submitted) {
    return (
      <section
        aria-live="polite"
        className="rounded-2xl border border-[color:var(--border)] bg-white p-10 shadow-sm"
      >
        <div className="space-y-5 text-center">
          <span
            aria-hidden="true"
            className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-[color:var(--accent-amber-light)] text-2xl"
          >
            ✓
          </span>
          <h2 className="font-display text-2xl font-bold tracking-tight text-[color:var(--text-primary)]">
            신청 완료
          </h2>
          <p className="text-sm leading-relaxed text-[color:var(--text-secondary)]">
            QuantBridge Beta 신청이 정상 접수됐습니다. Beta 그룹을 작게 유지하기 위해 신청서를 직접 검토합니다.
            <br />
            평균 회신 기간은 <strong>1-2 주</strong> 입니다. 받은편지함 (스팸 폴더 포함) 에서{" "}
            <code className="rounded bg-[color:var(--accent)] px-1.5 py-0.5 text-xs">
              waitlist@quantbridge.app
            </code>{" "}
            메일을 기다려주세요.
          </p>
          <div className="pt-2">
            <Link
              href="/"
              className="inline-flex h-10 items-center justify-center rounded-md border border-[color:var(--border)] bg-white px-5 text-sm font-medium text-[color:var(--text-primary)] transition-colors hover:bg-[color:var(--accent)]"
            >
              ← 홈으로
            </Link>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section
      aria-label="Beta 신청 폼"
      className="rounded-2xl border border-[color:var(--border)] bg-white p-8 shadow-sm sm:p-10"
    >
      <header className="mb-8 space-y-2">
        <h2 className="font-display text-2xl font-bold tracking-tight text-[color:var(--text-primary)]">
          Beta 신청
        </h2>
        <p className="text-sm text-[color:var(--text-secondary)]">
          신청자 프로필을 매주 검토해 5-10 명에게 초대장을 보냅니다.
        </p>
      </header>

      <form onSubmit={onSubmit} className="space-y-5" noValidate>
        <div className="space-y-1.5">
          <Label htmlFor="email">
            이메일 <span className="text-[color:var(--accent-amber)]">*</span>
          </Label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            aria-invalid={form.formState.errors.email ? "true" : "false"}
            {...form.register("email")}
          />
          {form.formState.errors.email?.message ? (
            <p role="alert" className="text-xs text-red-600">
              {form.formState.errors.email.message}
            </p>
          ) : null}
        </div>

        <div className="grid gap-5 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="tv_subscription">TradingView 구독</Label>
            <select
              id="tv_subscription"
              className={SELECT_BASE_CLASS}
              {...form.register("tv_subscription")}
            >
              {SUBSCRIPTION_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            <p className="text-xs text-[color:var(--text-muted)]">
              webhook 발송에는 Pro+ 이상이 필요합니다.
            </p>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="exchange_capital">운용 자본</Label>
            <select
              id="exchange_capital"
              className={SELECT_BASE_CLASS}
              {...form.register("exchange_capital")}
            >
              {CAPITAL_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="pine_experience">Pine Script 경험</Label>
          <select
            id="pine_experience"
            className={SELECT_BASE_CLASS}
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
            현재 사용 중인 자동매매 툴{" "}
            <span className="text-xs font-normal text-[color:var(--text-muted)]">
              (선택)
            </span>
          </Label>
          <Input
            id="existing_tool"
            type="text"
            maxLength={120}
            placeholder="예: 3Commas, Trading Connector, 없음"
            {...form.register("existing_tool")}
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="pain_point">
            QuantBridge 가 풀어주길 바라는 문제{" "}
            <span className="text-[color:var(--accent-amber)]">*</span>
          </Label>
          <Textarea
            id="pain_point"
            rows={4}
            maxLength={1000}
            placeholder="예: 알림을 거래소에 수동 복사 중인데 새벽에 진입을 놓치는 일이 잦음."
            aria-invalid={form.formState.errors.pain_point ? "true" : "false"}
            {...form.register("pain_point")}
          />
          {form.formState.errors.pain_point?.message ? (
            <p role="alert" className="text-xs text-red-600">
              {form.formState.errors.pain_point.message}
            </p>
          ) : null}
        </div>

        <div className="flex items-start gap-3 rounded-lg border border-[color:var(--accent-amber)]/30 bg-[color:var(--accent-amber-light)]/40 p-4">
          <input
            id="legalConsent"
            type="checkbox"
            className="mt-0.5 h-4 w-4 flex-none accent-[color:var(--accent-amber)]"
            {...form.register("legalConsent")}
          />
          <div className="flex-1 space-y-1.5">
            <Label
              htmlFor="legalConsent"
              className="text-sm font-semibold text-[color:var(--text-primary)]"
            >
              법적 고지 동의
            </Label>
            <p className="text-xs leading-relaxed text-[color:var(--text-secondary)]">
              QuantBridge Beta 가 투자 자문이 아니며, 암호화폐 파생상품 거래는 원금 전액 손실 가능성이 있다는 점을 이해합니다.{" "}
              <Link
                href="/terms"
                className="text-[color:var(--accent-amber)] underline underline-offset-2"
              >
                이용약관
              </Link>
              ,{" "}
              <Link
                href="/privacy"
                className="text-[color:var(--accent-amber)] underline underline-offset-2"
              >
                개인정보 처리방침
              </Link>
              ,{" "}
              <Link
                href="/disclaimer"
                className="text-[color:var(--accent-amber)] underline underline-offset-2"
              >
                면책조항
              </Link>
              에 동의합니다.
            </p>
            {form.formState.errors.legalConsent?.message ? (
              <p role="alert" className="text-xs text-red-600">
                {form.formState.errors.legalConsent.message}
              </p>
            ) : null}
          </div>
        </div>

        <Button
          type="submit"
          disabled={create.isPending}
          className="h-11 w-full text-sm font-semibold"
          style={{
            backgroundColor: "var(--accent-amber)",
            color: "#fff",
          }}
        >
          {create.isPending ? "전송 중…" : "Beta 신청서 제출"}
        </Button>
        <p className="text-center text-xs text-[color:var(--text-muted)]">
          제출 후 평균 1-2 주 안에 회신 메일을 보내드립니다.
        </p>
      </form>
    </section>
  );
}
