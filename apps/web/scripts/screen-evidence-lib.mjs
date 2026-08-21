// [BL-797] 화면 증거 팩 — 순수 계산 계층.
//
// ★왜 이 파일이 따로 있나. 오케스트레이터(`screen-evidence.mjs`)는 빌드·서버·playwright 를
//   부르므로 단위 시험이 불가능하다. **판별력을 증명해야 하는 것은 계산이지 배선이 아니다** —
//   「빈 표가 초록으로 새는가」·「라우트 매칭이 깨지면 0 kB 가 나오는가」는 전부 여기서 갈린다.
//   그래서 계산만 여기 두고 `src/__tests__/screen-evidence.test.ts` 가 이 파일을 직접 잰다.
//
// ★★**이 파일의 모든 실패는 던진다(throw). 0 이나 빈 값을 돌려주지 않는다.**
//   이 레포는 「볼 것이 없으면 통과」를 소크 게이트 C4 와 `tool-pin-audit` 두 곳에서 밟았다.
//   측정 실패와 「변화 없음」은 **같은 모양(Δ=0)** 이라 구분해서 소리 내지 않으면 영영 안 보인다.

/** 리포트 표에 들어가는 라우트 최소 개수. 0 행 표는 산출이 아니라 사고다. */
export const MIN_ROWS = 1;

/**
 * 바이트 → kB 문자열. 소수 1자리.
 *
 * ★1000 으로 나눈다(1024 아님). `next build` 와 브라우저 devtools 가 쓰는 단위가 kB 라
 *   사람이 다른 도구에서 본 숫자와 나란히 놓을 수 있어야 한다.
 */
export function formatKb(bytes) {
  if (typeof bytes !== "number" || !Number.isFinite(bytes)) return "—";
  return (bytes / 1000).toFixed(1);
}

/**
 * 델타 문자열. 0 은 `0`, 증가는 `+`, 감소는 `−`(U+2212 — 하이픈이 아니다. 표에서 줄바꿈되지 않는다).
 */
export function formatKbDelta(before, after) {
  if (typeof before !== "number" || typeof after !== "number") return "—";
  const d = (after - before) / 1000;
  if (Math.abs(d) < 0.05) return "0";
  return `${d > 0 ? "+" : "−"}${Math.abs(d).toFixed(1)}`;
}

export function formatCountDelta(before, after) {
  if (typeof before !== "number" || typeof after !== "number") return "—";
  const d = after - before;
  if (d === 0) return "0";
  return `${d > 0 ? "+" : "−"}${Math.abs(d)}`;
}

/**
 * 커밋된 산출물의 GitHub raw URL.
 *
 * ★**로컬 파일 경로를 PR 코멘트에 적으면 아무도 못 본다.** 스크린샷 baseline 은 레포에
 *   커밋되므로 blob URL 이 실재하고, 리뷰어는 클릭 한 번에 before/after 를 연다(AC-5).
 *   before 는 `main`, after 는 이 브랜치다 — 둘 다 **커밋된 것**이라 링크가 썩지 않는다.
 */
export function blobUrl(repoSlug, ref, filePath) {
  // ★ref 를 통째로 `encodeURIComponent` 하면 안 된다 — `stage/night3-…` 의 `/` 가 `%2F` 로
  //   바뀌어 GitHub 이 404 를 낸다. 그렇다고 무인코딩도 안 된다: `fix/#797` 은 `git
  //   check-ref-format` 이 통과시키는 **유효한 브랜치명**인데 `#` 가 URL fragment 가 되어
  //   파일 경로가 서버에 도달하지 않는다(codex 적대 리뷰 P3, 2026-08-17).
  //   ⇒ 경로 구분자 `/` 는 보존하고 **세그먼트마다** 인코딩한다.
  const safeRef = String(ref).split("/").map(encodeURIComponent).join("/");
  return `https://github.com/${repoSlug}/blob/${safeRef}/${filePath}?raw=1`;
}

/**
 * 라우트 하나의 before/after 를 한 행으로.
 *
 * @returns {{ route: string, screen: string, bundle: string, apiRequests: string, totalRequests: string, changed: boolean }}
 */
