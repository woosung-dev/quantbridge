// Clerk 로그인 페이지 — C 디자인 언어 셸 + 공유 appearance(clerk-appearance.ts).
// colorPrimary 는 clerk-theme-bridge.tsx 가 테마별 코퍼로 주입 — 여기서 하드코딩 금지.
import { SignIn } from "@clerk/nextjs";

import { CLERK_C_APPEARANCE } from "../../_components/clerk-appearance";
import { SplitScreenShell } from "../../_components/split-screen-shell";

export default function SignInPage() {
  return (
    <SplitScreenShell mode="sign-in">
      <SignIn appearance={CLERK_C_APPEARANCE} />
    </SplitScreenShell>
  );
}
