// Clerk 회원가입 페이지 — split-screen shell + Clerk appearance 토큰 정합
import { SignUp } from "@clerk/nextjs";
import { SplitScreenShell } from "../../_components/split-screen-shell";

export default function SignUpPage() {
  return (
    <SplitScreenShell mode="sign-up">
      <SignUp
        appearance={{
          elements: {
            rootBox: "w-full",
            card: "shadow-none bg-transparent border-0 p-0",
            headerTitle:
              "font-[var(--font-heading)] text-[color:var(--text-primary)]",
            headerSubtitle: "text-[color:var(--text-muted)]",
            formButtonPrimary:
              "bg-[color:var(--primary)] hover:bg-[color:var(--primary-hover)] rounded-[var(--radius-md)] shadow-[var(--btn-primary-shadow)] hover:shadow-[var(--btn-primary-shadow-hover)] normal-case text-sm font-semibold",
            formFieldInput:
              "rounded-[var(--radius-sm)] border-[color:var(--border)] focus:border-[color:var(--primary)] focus:ring-2 focus:ring-[color:var(--primary)]/15",
            formFieldLabel:
              "text-[color:var(--text-secondary)] text-sm font-medium",
            socialButtonsBlockButton:
              "rounded-[var(--radius-md)] border-[color:var(--border)] hover:border-[color:var(--border-dark)] hover:bg-[color:var(--bg-alt)]",
            footerActionLink:
              "text-[color:var(--primary)] hover:text-[color:var(--primary-hover)] font-semibold",
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
