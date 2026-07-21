// 랜딩 푸터 (.lp-foot) — 개인 프로젝트 표기 + 앵커 링크. screen-14-landing.html 이식.
const FOOT_LINKS = [
  { href: "#features", label: "기능" },
  { href: "#how", label: "작동 방식" },
  { href: "#support", label: "지원 현황" },
  { href: "#faq", label: "FAQ" },
] as const;

export function LandingFooter() {
  return (
    <footer className="lp-foot">
      <span>2026 QuantBridge. 개인 프로젝트입니다.</span>
      <nav className="lp-foot-links" aria-label="푸터 링크">
        {FOOT_LINKS.map((l) => (
          <a key={l.href} href={l.href}>
            {l.label}
          </a>
        ))}
      </nav>
      <span className="mono">woosung · 로컬 워크스페이스</span>
    </footer>
  );
}
