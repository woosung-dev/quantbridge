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
      {/* 가입 직후에는 온보딩(5분 코스)으로 보낸다 — 2026-09-06 d1 실사용 루프 실측:
          종전 착지점인 빈 `/strategies` 에서 온보딩으로 가는 링크가 앱 전체에 0건이었다.
          재방문 경로는 빈 목록의 진입 카드(`strategy-list.tsx`)가 맡는다. */}
      <AuthForm mode="sign-up" redirectTo="/onboarding" />
    </SplitScreenShell>
  );
}
