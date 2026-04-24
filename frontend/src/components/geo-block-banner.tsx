// Sprint 11 Phase A — 지원 지역 안내 배너 (Landing 상단 고정).
// 3 계층 방어의 사용자 가시 layer. WAF/proxy 에 차단되지 않은 방문자에게 안내 제공.

export function GeoBlockBanner() {
  return (
    <div
      role="note"
      className="w-full border-b border-amber-300 bg-amber-50 px-6 py-2 text-center text-xs text-amber-900"
    >
      <strong>Beta:</strong> QuantBridge is currently available in{" "}
      <span className="font-semibold">Asia-Pacific only</span>. US and EU residents are not eligible
      for signup at this time.
    </div>
  );
}
