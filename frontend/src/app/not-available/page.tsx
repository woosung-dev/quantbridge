// Sprint 11 Phase A — geo-block 에 의해 redirect 되는 안내 페이지.

export default function NotAvailablePage() {
  return (
    <main
      id="main-content"
      className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-[680px] flex-col items-center justify-center gap-6 px-6 py-20 text-center"
    >
      <h1 className="font-display text-3xl font-extrabold tracking-tight md:text-4xl">
        QuantBridge is not available in your region
      </h1>
      <p className="max-w-[560px] text-base text-[color:var(--text-secondary)] md:text-lg">
        현재 QuantBridge 는 아시아-태평양 지역에서만 제공됩니다. US/EU 거주자는 가입이
        제한되어 있습니다. 서비스 확장 시 waitlist 로 안내드리겠습니다.
      </p>
      <p className="text-sm text-[color:var(--text-tertiary)]">
        Currently serving: Korea · Japan · Singapore · Taiwan · Hong Kong · Southeast Asia.
      </p>
    </main>
  );
}
