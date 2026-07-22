"use client";

// 웨이트리스트 등록 폼 (.hero-form) — C 디자인 언어. screen-17-waitlist.html 구조 이식.
// 시각 정본은 프로토타입이지만 폼 필드는 실 백엔드 스키마(features/waitlist/schemas.ts)를 따른다.
// 프로토타입의 "사용 목적" 셀렉트는 스키마가 받치지 않아(§4.9) 렌더하지 않는다.
// 상태 3종을 실제로 렌더: 기본 / 필드 검증 에러(role=alert) / 등록 완료(state-box).

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod/v4";

import { StateBox } from "@/components/state-box";
import { useCreateWaitlist } from "@/features/waitlist/hooks";
import {
  CreateWaitlistApplicationSchema,
  type CreateWaitlistApplication,
} from "@/features/waitlist/schemas";
import { zodV4Resolver } from "@/lib/zod-v4-resolver";

// 폼 로컬 스키마 — 법무 동의 체크(서버로 전송하지 않음)를 더한다.
const FormSchema = CreateWaitlistApplicationSchema.extend({
  legalConsent: z.boolean().refine((v) => v === true, "약관에 동의해 주세요."),
});
type FormValues = z.infer<typeof FormSchema>;

const SUBSCRIPTION_OPTIONS: {
  value: CreateWaitlistApplication["tv_subscription"];
  label: string;
}[] = [
  { value: "pro", label: "Pro" },
  { value: "pro_plus", label: "Pro+" },
  { value: "premium", label: "Premium" },
];

const CAPITAL_OPTIONS: {
  value: CreateWaitlistApplication["exchange_capital"];
  label: string;
}[] = [
  { value: "under_1k", label: "$1,000 미만" },
  { value: "1k_to_10k", label: "$1,000 ~ $10,000" },
  { value: "10k_to_100k", label: "$10,000 ~ $100,000" },
  { value: "over_100k", label: "$100,000 초과" },
];

const EXPERIENCE_OPTIONS: {
  value: CreateWaitlistApplication["pine_experience"];
  label: string;
}[] = [
  { value: "none", label: "없음" },
  { value: "beginner", label: "초급" },
  { value: "intermediate", label: "중급" },
  { value: "expert", label: "전문가" },
];

function FieldError({ id, message }: { id: string; message: string }) {
  return (
    <p className="field-error" id={id} role="alert">
      <svg
        viewBox="0 0 24 24"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <circle cx="12" cy="12" r="9" />
        <line x1="12" y1="7.5" x2="12" y2="13" />
        <line x1="12" y1="16.5" x2="12" y2="16.6" />
      </svg>
      <span>{message}</span>
    </p>
  );
}

