// Clerk 로그인 페이지 — split-screen shell + Clerk appearance 토큰 정합
// design source: docs/prototypes/04-login.html (input radius=8 / button radius=10 / h=48)
// Sprint 44 W F2: focus ring transition 200ms / button hover lift / form rootBox fadeInUp.
import { SignIn } from "@clerk/nextjs";
import { SplitScreenShell } from "../../_components/split-screen-shell";

export default function SignInPage() {
  return (
    <SplitScreenShell mode="sign-in">
      <SignIn
        appearance={{
          elements: {
            // Sprint 44 W F2: form rootBox 진입 시 fadeInUp 200ms (brand 패널 stagger 와 sync).
            rootBox: "w-full motion-safe:animate-[fadeInUp_220ms_ease-out_60ms_both]",
            card: "shadow-none bg-transparent border-0 p-0",
            headerTitle:
              "font-[var(--font-heading)] text-[color:var(--text-primary)]",
            headerSubtitle: "text-[color:var(--text-muted)]",
            // Sprint 44 W F2: 버튼 transition 200ms ease-out + 호버 시 그림자 +
            formButtonPrimary:
              "bg-[color:var(--primary)] hover:bg-[color:var(--primary-hover)] rounded-[var(--radius-md)] shadow-[var(--btn-primary-shadow)] hover:shadow-[var(--btn-primary-shadow-hover)] normal-case text-sm font-semibold h-12 transition-[box-shadow,background-color] duration-200 ease-out",
            // Sprint 44 W F2: input focus ring 200ms transition 정합
            formFieldInput:
              "rounded-[8px] border-[1.5px] border-[color:var(--border)] h-12 focus:border-[color:var(--primary)] focus:ring-2 focus:ring-[color:var(--primary)]/15 transition-[border-color,box-shadow] duration-200 ease-out",
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
            colorPrimary: "#2563eb",
            colorText: "#0f172a",
            colorTextSecondary: "#475569",
            colorBackground: "#ffffff",
            colorInputBackground: "#ffffff",
            colorInputText: "#0f172a",
            borderRadius: "10px",
          },
        }}
      />
    </SplitScreenShell>
  );
}
