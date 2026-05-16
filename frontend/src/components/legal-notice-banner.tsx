// Sprint 11 Phase B — Beta 단계 고지 배너. 모든 페이지 상단에 고정 (layout.tsx).
// 정식 변호사 검토본 (D-5 A안) 배포 전까지 표시. H2 말 (~2026-06-30) 교체 예정.
//
// Sprint 61 T-2 (BL-339): 모바일 touch target ≥44pt — 링크 padding 확대 (14pt 위반 fix).

import Link from "next/link";

import { LEGAL_LINKS } from "@/lib/legal-links";

const LINK_CLASS =
  "inline-block min-h-11 px-2 py-2.5 align-middle underline hover:text-amber-950 md:min-h-0 md:px-0 md:py-0";

export function LegalNoticeBanner() {
  return (
    <div
      role="note"
      className="w-full border-b border-amber-300 bg-amber-100 px-4 py-1.5 text-center text-[11px] text-amber-900"
    >
      <strong>Beta:</strong> QuantBridge is provided as-is. See{" "}
      <Link href={LEGAL_LINKS.disclaimer} className={LINK_CLASS}>
        Disclaimer
      </Link>{" "}
      ·{" "}
      <Link href={LEGAL_LINKS.terms} className={LINK_CLASS}>
        Terms
      </Link>{" "}
      ·{" "}
      <Link href={LEGAL_LINKS.privacy} className={LINK_CLASS}>
        Privacy
      </Link>
      . <span className="opacity-75">(Beta 단계 — H2 말 정식 변호사 검토본 교체 예정)</span>
    </div>
  );
}
