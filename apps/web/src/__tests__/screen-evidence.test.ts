// [BL-797] 화면 증거 팩의 **계산 계층** 판별력 시험.
//
// ★여기서 재는 것은 배선이 아니라 **「빈 결과가 초록으로 새는가」**다. 이 레포는 그 병을
//   소크 게이트 C4(볼 창이 없으면 통과)와 `tool-pin-audit`(핀 0건이면 통과) 두 곳에서 밟았고,
//   화면 축은 특히 위험하다 — **측정 실패와 「변화 없음」이 같은 모양(Δ=0)** 이기 때문이다.
//   계측기가 죽으면 표는 「아무것도 안 바뀌었습니다 ✓」를 인쇄한다. 그것을 여기서 막는다.
//
// ★배선(빌드·서버·playwright)은 여기서 안 잰다 — 그쪽 증인은 `final-gates.sh` 의 실행이고
//   판별력 실측은 `A-REPORT.md` 의 변이 표다.
import { describe, expect, it } from "vitest";

import {
  blobUrl,
  buildReport,
  formatCountDelta,
  formatKb,
  formatKbDelta,
  type RouteMetrics,
  type ScreenshotRef,
} from "../../scripts/screen-evidence-lib.mjs";

const metrics = (over: Partial<RouteMetrics> = {}): RouteMetrics => ({
  firstLoadBytes: 220_416,
  apiRequests: 0,
  totalRequests: 52,
  screenshot: "landing.png",
  ...over,
});

const shot = (over: Partial<ScreenshotRef> = {}): ScreenshotRef => ({
  basePath: "apps/web/e2e/screen-evidence.snapshots/landing-darwin.png",
  headPath: "apps/web/e2e/screen-evidence.snapshots/landing-darwin.png",
  changed: false,
  ...over,
});

const report = (over: Partial<Parameters<typeof buildReport>[0]> = {}) =>
  buildReport({
    before: { "/": metrics() },
    after: { "/": metrics() },
    screenshots: { "/": shot() },
    repoSlug: "woosung-dev/quantbridge",
    baseRef: "main",
    headRef: "stage/night3-evidence-gate",
    ...over,
  });

describe("화면 증거 팩 — 빈 결과는 통과가 아니다", () => {
  it("행이 0개면 던진다", () => {
    // ★★착취 재현: 라우트를 한 건도 못 재면 표가 비고, 빈 표는 「변화 없음 ✓」으로 읽힌다.
    expect(() => report({ before: {}, after: {}, screenshots: {} })).toThrow(/행이 0개/);

    // 음성 대조 — 한 건이라도 있으면 통과한다(못 만드는 게 아니라 비어서 막는 것임을 증명).
    expect(report().rows).toHaveLength(1);
  });

  it("first-load 바이트가 0 이면 던진다 — 「가벼워졌다」로 인쇄하지 않는다", () => {
    // ★★자산 패턴이 안 맞거나 `page.on("response")` 가 떨어지면 결과는 예외가 아니라 **0** 이다.
    //   그리고 0 은 표에서 「−220.4 kB」라는 **최고의 성과**로 보인다.
    expect(() => report({ after: { "/": metrics({ firstLoadBytes: 0 }) } })).toThrow(
      /first-load JS 가 0 바이트/,
    );
    expect(() => report({ before: { "/": metrics({ firstLoadBytes: 0 }) } })).toThrow(
      /first-load JS 가 0 바이트/,
    );

    // 음성 대조 — 양수면 통과한다.
    expect(report({ after: { "/": metrics({ firstLoadBytes: 1 }) } }).rows).toHaveLength(1);
  });

  it("전체 요청 수가 0 이면 던진다 — 계수기 생존 앵커", () => {
    // ★★공개 라우트의 `apiRequests` 는 실측 0 이다(2026-08-17). 그래서 API 축만으로는
    //   `page.on("request")` 를 통째로 떼어내도 `0 → 0 (0)` 으로 **초록**이다.
    //   전체 요청 수는 0 일 수 없으므로 여기가 그 구멍을 막는 유일한 단언이다.
    expect(() => report({ after: { "/": metrics({ totalRequests: 0 }) } })).toThrow(
      /전체 요청 수가 0/,
    );

    // 음성 대조 — API 요청이 0 인 것 자체는 정상이다(공개 라우트의 실제 값).
    expect(report({ after: { "/": metrics({ apiRequests: 0 }) } }).rows).toHaveLength(1);
  });

  it("숫자가 아닌 측정값을 통과시키지 않는다", () => {
    expect(() =>
      report({ after: { "/": metrics({ firstLoadBytes: undefined as unknown as number }) } }),
    ).toThrow(/숫자가 아니다/);
    expect(() =>
      report({ after: { "/": metrics({ totalRequests: NaN }) } }),
    ).toThrow(/숫자가 아니다/);
  });

  it("스크린샷 경로가 빠지면 던진다 — 화면 축이 조용히 사라지지 않는다", () => {
    expect(() => report({ screenshots: {} })).toThrow(/스크린샷 경로가 없다/);
  });
});

