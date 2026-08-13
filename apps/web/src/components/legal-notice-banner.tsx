// 전 페이지 상단 고정 법적 고지 배너 (layout.tsx). C 디자인 언어 재스킨 — 한국어 · em-dash 0.
// 법적 고지이므로 제거하지 않는다. warn 토큰(카본 위 앰버) 얇은 줄로 둔다.

import Link from "next/link";

import { LEGAL_LINKS } from "@/lib/legal-links";

const LINK_CLASS =
  "inline-block min-h-11 px-2 py-2.5 align-middle underline hover:opacity-80 md:min-h-0 md:px-0 md:py-0";

export function LegalNoticeBanner() {
  return (
    <div
      role="note"
      className="w-full border-b border-[color:var(--warn)]/30 bg-[color:var(--warn-soft)] px-4 py-1.5 text-center text-[11px] text-[color:var(--warn)]"
    >
      <strong>고지.</strong> QuantBridge 는 있는 그대로 제공되는 공개 전 개인 워크스페이스입니다.
      투자 자문이 아니며 트레이딩 결과는 사용자 책임입니다.{" "}
      <Link href={LEGAL_LINKS.disclaimer} className={LINK_CLASS}>
        면책조항
      </Link>{" "}
      ·{" "}
      <Link href={LEGAL_LINKS.terms} className={LINK_CLASS}>
        이용약관
      </Link>{" "}
      ·{" "}
      <Link href={LEGAL_LINKS.privacy} className={LINK_CLASS}>
        개인정보 처리방침
      </Link>
    </div>
  );
}
