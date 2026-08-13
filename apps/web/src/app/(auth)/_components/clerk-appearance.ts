// Clerk 위젯 appearance — C 디자인 언어 정렬(sign-in/sign-up 공유). screen-15-login.html 이식.
// Clerk 내부 DOM 은 재구성 불가라 elements 클래스만 C 토큰으로 맞춘다. 헤더는 셸이 이미 그리므로 숨긴다.
// 포커스 링은 전역 카퍼 :focus-visible 이 담당하므로 여기서 자체 ring 을 주지 않는다(이중 링 방지).
// ★colorPrimary 는 clerk-theme-bridge.tsx 단일 소스이므로 여기서 하드코딩하지 않는다.

// 타입은 <SignIn appearance={...}> 호출부에서 Clerk Appearance 로 구조적 검증된다.
export const CLERK_C_APPEARANCE = {
  elements: {
    rootBox: "w-full motion-safe:animate-[fadeInUp_220ms_ease-out_60ms_both]",
    card: "shadow-none bg-transparent border-0 p-0",
    // 셸의 auth-form-head 가 제목을 그리므로 Clerk 내부 헤더는 감춘다(중복 방지).
    header: "hidden",
    formButtonPrimary:
      "bg-[color:var(--copper)] hover:bg-[color:var(--copper-hover)] text-[color:var(--copper-ink)] rounded-[var(--r)] normal-case text-sm font-semibold h-[42px] transition-colors duration-200 ease-out",
    formFieldInput:
      "rounded-[var(--r)] border border-[color:var(--line)] bg-[color:var(--card-2)] h-[42px] text-[color:var(--ink)] focus:border-[color:var(--line-2)] transition-colors duration-200 ease-out",
    formFieldLabel: "text-[color:var(--ink-2)] text-[0.78rem] font-semibold",
    socialButtonsBlockButton:
      "rounded-[var(--r)] border border-[color:var(--line)] bg-[color:var(--card-2)] hover:bg-[color:var(--card-3)] text-[color:var(--ink)] h-[42px] transition-colors duration-200 ease-out",
    footerActionLink:
      "text-[color:var(--copper)] hover:text-[color:var(--copper-hover)] font-semibold transition-colors duration-150",
    dividerLine: "bg-[color:var(--line)]",
    dividerText: "text-[color:var(--ink-3)]",
  },
  variables: {
    // Clerk 전역 반경 — C 캐논 var(--r)=12px 와 동일 값. colorPrimary 는 브릿지 SSOT.
    borderRadius: "12px",
  },
};
