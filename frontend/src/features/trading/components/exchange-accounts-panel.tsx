"use client";

import { Trash2, WalletIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { useDeleteExchangeAccount, useExchangeAccounts } from "../hooks";
import { RegisterExchangeAccountDialog } from "./register-exchange-account-dialog";
import { TradingEmptyState } from "./trading-empty-state";

// C-2: Demo/Live 배지 컴포넌트.
// null/undefined 가드 필수 — ExchangeAccount.mode 는 string (nullable 아님이지만 방어적으로 처리).
function ModeBadge({ mode }: { mode: string | null | undefined }) {
  if (mode === "demo") {
    return (
      <Badge
        variant="outline"
        className="border-amber-500 text-amber-600 uppercase text-xs font-semibold"
      >
        DEMO
      </Badge>
    );
  }
  if (mode === "live") {
    return (
      <Badge
        variant="outline"
        className="border-green-500 text-green-600 uppercase text-xs font-semibold"
      >
        LIVE
      </Badge>
    );
  }
  return (
    <Badge
      variant="outline"
      className="border-gray-400 text-gray-500 uppercase text-xs"
    >
      {mode ?? "UNKNOWN"}
    </Badge>
  );
}

export function ExchangeAccountsPanel() {
  const { data, isError } = useExchangeAccounts();
  const deleteAccount = useDeleteExchangeAccount();

  if (isError) {
    return (
      <section className="p-4 border rounded">
        <p className="text-sm text-[color:var(--destructive)]">
          거래소 계정 목록을 불러오지 못했습니다.
        </p>
      </section>
    );
  }
  if (!data) return null;

  return (
    <section className="p-4 border rounded">
      <div className="flex items-center justify-between mb-3">
        <h2 className="font-semibold">Exchange Accounts</h2>
        <RegisterExchangeAccountDialog />
      </div>
      {data.length === 0 ? (
        <TradingEmptyState
          icon={WalletIcon}
          title="연결된 거래소 계정이 없습니다."
          description="위 '계정 추가' 버튼으로 거래소 계정을 연결하세요."
        />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[520px]">
            <thead>
              <tr className="text-left text-[color:var(--text-secondary)]">
                <th className="py-1 font-medium">Exchange</th>
                <th className="py-1 font-medium">Mode</th>
                <th className="py-1 font-medium">Label</th>
                <th className="py-1 font-medium">API Key</th>
                <th className="py-1 w-8"></th>
              </tr>
            </thead>
            <tbody>
              {data.map((a) => (
                <tr key={a.id} className="border-t">
                  <td className="py-1.5">{a.exchange}</td>
                  <td className="py-1.5">
                    <ModeBadge mode={a.mode} />
                  </td>
                  <td className="py-1.5">{a.label ?? "—"}</td>
                  <td className="py-1.5 font-mono text-xs">{a.api_key_masked}</td>
                  <td className="py-1.5">
                    <button
                      type="button"
                      onClick={() => deleteAccount.mutate(a.id)}
                      disabled={deleteAccount.isPending}
                      aria-label="계정 삭제"
                      className="text-[color:var(--destructive)] hover:opacity-70 disabled:opacity-40 transition-opacity"
                    >
                      <Trash2 className="size-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
