// 거래소 지원 현황 표 — 마케팅 공동 원장(_KIT.md §4.1). 랜딩·웨이트리스트가 셀 단위로 공유.
// 지원 행은 chip done, 미지원 행은 chip + 무데이터 셀(title 로 사유). 표기는 한글 통일.

import {
  EMPTY_CELL,
  EXCHANGE_NO_ENV_TITLE,
  EXCHANGE_NO_SCOPE_TITLE,
  EXCHANGE_SUPPORT,
  EXCHANGE_TABLE_CAPTION,
} from "@/lib/marketing-canon";

/** aria-label 은 페이지 문맥에 맞게 넘긴다(랜딩 vs 웨이트리스트). */
export function ExchangeSupportTable({ ariaLabel }: { ariaLabel?: string }) {
  return (
    <div className="table-wrap">
      <table className="trades" aria-label={ariaLabel}>
        <caption className="dim sup-cap">{EXCHANGE_TABLE_CAPTION}</caption>
        <thead>
          <tr>
            <th scope="col">거래소</th>
            <th scope="col">환경</th>
            <th scope="col">상태</th>
            <th scope="col">확인한 범위</th>
          </tr>
        </thead>
        <tbody>
          {EXCHANGE_SUPPORT.map((row) => (
            <tr key={`${row.exchange}-${row.environment ?? "unsupported"}`}>
              <td className="mono-l">{row.exchange}</td>
              {row.environment === null ? (
                <td className="mono-l dim" title={EXCHANGE_NO_ENV_TITLE}>
                  {EMPTY_CELL}
                </td>
              ) : (
                <td className="mono-l">{row.environment}</td>
              )}
              <td>
                {row.status === "supported" ? (
                  <span className="chip done">
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                    지원
                  </span>
                ) : (
                  <span className="chip">지원하지 않음</span>
                )}
              </td>
              {row.scope === null ? (
                <td className="dim" title={EXCHANGE_NO_SCOPE_TITLE}>
                  {EMPTY_CELL}
                </td>
              ) : (
                <td>{row.scope}</td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