describe("화면 증거 팩 — 델타 서식", () => {
  it("증가·감소·불변을 구분한다", () => {
    expect(formatKbDelta(220_416, 270_800)).toBe("+50.4");
    expect(formatKbDelta(270_800, 220_416)).toBe("−50.4");
    expect(formatKbDelta(220_416, 220_416)).toBe("0");
    // 한쪽이 없으면 델타가 아니라 「모른다」다 — 0 으로 적으면 신규 라우트가 「변화 없음」이 된다.
    expect(formatKbDelta(undefined, 220_416)).toBe("—");
  });

  it("요청 수 델타도 같은 규칙이다", () => {
    expect(formatCountDelta(52, 53)).toBe("+1");
    expect(formatCountDelta(53, 52)).toBe("−1");
    expect(formatCountDelta(52, 52)).toBe("0");
    expect(formatCountDelta(undefined, 52)).toBe("—");
  });

  it("kB 는 1000 으로 나눈다 (devtools·next build 와 같은 단위)", () => {
    expect(formatKb(220_416)).toBe("220.4");
    expect(formatKb(undefined)).toBe("—");
  });
});

describe("화면 증거 팩 — 표", () => {
  it("변화가 없으면 changed 0 이고, 어느 축이든 움직이면 센다", () => {
    expect(report().changedCount).toBe(0);
    expect(report({ after: { "/": metrics({ firstLoadBytes: 270_800 }) } }).changedCount).toBe(1);
    expect(report({ after: { "/": metrics({ totalRequests: 53 }) } }).changedCount).toBe(1);
    expect(report({ screenshots: { "/": shot({ changed: true }) } }).changedCount).toBe(1);
  });

  it("한쪽에만 있는 라우트는 신규/삭제로 적는다", () => {
    const added = report({ before: {} });
    expect(added.markdown).toContain("신규");
    const removed = report({ after: {} });
    expect(removed.markdown).toContain("삭제됨");
  });

  it("스크린샷 링크는 브랜치명의 `/` 를 인코딩하지 않는다", () => {
    // ★★회귀 방지: `encodeURIComponent(ref)` 로 감싸면 `stage/night3-…` 이 `stage%2Fnight3-…` 이
    //   돼서 GitHub 이 404 를 낸다. 링크가 죽으면 AC-5(「클릭 한 번 안에 본다」)가 무너진다.
    const url = blobUrl("woosung-dev/quantbridge", "stage/night3-evidence-gate", "apps/web/x.png");
    expect(url).toBe(
      "https://github.com/woosung-dev/quantbridge/blob/stage/night3-evidence-gate/apps/web/x.png?raw=1",
    );
    expect(url).not.toContain("%2F");
  });

  it("스크린샷 링크는 `#` 가 든 유효 브랜치명을 인코딩한다", () => {
    // ★`git check-ref-format --branch 'fix/#797'` 은 통과한다 — 유효한 브랜치명이다.
    //   무인코딩이면 `#797` 이 URL fragment 가 되어 뒤의 파일 경로가 서버에 도달하지 않는다
    //   (codex 적대 리뷰 P3, 2026-08-17). `/` 는 보존하고 세그먼트마다 인코딩한다.
    const url = blobUrl("woosung-dev/quantbridge", "fix/#797", "apps/web/x.png");
    expect(url).toBe(
      "https://github.com/woosung-dev/quantbridge/blob/fix/%23797/apps/web/x.png?raw=1",
    );
    expect(url).not.toContain("/#");
    // ★음성 대조 — 경로 구분자는 여전히 살아 있어야 한다.
    expect(url).toContain("/blob/fix/");
  });

  it("표가 마크다운 그대로 PR 코멘트에 들어간다", () => {
    const { markdown } = report();
    expect(markdown).toContain("| 라우트 | 화면 | first-load JS | API 요청 | 전체 요청 |");
    expect(markdown).toContain("| `/` |");
    expect(markdown).toContain("220.4 → 220.4 kB (0)");
  });
});
