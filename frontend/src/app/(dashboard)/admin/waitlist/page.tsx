"use client";

// Sprint 11 Phase C — Admin waitlist dashboard.
// Clerk JWT + BE WAITLIST_ADMIN_EMAILS 화이트리스트 기반 인증 (FE 는 403 수신 시 안내).
// 상태 필터 + approve 버튼 + 발송 상태 뱃지.

import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { useAdminWaitlistList, useApproveWaitlist } from "@/features/waitlist/hooks";
import type {
  WaitlistApplicationResponse,
  WaitlistStatus,
} from "@/features/waitlist/schemas";
import { ApiError } from "@/lib/api-client";

const STATUS_FILTERS: { value: WaitlistStatus | "all"; label: string }[] = [
  { value: "all", label: "All" },
  { value: "pending", label: "Pending" },
  { value: "invited", label: "Invited" },
  { value: "joined", label: "Joined" },
  { value: "rejected", label: "Rejected" },
];

function StatusBadge({ status }: { status: WaitlistStatus }) {
  const styles: Record<WaitlistStatus, string> = {
    pending: "bg-amber-100 text-amber-900",
    invited: "bg-blue-100 text-blue-900",
    joined: "bg-green-100 text-green-900",
    rejected: "bg-gray-200 text-gray-800",
  };
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${styles[status]}`}
    >
      {status}
    </span>
  );
}

export default function AdminWaitlistPage() {
  const [filter, setFilter] = useState<WaitlistStatus | "all">("pending");

  const query = filter === "all" ? {} : { status: filter };
  const { data, isPending, error } = useAdminWaitlistList(query);
  const approve = useApproveWaitlist({
    onSuccess: (approved) => {
      toast.success(`Invite sent to ${approved.email}`);
    },
    onError: (err) => {
      const msg = err instanceof Error ? err.message : "Approval failed";
      toast.error(msg);
    },
  });

  // 403 렌더 (admin 권한 부족)
  const errStatus =
    error instanceof ApiError ? error.status : undefined;

  return (
    <div className="mx-auto max-w-[1100px] space-y-6 px-6 py-8">
      <header className="space-y-2">
        <h1 className="font-display text-2xl font-bold">Waitlist Admin</h1>
        <p className="text-sm text-[color:var(--text-secondary)]">
          Review pending applications and send Beta invites via Resend.
        </p>
      </header>

      <div className="flex flex-wrap items-center gap-2">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.value}
            type="button"
            onClick={() => setFilter(f.value)}
            className={`rounded-full border px-3 py-1 text-xs transition ${
              filter === f.value
                ? "border-[color:var(--accent)] bg-[color:var(--accent)] text-white"
                : "border-[color:var(--border)] bg-transparent text-[color:var(--text-secondary)]"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {errStatus === 403 ? (
        <div className="rounded-md border-l-4 border-red-500 bg-red-50 p-4 text-sm text-red-900">
          <strong>Admin access required.</strong> Your email is not on the admin
          allowlist. Contact the QuantBridge operator.
        </div>
      ) : null}

      {isPending && !error ? (
        <p className="text-sm text-[color:var(--text-tertiary)]">Loading…</p>
      ) : null}

      {error && errStatus !== 403 ? (
        <div className="rounded-md border-l-4 border-red-500 bg-red-50 p-4 text-sm text-red-900">
          Failed to load waitlist: {error.message}
        </div>
      ) : null}

      {data && data.items.length === 0 ? (
        <p className="text-sm text-[color:var(--text-tertiary)]">
          No applications match this filter.
        </p>
      ) : null}

      {data && data.items.length > 0 ? (
        <div className="overflow-x-auto rounded-md border border-[color:var(--border)]">
          <table className="w-full text-left text-sm">
            <thead className="bg-[color:var(--bg-muted)] text-xs uppercase text-[color:var(--text-tertiary)]">
              <tr>
                <th className="px-4 py-3">Email</th>
                <th className="px-4 py-3">TV</th>
                <th className="px-4 py-3">Capital</th>
                <th className="px-4 py-3">Pine</th>
                <th className="px-4 py-3">Pain Point</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Created</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((item: WaitlistApplicationResponse) => (
                <tr
                  key={item.id}
                  className="border-t border-[color:var(--border)] align-top"
                >
                  <td className="px-4 py-3 font-medium">{item.email}</td>
                  <td className="px-4 py-3">{item.tv_subscription}</td>
                  <td className="px-4 py-3">{item.exchange_capital}</td>
                  <td className="px-4 py-3">{item.pine_experience}</td>
                  <td className="px-4 py-3">
                    <span className="line-clamp-3 block max-w-[320px] text-xs text-[color:var(--text-secondary)]">
                      {item.pain_point}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={item.status} />
                  </td>
                  <td className="px-4 py-3 text-xs text-[color:var(--text-tertiary)]">
                    {new Date(item.created_at).toLocaleDateString("ko-KR")}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {item.status === "pending" ? (
                      <Button
                        type="button"
                        size="sm"
                        disabled={approve.isPending}
                        onClick={() => approve.mutate(item.id)}
                      >
                        {approve.isPending ? "Sending…" : "Approve + Invite"}
                      </Button>
                    ) : (
                      <span className="text-xs text-[color:var(--text-tertiary)]">
                        —
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {data ? (
        <p className="text-xs text-[color:var(--text-tertiary)]">
          Total: {data.total}
        </p>
      ) : null}
    </div>
  );
}
