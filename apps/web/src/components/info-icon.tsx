// 정보 아이콘 크로스페이지 프리미티브 (S9 추출) — disclaimer/chart-note 앞의 원형 i 아이콘.
// dashboard-cockpit · workspace-equity-card · trading-cockpit 에 바이트 동일한 인라인 SVG 가
// 3벌 반복돼 한 곳으로 모은다. aria-hidden 이므로 접근 이름은 옆 산문이 담당한다.

export function InfoIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="9" />
      <line x1="12" y1="11" x2="12" y2="16" />
      <line x1="12" y1="7.5" x2="12.01" y2="7.5" />
    </svg>
  );
}
