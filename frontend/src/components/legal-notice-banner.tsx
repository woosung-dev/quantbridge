// Sprint 11 Phase B — 법무 임시 고지 배너. 모든 페이지 상단에 고정 (layout.tsx).
// 정식 변호사 검토본 (D-5 A안) 배포 전까지 표시. H2 말 (~2026-06-30) 교체 예정.

import Link from "next/link";

import { LEGAL_LINKS } from "@/lib/legal-links";

export function LegalNoticeBanner() {
  return (
    <div
      role="note"
      className="w-full border-b border-amber-300 bg-amber-100 px-4 py-1.5 text-center text-[11px] text-amber-900"
    >
      <strong>Beta:</strong> QuantBridge is provided as-is. See{" "}
      <Link href={LEGAL_LINKS.disclaimer} className="underline hover:text-amber-950">
        Disclaimer
      </Link>{" "}
      ·{" "}
      <Link href={LEGAL_LINKS.terms} className="underline hover:text-amber-950">
        Terms
      </Link>{" "}
      ·{" "}
      <Link href={LEGAL_LINKS.privacy} className="underline hover:text-amber-950">
        Privacy
      </Link>
      . <span className="opacity-75">(법무 임시 — H2 말 정식 변호사 교체 예정)</span>
    </div>
  );
}
