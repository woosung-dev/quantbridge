// 공용 포매터 — 도메인(backtest·strategy·live-sessions)이 같은 규약을 한 벌로 쓴다.

import { EMPTY_CELL } from "@/lib/labels";

/**
 * ISO(또는 epoch ms) → `YYYY-MM-DD HH:mm` (UTC). 값이 없거나 파싱 불가면
 * 무데이터 셀 표기(EMPTY_CELL)를 돌려준다.
 * toLocaleString 류는 실행 환경 타임존에 따라 결과가 갈려 캐논(모든 화면이 같은 사실을
 * 말한다)과 컴포넌트 테스트를 깨뜨리므로 쓰지 않는다.
 */
export function formatDateTime(iso: string | number | null | undefined): string {
  if (!iso) return EMPTY_CELL;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return EMPTY_CELL;
  const yyyy = d.getUTCFullYear();
  const mo = String(d.getUTCMonth() + 1).padStart(2, "0");
  const dd = String(d.getUTCDate()).padStart(2, "0");
  const hh = String(d.getUTCHours()).padStart(2, "0");
  const mm = String(d.getUTCMinutes()).padStart(2, "0");
  return `${yyyy}-${mo}-${dd} ${hh}:${mm}`;
}
