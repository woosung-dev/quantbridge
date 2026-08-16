"use client";

// 로그인/가입 폼 — Better Auth 는 프리빌트 UI 를 제공하지 않으므로 우리가 짓는다(ADR-034).
// 마크업 어휘(.field/.input/.field-error/.btn)는 `waitlist-form-card.tsx` 와 같은 C 디자인
// 캐논을 따른다 — 새 클래스를 만들지 않는 것이 이 파일의 제약이다.

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod/v4";

import { clearAuthTokenCache, signIn, signUp } from "@/lib/auth-client";
import { zodV4Resolver } from "@/lib/zod-v4-resolver";

const MIN_PASSWORD = 8;

const SignInSchema = z.object({
  email: z.email("올바른 이메일 주소를 입력해 주세요."),
  password: z.string().min(1, "비밀번호를 입력해 주세요."),
});

const SignUpSchema = z.object({
  name: z.string().trim().min(1, "이름을 입력해 주세요.").max(64, "64자 이내로 입력해 주세요."),
  email: z.email("올바른 이메일 주소를 입력해 주세요."),
  password: z.string().min(MIN_PASSWORD, `비밀번호는 ${MIN_PASSWORD}자 이상이어야 합니다.`),
});

type SignInValues = z.infer<typeof SignInSchema>;
type SignUpValues = z.infer<typeof SignUpSchema>;
type Values = SignInValues & Partial<Pick<SignUpValues, "name">>;

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

/**
 * 서버가 준 에러를 사람이 읽을 문장으로 바꾼다.
 *
 * ★원문을 그대로 노출하지 않는다 — 2026-08-15 surface-truth 가 「내부 예외 문자열이 응답
 * 본문에 반사된다」를 두 축에서 닫았고, 인증 화면은 그 표면이 가장 넓은 자리다.
 */
function describe(code: string | undefined, status: number | undefined, mode: Mode): string {
  if (status === 429) return "요청이 너무 잦습니다. 잠시 후 다시 시도해 주세요.";
  if (mode === "sign-up" && code === "USER_ALREADY_EXISTS") {
    return "이미 가입된 이메일입니다. 로그인해 주세요.";
  }
  if (mode === "sign-up" && status === 403) {
    return "현재 이 지역에서는 가입할 수 없습니다.";
  }
  if (mode === "sign-in") return "이메일 또는 비밀번호가 올바르지 않습니다.";
  return "가입에 실패했습니다. 잠시 후 다시 시도해 주세요.";
}

export type Mode = "sign-in" | "sign-up";

export function AuthForm({ mode, redirectTo }: { mode: Mode; redirectTo: string }) {
  const router = useRouter();
  const isSignUp = mode === "sign-up";
  const [formError, setFormError] = useState<string | null>(null);

  const form = useForm<Values>({
    resolver: zodV4Resolver(isSignUp ? SignUpSchema : SignInSchema),
    defaultValues: { email: "", password: "", ...(isSignUp ? { name: "" } : {}) },
  });

  const onSubmit = form.handleSubmit(async (values) => {
    setFormError(null);
    // ★토큰 캐시를 먼저 비운다 — 계정 전환 시 앞 사용자의 JWT 가 남아 있으면 첫 API 호출이
    //   남의 자격으로 나간다.
    clearAuthTokenCache();

    const result = isSignUp
      ? await signUp.email({
          name: (values.name ?? "").trim(),
          email: values.email,
          password: values.password,
        })
      : await signIn.email({ email: values.email, password: values.password });

    if (result.error) {
      setFormError(describe(result.error.code, result.error.status, mode));
      return;
    }
    router.replace(redirectTo);
    router.refresh();
  });

  const errors = form.formState.errors;
  const busy = form.formState.isSubmitting;

  return (
    // ★카드는 `SplitScreenShell` 이 이미 씌운다 — 여기서 또 `.card` 를 쓰면 카드 안 카드가 된다.
    <form className="auth-form" onSubmit={onSubmit} noValidate>
      <div className="auth-form-body">
        {isSignUp ? (
          <div className="field">
            <label className="field-label" htmlFor="auth-name">
              이름
            </label>
            <input
              className={errors.name ? "input invalid" : "input"}
              id="auth-name"
              type="text"
              autoComplete="name"
              placeholder="홍길동"
              aria-invalid={errors.name ? "true" : "false"}
              aria-describedby={errors.name ? "auth-name-error" : undefined}
              {...form.register("name")}
            />
            {errors.name?.message ? (
              <FieldError id="auth-name-error" message={errors.name.message} />
            ) : null}
          </div>
        ) : null}

        <div className="field">
          <label className="field-label" htmlFor="auth-email">
            이메일 주소
          </label>
          <input
            className={errors.email ? "input invalid" : "input"}
            id="auth-email"
            type="email"
            inputMode="email"
            autoComplete="email"
            placeholder="name@example.com"
            aria-invalid={errors.email ? "true" : "false"}
            aria-describedby={errors.email ? "auth-email-error" : undefined}
            {...form.register("email")}
          />
          {errors.email?.message ? (
            <FieldError id="auth-email-error" message={errors.email.message} />
          ) : null}
        </div>

        <div className="field">
          <label className="field-label" htmlFor="auth-password">
            비밀번호
          </label>
          <input
            className={errors.password ? "input invalid" : "input"}
            id="auth-password"
            type="password"
            autoComplete={isSignUp ? "new-password" : "current-password"}
            aria-invalid={errors.password ? "true" : "false"}
            aria-describedby={
              errors.password ? "auth-password-error" : isSignUp ? "auth-password-hint" : undefined
            }
            {...form.register("password")}
          />
          {errors.password?.message ? (
            <FieldError id="auth-password-error" message={errors.password.message} />
          ) : isSignUp ? (
            <p className="field-hint" id="auth-password-hint">
              {MIN_PASSWORD}자 이상으로 정해 주세요.
            </p>
          ) : null}
        </div>

        {formError ? <FieldError id="auth-form-error" message={formError} /> : null}

        <button
          className="btn btn-primary btn-block form-submit"
          type="submit"
          disabled={busy}
          aria-busy={busy}
        >
          {busy ? "처리 중…" : isSignUp ? "계정 만들기" : "로그인"}
        </button>
      </div>
    </form>
  );
}
