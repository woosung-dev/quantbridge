"use client";

// 계정 표시 + 로그아웃 — 구 Clerk `<UserButton/>` 의 자리(ADR-034).
// ★프리빌트 위젯이 아니라 우리 DOM 이므로 BL-305/339 의 「Clerk 내부 root 가 0×0 으로 접힌다」
//   함정이 구조적으로 사라진다. 터치 타깃은 여기서 직접 보장한다(BL-356~359, ≥44pt).

import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";

import { clearAuthTokenCache, signOut, useSession } from "@/lib/auth-client";

/** 표시용 머리글자 — 이름 → 이메일 → 물음표 순으로 떨어진다. */
function initialOf(name: string | null | undefined, email: string | null | undefined): string {
  const source = (name ?? "").trim() || (email ?? "").trim();
  return source ? source.charAt(0).toUpperCase() : "?";
}

export function AccountButton({ size = "sm" }: { size?: "sm" | "lg" }) {
  const router = useRouter();
  const { data } = useSession();
  const user = data?.user;
  const box = size === "lg" ? "size-11 min-h-11 min-w-11" : "size-9 min-h-9 min-w-9";

  const handleSignOut = async () => {
    // ★캐시를 먼저 비운다 — 이 순서가 뒤집히면 로그아웃 직후 남은 JWT 로 API 호출이 한 번 더 나간다.
    clearAuthTokenCache();
    await signOut();
    router.replace("/sign-in");
    router.refresh();
  };

  return (
    <span className="inline-flex items-center gap-2">
      <span
        aria-hidden="true"
        className={`inline-flex shrink-0 items-center justify-center rounded-full border border-[color:var(--line)] bg-[color:var(--surface-2)] text-sm font-semibold ${box}`}
        data-testid="account-avatar"
      >
        {initialOf(user?.name, user?.email)}
      </span>
      <button
        type="button"
        className={`inline-flex items-center justify-center rounded-[var(--r)] ${box}`}
        onClick={handleSignOut}
        aria-label={user?.email ? `${user.email} 로그아웃` : "로그아웃"}
        title="로그아웃"
      >
        <LogOut aria-hidden="true" className="size-4" />
      </button>
    </span>
  );
}