function buildRow({ route, before, after, screenshot, repoSlug, baseRef, headRef }) {
  const isNew = before === undefined;
  const isGone = after === undefined;

  let screen;
  // ★★**수치 전용 라우트** ([BL-797] authed 확장, 2026-08-18). authed 화면은 실데이터가
  //   픽셀을 흔들어 스크린샷 축과 상극이라 번들·요청 수만 잰다. `null` 은 **「이 라우트는
  //   화면 축을 안 잰다」는 선언**이고, 키 자체의 부재(`undefined`)와 다르다 — 후자는 여전히
  //   측정 실패이며 `buildReport` 가 던진다. 둘을 같게 낮추면 스냅샷이 통째로 빠진 회차가
  //   조용히 초록이 된다.
  if (screenshot === null) {
    screen = "—(수치 전용)";
  } else if (isNew) {
    screen = `신규 — [after](${blobUrl(repoSlug, headRef, screenshot.headPath)})`;
  } else if (isGone) {
    screen = `삭제됨 — [before](${blobUrl(repoSlug, baseRef, screenshot.basePath)})`;
  } else if (screenshot.changed) {
    screen =
      `**변경됨** — [before](${blobUrl(repoSlug, baseRef, screenshot.basePath)})` +
      ` · [after](${blobUrl(repoSlug, headRef, screenshot.headPath)})`;
  } else {
    screen = `변경 없음 — [보기](${blobUrl(repoSlug, headRef, screenshot.headPath)})`;
  }

  const bundle = `${formatKb(before?.firstLoadBytes)} → ${formatKb(after?.firstLoadBytes)} kB (${formatKbDelta(
    before?.firstLoadBytes,
    after?.firstLoadBytes,
  )})`;
  const counts = (key) =>
    `${before?.[key] ?? "—"} → ${after?.[key] ?? "—"} (${formatCountDelta(before?.[key], after?.[key])})`;

  return {
    route,
    screen,
    bundle,
    apiRequests: counts("apiRequests"),
    totalRequests: counts("totalRequests"),
    changed:
      isNew ||
      isGone ||
      screenshot?.changed === true ||
      before?.firstLoadBytes !== after?.firstLoadBytes ||
      before?.apiRequests !== after?.apiRequests ||
      before?.totalRequests !== after?.totalRequests,
  };
}

/**
 * 측정값이 「측정된 것」인지 검증한다.
 *
 * ★★**이것이 이 파일의 핵심 단언이다.** 라우트 매칭이 깨지거나 계수기가 떨어져 나가면
 *   결과는 예외가 아니라 **0** 으로 나온다 — 그리고 0 은 「가벼워졌다」로 읽힌다.
 *   빈 페이지가 아닌 이상 first-load JS 가 0 바이트일 수 없으므로 여기서 던진다.
 */
function assertMeasurable(label, metrics) {
  if (!metrics || typeof metrics !== "object")
    throw new Error(`${label}: 측정값이 없다 — 표를 만들 수 없다.`);
  if (typeof metrics.firstLoadBytes !== "number" || !Number.isFinite(metrics.firstLoadBytes))
    throw new Error(`${label}: firstLoadBytes 가 숫자가 아니다 (${metrics.firstLoadBytes}).`);
  if (metrics.firstLoadBytes <= 0)
    throw new Error(
      `${label}: first-load JS 가 ${metrics.firstLoadBytes} 바이트다. ` +
        "Next 앱의 라우트가 JS 0 바이트일 수 없다 — 계측기가 응답을 못 봤거나 라우트 키가 어긋났다. " +
        "**0 을 「가벼워졌다」로 인쇄하지 않는다.**",
    );
  // ★`null` 은 **「대조 제외」의 선언**이지 결측이 아니다(authed — 실측상 요청 수가 ±1 로
  //   흔들린다). `undefined` 는 여전히 결측이라 던진다 — 둘을 같게 낮추면 계수기가 통째로
  //   빠진 회차가 「비결정 축」으로 위장한다.
  if (
    metrics.apiRequests !== null &&
    (typeof metrics.apiRequests !== "number" || !Number.isFinite(metrics.apiRequests))
  )
    throw new Error(`${label}: apiRequests 가 숫자가 아니다 (${metrics.apiRequests}).`);
  // ★공개 라우트의 `apiRequests` 는 실측 0 이다 — 그래서 **그 축만으로는 계수기가 죽어도
  //   0 == 0 으로 초록이다.** 전체 요청 수는 0 일 수 없으므로 여기가 계수기의 생존 앵커다.
  if (metrics.totalRequests === null) return; // 대조 제외 — 생존 검사는 spec 의 `> 0` 앵커가 진다.
  if (typeof metrics.totalRequests !== "number" || !Number.isFinite(metrics.totalRequests))
    throw new Error(`${label}: totalRequests 가 숫자가 아니다 (${metrics.totalRequests}).`);
  if (metrics.totalRequests <= 0)
    throw new Error(
      `${label}: 전체 요청 수가 ${metrics.totalRequests} 다. 화면을 그린 실행이 요청 0건일 수 없다 — ` +
        "요청 계수기가 죽었다. **0 을 「가벼운 화면」으로 인쇄하지 않는다.**",
    );
}

