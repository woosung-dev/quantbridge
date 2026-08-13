// 활성 라이브 세션이 참조하는 거래소 계정 잔고 카드를 렌더한다.
"use client";

import { StateBox } from "@/components/state-box";
import { useAccountBalances } from "@/features/trading/hooks";
import type { ExchangeAccount } from "@/features/trading/schemas";

type AccountTarget = Pick<ExchangeAccount, "id"> & { label: string };

function usagePercent(total: string | null, free: string | null): number | null {
  if (total === null || free === null) return null;
  const totalValue = Number(total);
  const freeValue = Number(free);
  if (!Number.isFinite(totalValue) || !Number.isFinite(freeValue)) return null;
  if (totalValue === 0) return 0;
  return Math.max(0, Math.min(100, (freeValue / totalValue) * 100));
}

export function AccountBalanceSection({ accounts }: { accounts: readonly AccountTarget[] }) {
  const balances = useAccountBalances(accounts);

  if (accounts.length === 0) {
    return (
      <div className="card" data-testid="account-balance-section">
        <div className="card-body">
          <StateBox
            testId="account-balance-empty"
            title="활성 라이브 세션이 없습니다."
            body="활성 세션이 참조하는 거래소 계정의 잔고만 표시합니다."
          />
        </div>
      </div>
    );
  }

  return (
    <div className="kpi-row" data-testid="account-balance-section">
      {accounts.map((account, index) => {
        const query = balances[index];
        const balance = query?.data;
        const percent = usagePercent(balance?.total ?? null, balance?.free ?? null);
        const asset = balance?.asset ?? "USDT";

        return (
          <article className="card kpi" key={account.id}>
            <p className="kpi-label">계정 잔고</p>
            <p className="kpi-value mono" data-testid={`balance-total-${account.id}`}>
              {query?.isLoading ? "불러오는 중" : balance?.total ?? "확인 불가"}
              {balance?.total !== null && balance?.total !== undefined ? ` ${asset}` : null}
            </p>
            <p className="kpi-label">사용 가능</p>
            <p className="kpi-value mono" data-testid={`balance-free-${account.id}`}>
              {query?.isLoading ? "불러오는 중" : balance?.free ?? "확인 불가"}
              {balance?.free !== null && balance?.free !== undefined ? ` ${asset}` : null}
            </p>
            {query?.isLoading ? null : query?.isError ? (
              <p className="kpi-foot">잔고를 불러오지 못했습니다.</p>
            ) : !balance?.supported ? (
              <p className="kpi-foot">{balance?.reason ?? "잔고 조회를 지원하지 않습니다."}</p>
            ) : percent === null ? (
              <p className="kpi-foot">확인 불가</p>
            ) : (
              <>
                <div
                  className="meter"
                  aria-label={`사용 가능 잔고 ${percent.toFixed(0)}%`}
                  data-testid={`balance-meter-${account.id}`}
                >
                  <span style={{ width: `${percent}%` }} />
                </div>
                <p className="kpi-foot">사용 가능 {percent.toFixed(0)}%</p>
              </>
            )}
            <p className="card-sub">
              <span className="chip">{account.label}</span>
              {balance?.fetched_at ? ` · ${balance.fetched_at}` : null}
            </p>
          </article>
        );
      })}
    </div>
  );
}
