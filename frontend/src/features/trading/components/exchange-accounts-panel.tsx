"use client";

import { WalletIcon } from "lucide-react";
import { useExchangeAccounts } from "../hooks";
import { TradingEmptyState } from "./trading-empty-state";

export function ExchangeAccountsPanel() {
  const { data, isError } = useExchangeAccounts();

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
      <h2 className="font-semibold mb-3">Exchange Accounts</h2>
      {data.length === 0 ? (
        <TradingEmptyState
          icon={WalletIcon}
          title="연결된 거래소 계정이 없습니다."
          description="계정을 추가하고 자동매매를 시작하세요."
          ctaLabel="계정 추가"
          ctaHref="/trading"
        />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[520px]">
            <thead>
              <tr>
                <th>Exchange</th>
                <th>Mode</th>
                <th>Label</th>
                <th>API Key</th>
              </tr>
            </thead>
            <tbody>
              {data.map((a) => (
                <tr key={a.id} className="border-t">
                  <td>{a.exchange}</td>
                  <td>{a.mode}</td>
                  <td>{a.label ?? "—"}</td>
                  <td className="font-mono">{a.api_key_masked}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
