"use client";

// 계정 표시 + 로그아웃 + 계정 삭제 — 구 Clerk `<UserButton/>` 의 자리(ADR-034).
// ★프리빌트 위젯이 아니라 우리 DOM 이므로 BL-305/339 의 「Clerk 내부 root 가 0×0 으로 접힌다」
//   함정이 구조적으로 사라진다. 터치 타깃은 여기서 직접 보장한다(BL-356~359, ≥44pt).

import { useState } from "react";
import { useRouter } from "next/navigation";
import { LogOut, Trash2 } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { clearAuthTokenCache, deleteAccount, signOut, useSession } from "@/lib/auth-client";

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
      <button
        type="button"
        className={`inline-flex items-center justify-center rounded-[var(--r)] ${box}`}
        onClick={() => {
          setDeleteError(null);
          setConfirmOpen(true);
        }}
        aria-label="계정 삭제"
        title="계정 삭제"
      >
        <Trash2 aria-hidden="true" className="size-4" />
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
              {deleting ? "삭제 중…" : "계정 삭제"}
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </span>
  );
}
