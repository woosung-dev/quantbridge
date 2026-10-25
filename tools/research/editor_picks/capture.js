async (page) => {
  // MCP가 실행하는 UI 수집 함수다. 내부 API 주소를 추측하거나 직접 재호출하지 않는다.
  const config = { firstPage: 1, pages: 1, offset: 0, limit: 6 };
  const listings = config.listings ?? [];
  const publications = listings.flatMap(listing => listing.items.map((item, index) => ({ ...item, listing_url: listing.url, listing_position: index })));
  for (let number = config.firstPage; number < config.firstPage + config.pages; number++) {
    const url = `https://www.tradingview.com/scripts/editors-picks/${number === 1 ? "" : `page-${number}/`}`;
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.locator('a[href*="/script/"]').first().waitFor({ timeout: 15000 });
    const items = await page.locator('a[href*="/script/"]').evaluateAll(elements => {
      const unique = new Map();
      for (const element of elements) {
        const url = new URL(element.href);
        const title = element.innerText.trim();
        if (!url.hash && !url.search && title.length > 1 && title.length < 150 && !/^\d[\d\s,.Kk]*$/.test(title) && !unique.has(element.href)) {
          unique.set(element.href, { url: element.href, title, metadata: element.closest("article")?.innerText ?? title });
        }
      }
      return Array.from(unique.values());
    });
    listings.push({ url: page.url(), observed_at: new Date().toISOString(), items });
    publications.push(...items.map((item, index) => ({ ...item, listing_url: page.url(), listing_position: index })));
  }
  const captures = [];
  const scoped = config.indicatorsOnly ? publications.filter(item => /\nINDICATOR\n/.test(item.metadata)) : publications;
  const candidates = config.match ? scoped.filter(item => new RegExp(config.match, "i").test(item.metadata)) : scoped;
  const selected = config.ids ? candidates.filter(item => config.ids.includes(new URL(item.url).pathname.split("/")[2].slice(0, 8))) : candidates;
  const state = { schema_version: 1, listings, captures, running: true, cancelled: false };
  const work = async () => {
  for (const item of selected.slice(config.offset, config.offset + config.limit)) {
    if (state.cancelled) break;
    const record = { ...item, id: new URL(item.url).pathname.split("/")[2].slice(0, 8), observed_at: new Date().toISOString() };
    try {
      await page.goto(item.url, { waitUntil: "domcontentloaded", timeout: 30000 });
      const control = page.getByText("Source code", { exact: true });
      if (await control.count() === 0) throw new Error("공개 Source code UI 없음");
      const responsePromise = page.waitForResponse(response => response.url().includes("pine-facade/get/") && response.status() === 200, { timeout: 15000 });
      await control.click();
      const response = await responsePromise;
      const body = await response.json();
      const title = await page.title();
      const author = title.match(/ by (.*?) — TradingView/)?.[1] ?? null;
      if (typeof body.source !== "string" || !body.source.trim()) throw new Error("공개 원문 응답 없음");
      captures.push({ ...record, author, source: body.source, source_response_url: response.url(),
        script_access: body.scriptAccess, script_version: body.lastVersionMaj,
        page_title: title, status: "captured" });
    } catch (error) {
      captures.push({ ...record, status: "capture_failed", error: String(error) });
    }
  }
  state.running = false;
  };
  if (config.background) {
    if (page.__qbCaptureJob?.running) throw new Error("이 탭에서 원문 수집이 이미 실행 중입니다");
    page.__qbCaptureJob = state;
    state.promise = work().catch(error => { state.error = String(error); state.running = false; });
    return { started: true, requested: Math.min(config.limit, selected.length - config.offset) };
  }
  await work();
  return { schema_version: 1, listings, captures };
}
