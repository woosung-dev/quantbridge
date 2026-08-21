// 인증 라우트 그룹 (auth) 셸 — C 디자인 언어. screen-15-login.html 이식.
// 자체 헤더(.auth-top) + 좌우 2분할(.auth-split: 좌 BrandPanel · 우 인증 폼) + 푸터(.auth-foot).
// 폼은 `auth-form.tsx` 가 그리고 이 셸은 카드만 준다 — 2026-08-17 ADR-034 로 외부 위젯이 사라졌다.

import type { ReactNode } from "react";
import Link from "next/link";

import { BrandPanel } from "./brand-panel";

type SplitMode = "sign-in" | "sign-up";

interface ModeCopy {
  title: string;
  desc: string;
  /** 우상단 상호 링크 — sign-in ↔ sign-up 을 오간다. */
  crossHref: string;
  crossLabel: string;
}

const MODE_COPY: Record<SplitMode, ModeCopy> = {
  "sign-in": {
    title: "로그인",
    desc: "이메일과 비밀번호로 워크스페이스에 들어갑니다.",
    crossHref: "/sign-up",
    crossLabel: "회원가입",
  },
  "sign-up": {
    title: "회원가입",
    desc: "이메일로 워크스페이스 계정을 만듭니다. 거래소 연결은 가입 뒤에 따로 진행합니다.",
    crossHref: "/sign-in",
    crossLabel: "로그인",
  },
};

export function SplitScreenShell({ mode, children }: { mode: SplitMode; children: ReactNode }) {
  const copy = MODE_COPY[mode];

  return (
    <div className="auth-shell">
      <header className="auth-top">
        <Link className="auth-logo" href="/" aria-label="QuantBridge 홈으로">
          <span className="brand-mark" aria-hidden="true">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.4"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="3 17 9 11 13 15 21 7" />
              <polyline points="15 7 21 7 21 13" />
            </svg>
          </span>
          <span className="brand-name">QuantBridge</span>
        </Link>

        <span className="auth-top-right">
          <Link className="btn btn-ghost" href={copy.crossHref}>
            {copy.crossLabel}
          </Link>
          <Link className="btn btn-ghost" href="/">
            홈으로
          </Link>
        </span>
      </header>

      <main className="auth-main" id="main-content">
        <div className="auth-split">
          <BrandPanel />

          <section className="auth-form-col rise d2" aria-labelledby="auth-title">
            <header className="auth-form-head section-head">
              <p className="eyebrow">
                <span className="num">02</span> 계정
              </p>
              <h2 className="section-title" id="auth-title">
                {copy.title}
              </h2>
              <p className="section-desc">{copy.desc}</p>
            </header>

            <div className="card auth-card">
              <div className="card-body">
                <div className="auth-form-slot">{children}</div>
              </div>
            </div>
          </section>
        </div>
      </main>

      <footer className="foot auth-foot">
        <span>QuantBridge · {copy.title} · 계정은 QuantBridge 가 직접 관리합니다.</span>
        <span>백테스트와 실제 주문이 같은 코드 경로를 씁니다.</span>
      </footer>
    </div>
  );
}
