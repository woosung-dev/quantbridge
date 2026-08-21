// 회원가입 페이지 — C 디자인 언어 셸 + 자체 폼(ADR-034, 구 Clerk `<SignUp/>` 대체).
// 제한 국가 차단은 이 화면이 아니라 `lib/auth.ts` 의 create 훅(L3)이 한다 — 클라이언트에서
// 막으면 우회되고, 그 차단은 서버가 헤더를 보는 자리에서만 참이다.
import type { Metadata } from "next";

import { AuthForm } from "@/features/auth/components/auth-form";
import { SplitScreenShell } from "@/features/auth/components/split-screen-shell";

// 페이지 이름 5축 일치(§4.10) — 셸 제목·<title> 모두 "회원가입"(split-screen-shell.tsx SSOT).
export const metadata: Metadata = {
  title: "회원가입",
};

export default function SignUpPage() {
  return (
    <SplitScreenShell mode="sign-up">
      <AuthForm mode="sign-up" redirectTo="/strategies" />
    </SplitScreenShell>
  );
}
