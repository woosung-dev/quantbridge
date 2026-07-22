// 요금제 05 웨이트리스트 미니 폼 (.signup) — 이메일 검증 후 /waitlist 로 이동. screen-16 이식.
// 등록 인원수·대기 순번은 집계하지 않으므로 표시하지 않는다(§4.9).
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

export function PricingWaitlistForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [invalid, setInvalid] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const ok = EMAIL_RE.test(email.trim());
    setInvalid(!ok);
    if (ok) router.push(`/waitlist?email=${encodeURIComponent(email.trim())}`);
  };

  return (
    <div className="card card-pad">
      <form className="signup" onSubmit={handleSubmit} noValidate>
        <div>
          <label className="field-label" htmlFor="pricing-waitlist-email">
            이메일 주소
          </label>
          <input
            className={invalid ? "input invalid" : "input"}
            id="pricing-waitlist-email"
            name="email"
            type="email"
            placeholder="name@example.com"
            style={{ width: "100%" }}
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              if (invalid) setInvalid(false);
            }}
            aria-invalid={invalid}
            aria-describedby={invalid ? "pricing-waitlist-error" : undefined}
          />
        </div>
        <button className="btn btn-primary" type="submit">
          등록하기
        </button>
      </form>

      {invalid && (
        <p className="field-error" id="pricing-waitlist-error" role="alert">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="9" />
            <line x1="12" y1="7.5" x2="12" y2="12.5" />
            <line x1="12" y1="16" x2="12" y2="16.1" />
          </svg>
          이메일 주소 형식이 올바르지 않습니다. @ 뒤에 도메인을 입력해 주세요.
        </p>
      )}

      <p className="signup-note">
        등록은 웨이트리스트 페이지에서 마칩니다. 등록 인원수나 대기 순번은 집계하지 않습니다. 보낼
        메일도 공개 안내 한 통뿐입니다.
      </p>
    </div>
  );
}
