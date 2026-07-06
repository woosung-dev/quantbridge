// Clerk 회원가입 페이지 — split-screen shell + Clerk appearance 토큰 정합
// Precision Instrument W5 PR-12: radius 토큰 정합(input=--radius-sm / button=--radius-md)
// + hover lift 폐기(색 변화만). form rootBox fadeInUp 유지.
import { SignUp } from "@clerk/nextjs";
import { SplitScreenShell } from "../../_components/split-screen-shell";

export default function SignUpPage() {
  return (
    <SplitScreenShell mode="sign-up">
      <SignUp
        appearance={{
          elements: {
            // Sprint 44 W F2: form rootBox 진입 시 fadeInUp 200ms (brand 패널 stagger 와 sync).
            rootBox: "w-full motion-safe:animate-[fadeInUp_220ms_ease-out_60ms_both]",
            card: "shadow-none bg-transparent border-0 p-0",
            headerTitle:
              "font-[var(--font-heading)] text-[color:var(--text-primary)]",
            headerSubtitle: "text-[color:var(--text-muted)]",
            // Precision Instrument: hover 색 변화만 + input radius-sm 토큰 (sign-in 과 동일)
            formButtonPrimary:
              "bg-[color:var(--primary)] hover:bg-[color:var(--primary-hover)] rounded-[var(--radius-md)] shadow-[var(--btn-primary-shadow)] normal-case text-sm font-semibold h-12 transition-colors duration-200 ease-out",
            formFieldInput:
              "rounded-[var(--radius-sm)] border-[1.5px] border-[color:var(--border)] h-12 focus:border-[color:var(--primary)] focus:ring-2 focus:ring-[color:var(--primary)]/15 transition-[border-color,box-shadow] duration-200 ease-out",
            formFieldLabel:
              "text-[color:var(--text-secondary)] text-sm font-medium",
            socialButtonsBlockButton:
              "rounded-[var(--radius-md)] border-[1.5px] border-[color:var(--border)] hover:border-[color:var(--border-dark)] hover:bg-[color:var(--bg-alt)] h-12 transition-[border-color,background-color] duration-200 ease-out",
            footerActionLink:
              "text-[color:var(--primary)] hover:text-[color:var(--primary-hover)] font-semibold transition-colors duration-150",
            dividerLine: "bg-[color:var(--border)]",
            dividerText: "text-[color:var(--text-muted)]",
          },
          variables: {
            // colorPrimary 는 ClerkThemeBridge 가 테마별 코퍼 등급으로 주입 — 여기서
            // 재정의하면 다크 코퍼(#f08c2e)를 덮어써서 하드코딩 금지.
            borderRadius: "6px",
          },
        }}
      />
    </SplitScreenShell>
  );
}
