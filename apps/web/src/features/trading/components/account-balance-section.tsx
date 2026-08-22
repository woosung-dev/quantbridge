// 활성 라이브 세션이 참조하는 거래소 계정 잔고 카드를 렌더한다.
// 프로토타입 screen-01:1171-1197 의 1카드-1지표 관례 — 계정 잔고와 사용 가능을 각각의
// .card.kpi 로 나누고, 로딩·에러는 §01 형제 KPI 들과 같은 StatValue 규율로 표기한다.
"use client";

import { Fragment } from "react";

import { StateBox } from "@/components/state-box";
import { StatValue } from "@/components/stat-value";
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
        const isPending = query?.isLoading === true;
        const isError = query?.isError === true;
        // 무데이터 사유는 계정 잔고 카드 한 곳에만 적는다(같은 조회의 사유를 두 번 반복하지 않는다).
        const reasonFoot = isError
          ? "잔고를 불러오지 못했습니다."
          : !isPending && balance != null && !balance.supported
            ? (balance.reason ?? "잔고 조회를 지원하지 않습니다.")
            : null;

        return (
          <Fragment key={account.id}>
            <article className="card kpi">
              <p className="kpi-label">계정 잔고</p>
              <p className="kpi-value mono" data-testid={`balance-total-${account.id}`}>
                <StatValue isError={isError} isPending={isPending}>
                  {balance?.total != null ? `${balance.total} ${asset}` : "확인 불가"}
                </StatValue>
              </p>
              {reasonFoot != null ? <p className="kpi-foot">{reasonFoot}</p> : null}
              <p className="card-sub">
                <span className="chip">{account.label}</span>
                {balance?.fetched_at ? ` · ${balance.fetched_at}` : null}
              </p>
            </article>

            <article className="card kpi">
              <p className="kpi-label">사용 가능</p>
              <p className="kpi-value mono" data-testid={`balance-free-${account.id}`}>
                <StatValue isError={isError} isPending={isPending}>
                  {balance?.free != null ? `${balance.free} ${asset}` : "확인 불가"}
                </StatValue>
              </p>
              {isPending || isError ? null : percent === null ? (
                <p className="kpi-foot">확인 불가</p>
              ) : (
                <>
                  <div
                    className="meter"
                    role="progressbar"
                    aria-label={`사용 가능 잔고 ${percent.toFixed(0)}%`}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuenow={percent}
                    data-testid={`balance-meter-${account.id}`}
                  >
                    <span style={{ width: `${percent}%` }} />
                  </div>
                  <p className="kpi-foot">사용 가능 {percent.toFixed(0)}%</p>
                </>
              )}
              <p className="card-sub">
                <span className="chip">{account.label}</span>
              </p>
            </article>
          </Fragment>
        );
      })}
    </div>
  );
}