export function WaitlistFormCard({ defaultEmail = "" }: { defaultEmail?: string }) {
  const [submitted, setSubmitted] = useState(false);

  const form = useForm<FormValues>({
    resolver: zodV4Resolver(FormSchema),
    defaultValues: {
      email: defaultEmail,
      tv_subscription: "pro_plus",
      exchange_capital: "1k_to_10k",
      pine_experience: "beginner",
      existing_tool: "",
      pain_point: "",
      legalConsent: false,
    },
  });

  const create = useCreateWaitlist({
    onSuccess: () => setSubmitted(true),
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : "등록에 실패했습니다.");
    },
  });

  const onSubmit = form.handleSubmit((values) => {
    const { legalConsent: _legalConsent, ...payload } = values;
    void _legalConsent;
    create.mutate({
      ...payload,
      existing_tool: payload.existing_tool?.trim() ? payload.existing_tool.trim() : null,
    });
  });

  if (submitted) {
    return (
      <section className="card hero-form" aria-label="등록 완료" aria-live="polite">
        <div className="card-body">
          <StateBox
            tone="neutral"
            icon={
              <svg viewBox="0 0 24 24" fill="none" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="4 12.5 9.5 18 20 6.5" />
              </svg>
            }
            title="등록되었습니다."
            body="공개 준비가 시작되면 그 사실만 담은 메일 한 통을 보냅니다. 그 전에는 아무 메일도 보내지 않습니다."
          />
          <p className="form-note">
            등록 순번, 대기 인원, 예상 대기 기간은 표시하지 않습니다. 집계하지 않는 값이라 인쇄할
            근거가 없습니다.
          </p>
        </div>
      </section>
    );
  }

  const errors = form.formState.errors;

  return (
    <form className="card hero-form" onSubmit={onSubmit} noValidate>
      <div className="card-head">
        <div>
          <h2 className="card-title" id="signup">
            웨이트리스트 등록
          </h2>
          <p className="card-sub">이메일과 몇 가지 배경만 받습니다.</p>
        </div>
      </div>
      <div className="card-body">
        <div className="field">
          <label className="field-label" htmlFor="wl-email">
            이메일 주소
          </label>
          <input
            className={errors.email ? "input invalid" : "input"}
            id="wl-email"
            type="email"
            inputMode="email"
            autoComplete="email"
            placeholder="name@example.com"
            aria-invalid={errors.email ? "true" : "false"}
            aria-describedby={errors.email ? "wl-email-error" : "wl-email-hint"}
            {...form.register("email")}
          />
          {errors.email?.message ? (
            <FieldError id="wl-email-error" message={errors.email.message} />
          ) : (
            <p className="field-hint" id="wl-email-hint">
              공개 안내 메일 한 통에만 사용합니다.
            </p>
          )}
        </div>

        <div className="field">
          <label className="field-label" htmlFor="wl-subscription">
            TradingView 구독
          </label>
          <select className="select" id="wl-subscription" {...form.register("tv_subscription")}>
            {SUBSCRIPTION_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
          <p className="field-hint">webhook 발송에는 Pro+ 이상이 필요합니다.</p>
        </div>

        <div className="field">
          <label className="field-label" htmlFor="wl-capital">
            운용 자본
          </label>
          <select className="select" id="wl-capital" {...form.register("exchange_capital")}>
            {CAPITAL_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <label className="field-label" htmlFor="wl-experience">
            Pine Script 경험
          </label>
          <select className="select" id="wl-experience" {...form.register("pine_experience")}>
            {EXPERIENCE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <label className="field-label" htmlFor="wl-existing">
            현재 쓰는 자동매매 도구 <span className="optional-tag">(선택)</span>
          </label>
          <input
            className="input"
            id="wl-existing"
            type="text"
            maxLength={120}
            placeholder="예: 3Commas, Trading Connector, 없음"
            {...form.register("existing_tool")}
          />
        </div>

        <div className="field">
          <label className="field-label" htmlFor="wl-pain">
            QuantBridge 로 풀고 싶은 문제
          </label>
          <textarea
            className={errors.pain_point ? "input invalid" : "input"}
            id="wl-pain"
            rows={4}
            maxLength={1000}
            placeholder="예: 알림을 거래소에 수동으로 옮기다 새벽 진입을 자주 놓칩니다."
            aria-invalid={errors.pain_point ? "true" : "false"}
            aria-describedby={errors.pain_point ? "wl-pain-error" : undefined}
            {...form.register("pain_point")}
          />
          {errors.pain_point?.message && (
            <FieldError id="wl-pain-error" message={errors.pain_point.message} />
          )}
        </div>

        <div className="field">
          <div className="consent-field">
            <input
              id="wl-consent"
              type="checkbox"
              aria-invalid={errors.legalConsent ? "true" : "false"}
              aria-describedby={errors.legalConsent ? "wl-consent-error" : undefined}
              {...form.register("legalConsent")}
            />
            <label className="consent-body" htmlFor="wl-consent">
              QuantBridge 가 투자 자문이 아니며, 자동매매는 원금 손실 가능성이 있다는 점을
              이해합니다. <Link href="/terms">이용약관</Link>,{" "}
              <Link href="/privacy">개인정보 처리방침</Link>,{" "}
              <Link href="/disclaimer">면책조항</Link>에 동의합니다.
            </label>
          </div>
          {errors.legalConsent?.message && (
            <FieldError id="wl-consent-error" message={errors.legalConsent.message} />
          )}
        </div>

        <button
          className="btn btn-primary btn-block form-submit"
          type="submit"
          disabled={create.isPending}
          aria-busy={create.isPending}
        >
          {create.isPending ? "전송 중" : "등록"}
        </button>

        <p className="form-note">
          이메일과 사용 목적만 받습니다. 대기자 수와 등록 순번은 집계하지 않으므로 표시하지
          않습니다.
        </p>
      </div>
    </form>
  );
}
