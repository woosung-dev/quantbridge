// 랜딩 06 시작 (.lp-cta) — 이메일 인라인 검증 + 웨이트리스트로 안내. screen-14-landing.html 이식.
// 지금은 가입을 받지 않으므로, 유효한 이메일이면 웨이트리스트 페이지로 이동해 등록을 마친다.
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

export function LandingCta() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [invalid, setInvalid] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const ok = EMAIL_RE.test(email.trim());
    setInvalid(!ok);
    if (ok) {
      router.push(`/waitlist?email=${encodeURIComponent(email.trim())}`);
    }
  };

  return (
    <section className="section rise d7" id="cta" aria-label="시작하기">
      <header className="section-head">
        <p className="eyebrow">시작</p>
        <h2 className="section-title">지금은 가입을 받지 않습니다</h2>
        <p className="section-desc">공개하게 되면 한 번만 알리도록 이메일을 남겨 둘 수 있습니다.</p>
      </header>

      <div className="card lp-cta">
        <p className="lp-cta-title">공개하면 한 번 알려 드립니다.</p>
        <p className="lp-cta-desc">
          지금 남길 수 있는 것은 이메일 하나뿐입니다. 마케팅 메일은 보내지 않고 공개 시점에 한 번만
          씁니다.
        </p>

        <form className="email-form" onSubmit={handleSubmit} noValidate>
          <label className="field-label" htmlFor="notifyEmail">
            알림 받을 이메일
          </label>
          <div className="field-row">
            <input
              className="input mono"
              id="notifyEmail"
              name="email"
              type="email"
              placeholder="name@example.com"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                if (invalid) setInvalid(false);
              }}
              aria-invalid={invalid}
              aria-describedby={invalid ? "notifyEmailErr" : undefined}
            />
            <button className="btn btn-primary" type="submit">
              알림 신청
            </button>
          </div>
          {invalid && (
            <p className="field-error" id="notifyEmailErr" role="alert">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <circle cx="12" cy="12" r="9" />
                <line x1="12" y1="8" x2="12" y2="13" />
                <line x1="12" y1="16.5" x2="12.01" y2="16.5" />
              </svg>
              <span>
                이메일 형식이 올바르지 않습니다. name@example.com 처럼 도메인까지 입력해 주세요.
              </span>
            </p>
          )}
          <p className="field-help">
            등록은 웨이트리스트 페이지에서 마칩니다. 마케팅 메일 없이 공개 시점에 한 번만 알립니다.
          </p>
        </form>
      </div>
    </section>
  );
}
