// 거래소 지원 현황 표 — 마케팅 공동 원장(_KIT.md §4.1). 랜딩·웨이트리스트가 셀 단위로 공유.
// 지원 행은 chip done, 미지원 행은 chip + 무데이터 셀(title 로 사유). 표기는 한글 통일.

import {
  EMPTY_CELL,
  EXCHANGE_NO_ENV_TITLE,
  EXCHANGE_NO_SCOPE_TITLE,
  EXCHANGE_SUPPORT,
  EXCHANGE_TABLE_CAPTION,
} from "@/lib/marketing-canon";

import { TableScrollRegion } from "./table-scroll-region";

/** aria-label 은 페이지 문맥에 맞게 넘긴다(랜딩 vs 웨이트리스트). */
// ★가로 스크롤 영역은 키보드로 도달할 수 있어야 한다(WCAG 2.1.1) — axe
// `scrollable-region-focusable`(serious). `.table-wrap` 은 `overflow-x` 만 갖고 내부에 포커스
// 가능한 요소가 없어서, 375px 에서 키보드 사용자는 넘친 열을 볼 방법이 없었다(2026-09-06 실측).
// `role="region"` + 이름을 함께 줘야 탭 정지가 무엇인지 읽힌다.
export function ExchangeSupportTable({ ariaLabel }: { ariaLabel?: string }) {
  return (
    <TableScrollRegion label={ariaLabel ?? "거래소 지원 현황"}>
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
    </TableScrollRegion>
  );
}
