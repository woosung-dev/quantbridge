"use client";

// 계정 표시 + 로그아웃 + 계정 삭제 — 구 Clerk `<UserButton/>` 의 자리(ADR-034).
// ★프리빌트 위젯이 아니라 우리 DOM 이므로 BL-305/339 의 「Clerk 내부 root 가 0×0 으로 접힌다」
//   함정이 구조적으로 사라진다. 터치 타깃은 여기서 직접 보장한다(BL-356~359, ≥44pt).

import { useState } from "react";
import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useAuthCtx } from "@/hooks/use-auth-ctx";
import { clearAuthTokenCache, deleteAccount, signOut } from "@/lib/auth-client";

/** 표시용 머리글자 — 이름 → 이메일 → 물음표 순으로 떨어진다. */
function initialOf(name: string | null | undefined, email: string | null | undefined): string {
  const source = (name ?? "").trim() || (email ?? "").trim();
  return source ? source.charAt(0).toUpperCase() : "?";
}

/**
 * @param showIdentity 아바타 옆에 계정 이름·이메일을 함께 그린다(캐논 `.account-name`/`.account-sub`).
 *   ★사이드바 전용이다 — 상단바 인스턴스는 320px 에서 폭이 없다(아래 §폭 주석).
 */
export function AccountButton({
  size = "sm",
  showIdentity = false,
}: {
  size?: "sm" | "lg";
  showIdentity?: boolean;
}) {
  const router = useRouter();
  const { user } = useAuthCtx();
  const box = size === "lg" ? "size-11 min-h-11 min-w-11" : "size-9 min-h-9 min-w-9";
  // 표시용 신원 — 이름 → 이메일 순. 둘 다 없으면 신원 블록 자체를 그리지 않는다
  // (「계정」 같은 고정 문자열은 어느 계정인지 답하지 못하면서 답한 것처럼 보인다).
  const displayName = (user?.name ?? "").trim() || (user?.email ?? "").trim();

  const [confirmOpen, setConfirmOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const handleSignOut = async () => {
    // ★캐시를 먼저 비운다 — 이 순서가 뒤집히면 로그아웃 직후 남은 JWT 로 API 호출이 한 번 더 나간다.
    clearAuthTokenCache();
    await signOut();
    router.replace("/sign-in");
    router.refresh();
  };

  const handleDelete = async () => {
    setDeleting(true);
    setDeleteError(null);
    const { error } = await deleteAccount();
    setDeleting(false);
    if (error) {
      // ★서버가 「돈을 멈추지 못했다」고 답하면 **계정은 그대로 남는다**(fail-closed).
      //   그 사실을 사용자에게 그대로 말한다 — 조용히 닫으면 지워진 줄 안다.
      setDeleteError(error.message ?? "계정 삭제에 실패했습니다. 잠시 후 다시 시도해 주세요.");
      return;
    }
    setConfirmOpen(false);
    router.replace("/sign-in");
    router.refresh();
  };

  return (
    // 신원을 그릴 때만 컨테이너 폭을 채우고 줄바꿈을 허용한다 — 상단바 인스턴스는 콘텐츠 폭 그대로.
    // 232px 사이드바에서 아바타+신원+로그아웃+「계정 지우기」를 한 줄에 넣으면 신원이 55px 로
    // 눌려 이메일이 `e2...` 가 된다. 좁으면 액션이 둘째 줄로 내려가게 두는 편이 읽힌다.
    <span
      className={`inline-flex items-center gap-2 ${showIdentity ? "w-full min-w-0 flex-wrap" : ""}`}
    >
      <span
        aria-hidden="true"
        className={`inline-flex shrink-0 items-center justify-center rounded-full border border-[color:var(--line)] bg-[color:var(--surface-2)] text-sm font-semibold ${box}`}
        data-testid="account-avatar"
      >
        {initialOf(user?.name, user?.email)}
      </span>
      {/* 신원 블록 — 캐논 `_kit.html` 의 `.account-name` + `.account-sub` 자리(2026-09-06).
          종전에는 사이드바가 `"계정"` 문자열을 하드코딩해 **어느 계정으로 들어와 있는지 화면이
          답하지 못했다**. `min-w-0` + truncate 로 232px 사이드바 안에서 줄바꿈 없이 줄인다. */}
      {showIdentity && displayName ? (
        // flex-1 + min-w-0 — 아바타·로그아웃·「계정 지우기」는 고정 폭이라 줄어들 수 없다.
        // 신원 블록이 남는 폭을 흡수해야 280px 드로어에서 마지막 버튼이 잘리지 않는다(2026-09-06 실측).
        <span className="flex min-w-0 flex-1 basis-28 flex-col">
          <span className="account-name truncate" title={displayName}>
            {displayName}
          </span>
          {user?.name && user?.email ? (
            <span className="account-sub truncate" title={user.email}>
              {user.email}
            </span>
          ) : null}
        </span>
      ) : null}
      {/* ★레일 구간(769~1024px, --sidebar-w 64px) 숨김 — **사이드바 인스턴스에만** 적용한다.
          이 컴포넌트는 상단바에도 렌더되므로 버튼 자체에 미디어 숨김을 걸면 레일 구간에서
          로그아웃/삭제 경로가 화면 전체에서 사라진다(codex P2, 2026-08-18). 스코프는 globals 의
          `.sidebar .qb-acct-action` 언레이어드 규칙(min-width:769 and max-width:1024, 양끝 포함 —
          Tailwind max-[N]: 은 경계 미포함이라 raw 미디어가 정본)이 담당하고, 그 구간의 계정
          경로는 상단바 인스턴스(dashboard-header, min-[1025px]:hidden)가 잇는다.
          hover 배경은 같은 셸의 .nav-item/.hamburger 관용구(var(--card-2)). */}
      <button
        type="button"
        className={`qb-acct-action inline-flex items-center justify-center rounded-[var(--r)] text-[color:var(--ink-2)] transition-colors hover:bg-[color:var(--card-2)] hover:text-[color:var(--ink)] ${box}`}
        onClick={handleSignOut}
        aria-label={user?.email ? `${user.email} 로그아웃` : "로그아웃"}
        title="로그아웃"
      >
        <LogOut aria-hidden="true" className="size-4" />
      </button>
      {/* ★위계 강등 — 「내 계정 지우기」는 로그아웃과 동급 아이콘 버튼이 아니라 작은 muted 텍스트
          버튼으로 둔다. 기본은 ink-3 무채색, hover 에서만 destructive 톤. 확인 다이얼로그 플로우는 유지.
          터치 타깃 높이는 size 프롭이 계속 보장한다(≥44pt @ lg). */}
      <button
        type="button"
        className={`qb-acct-action inline-flex items-center justify-center rounded-[var(--r)] px-1.5 text-[0.72rem] whitespace-nowrap text-[color:var(--ink-3)] transition-colors hover:bg-[color:var(--destructive-subtle)] hover:text-[color:var(--destructive)] ${size === "lg" ? "min-h-11" : "min-h-9"}`}
        onClick={() => {
          setDeleteError(null);
          setConfirmOpen(true);
        }}
        // ★★라벨에 「계정 삭제」라는 **부분 문자열이 들어가면 안 된다.** 거래소 계정 행의
        //   삭제 버튼이 `aria-label="계정 삭제"` 이고 Playwright 의 `getByRole(name)` 은
        //   **부분 문자열 매칭**이라, 「내 계정 삭제」처럼 상위 문자열로 바꿔도 여전히 둘 다
        //   잡혀 기존 e2e(#7)가 strict-mode 로 죽는다. 2026-08-17 에 두 번 밟고 확정했다.
        aria-label="내 계정 지우기"
        title="내 계정 지우기"
      >
        계정 지우기
      </button>

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>계정을 삭제할까요?</DialogTitle>
            <DialogDescription>
              되돌릴 수 없습니다. 삭제하면 <strong>실행 중인 라이브 세션이 전부 정지</strong>되고
              TradingView 웹훅 시크릿이 즉시 폐기되며, 전략은 보관 처리됩니다. 백테스트 기록과
              거래소 계정 정보는 남지만 더 이상 접근할 수 없습니다.
            </DialogDescription>
          </DialogHeader>
          {/* ★Better Auth 는 민감 동작에 **최근 세션**을 요구한다(`session.freshAge` 기본 1일).
              오래된 세션이면 `beforeDelete` 가 돌기도 전에 거부되고, 화면에는 이유 없는 실패로
              보인다. 문서가 지시하는 처방이 「다시 로그인하도록 안내」라 여기에 상시로 둔다
              (2026-08-17 codex 적대 리뷰 P2). */}
          <p className="field-hint">
            마지막 로그인이 하루를 넘겼다면 보안상 삭제가 거부됩니다. 그때는 로그아웃 후 다시
            로그인한 뒤 시도해 주세요.
          </p>
          {deleteError ? (
            <p className="field-error" role="alert">
              <span>{deleteError}</span>
            </p>
          ) : null}
          <DialogFooter>
            <button
              type="button"
              className="btn"
              onClick={() => setConfirmOpen(false)}
              disabled={deleting}
            >
              취소
            </button>
            <button
              type="button"
              className="btn btn-danger"
              onClick={handleDelete}
              disabled={deleting}
              aria-busy={deleting}
            >
              {deleting ? "지우는 중…" : "영구 삭제"}
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </span>
  );
}