/**
 * before/after 를 사람이 읽는 표 하나로 합친다 (AC-5).
 *
 * @param before  `origin/main` 의 baseline — `{ [route]: { firstLoadBytes, apiRequests, screenshot } }`
 * @param after   이 브랜치의 baseline (라이브 측정으로 검증된 값)
 * @param screenshots `{ [route]: { basePath, headPath, changed } }`
 * @throws 표가 비거나 측정이 성립하지 않으면 — **rc≠0 의 유일한 출처다.**
 */
export function buildReport({
  before,
  after,
  screenshots,
  repoSlug,
  baseRef,
  headRef,
  notes = [],
}) {
  const routes = [...new Set([...Object.keys(before ?? {}), ...Object.keys(after ?? {})])].sort();

  if (routes.length < MIN_ROWS)
    throw new Error(
      `화면 증거 표에 행이 0개다 (before ${Object.keys(before ?? {}).length}건 · after ${Object.keys(after ?? {}).length}건).\n` +
        "빈 표는 「변화 없음」이 아니라 **측정이 일어나지 않았다**는 뜻이다. 통과시키지 않는다.",
    );

  const rows = routes.map((route) => {
    // 양쪽에 다 있는 라우트만 「측정됐다」를 요구한다 — 신규/삭제는 한쪽이 없는 것이 정상이다.
    if (after?.[route]) assertMeasurable(`${route} (after)`, after[route]);
    if (before?.[route]) assertMeasurable(`${route} (before)`, before[route]);
    // ★`Object.hasOwn` 으로 가른다 — `null`(수치 전용 선언)은 통과시키고, **키의 부재**는
    //   여전히 던진다. `!shot` 하나로 두 경우를 묶으면 스냅샷이 통째로 빠진 회차가 「수치
    //   전용」으로 위장해 초록이 된다.
    if (!Object.hasOwn(screenshots ?? {}, route))
      throw new Error(`${route}: 스크린샷 경로가 없다 — 화면 축이 통째로 빠진다.`);
    const shot = screenshots[route];
    return buildRow({
      route,
      before: before?.[route],
      after: after?.[route],
      screenshot: shot,
      repoSlug,
      baseRef,
      headRef,
    });
  });

  const changedCount = rows.filter((r) => r.changed).length;
  const header = [
    `## 화면 증거 팩 — \`${headRef}\` vs \`${baseRef}\``,
    "",
    `라우트 ${rows.length}건 중 **${changedCount}건**이 달라졌다.`,
    "",
    "| 라우트 | 화면 | first-load JS | API 요청 | 전체 요청 |",
    "| --- | --- | --- | --- | --- |",
  ];
  const body = rows.map(
    (r) => `| \`${r.route}\` | ${r.screen} | ${r.bundle} | ${r.apiRequests} | ${r.totalRequests} |`,
  );
  const footer = notes.length > 0 ? ["", "<sub>", ...notes.map((n) => `- ${n}`), "</sub>"] : [];

  return { markdown: [...header, ...body, ...footer].join("\n"), rows, changedCount };
}
