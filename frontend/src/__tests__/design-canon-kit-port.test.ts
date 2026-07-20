// 이식된 C 공용 CSS 를 프로토타입 정본(_kit.html)에 잠그는 무결성 가드 (이식 S2)
//
// 목적. globals.css @layer components 안의 이식 블록이 docs/prototypes/shotgun-2026-07/_kit.html
// 의 공용 컴포넌트 CSS 와 "정규화 동일" 함을 동결한다. 프로토타입은 바이트 정본이며 다크 17벌이
// 그것을 참조하므로, 이식본이 정본에서 조용히 표류(kitdrift)하면 이 테스트가 즉시 빨개진다.
//
// ★byte-exact 는 불가능하다 — lint-staged prettier 가 이식 CSS 를 재포맷한다(단일 줄 규칙을
// 여러 줄로 펼치고 들여쓰기를 바꾼다). 그래서 공백/개행을 단일 공백으로 접어(normalize) 대조한다.
// 값·주석·토큰은 보존하므로 규칙 한 글자만 바뀌어도(예: 30px→31px) FAIL 한다.
//
// ★유일한 의도적 편차 = td.num 명시도 교정. _kit.html 에는 없고 이식본에만 있다. 아래 allowlist 가
// 근거와 함께 명시적으로 걷어낸 뒤 대조한다. allowlist 항목이 실재하지 않으면(누가 교정을 지우면)
// 별도 assertion 이 먼저 빨개져 silent no-op 를 막는다.

import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

const GLOBALS = resolve(__dirname, "../styles/globals.css");
const KIT = resolve(__dirname, "../../../docs/prototypes/shotgun-2026-07/_kit.html");

/** 공백/개행/들여쓰기를 단일 공백으로 접는다. prettier 재포맷을 무력화하되 값·주석은 보존한다. */
function normalize(css: string): string {
  return css.replace(/\s+/g, " ").trim();
}

/**
 * globals.css 의 @layer components 안, KITPORT-START ~ KITPORT-END 센티넬 사이만 추출한다.
 * 센티넬 주석 자체는 제외하고 그 안의 이식 CSS 만 반환한다(_kit.html 정본과 1:1 대응 구간).
 */
function extractPortedBlock(src: string): string {
  const startIdx = src.indexOf("KITPORT-START");
  const endIdx = src.indexOf("KITPORT-END");
  if (startIdx === -1 || endIdx === -1) {
    throw new Error("globals.css 에서 KITPORT 센티넬을 찾지 못했다.");
  }
  const afterStart = src.indexOf("*/", startIdx) + 2; // START 센티넬 주석의 끝
  const beforeEnd = src.lastIndexOf("/*", endIdx); // END 센티넬 주석의 시작
  return src.slice(afterStart, beforeEnd);
}

/**
 * _kit.html <style> 의 공용 컴포넌트 블록(.mono ~ PAGE-SPECIFIC 마커)만 추출한다.
 * :root 토큰과 전역 리셋은 앱 것을 쓰므로 이식하지 않았고 대조 대상에서도 뺀다.
 */
function extractKitBlock(src: string): string {
  const startIdx = src.indexOf(".mono {");
  const endIdx = src.indexOf("</style>");
  if (startIdx === -1 || endIdx === -1) {
    throw new Error("_kit.html 에서 공용 CSS 경계를 찾지 못했다.");
  }
  return src.slice(startIdx, endIdx);
}

// ── 의도적 편차 allowlist ────────────────────────────────────────────────
// td.num 명시도 교정. `table.trades tbody td.num`(0,2,3) 이 `.pos`/`.neg`(0,1,0) 를 명시도로
// 이겨, num 셀의 손익 색이 두 테마 모두 죽는다. 라이트 참조 light-01/light-02 가 이미 반영한
// 교정을 정본 공용 CSS 에 동일 적용했다(같은 명시도로 되살림). _kit.html 에는 아직 없으므로 여기서
// 명시적으로 걷어낸 뒤 대조한다. HANDOFF §7 부채. _kit.html 에 교정이 반영되면 이 항목을 지운다.
const TD_NUM_FIX = normalize(`
  /* td.num(0,2,3) 이 .pos/.neg(0,1,0) 를 이겨 표의 손익 색이 두 테마 모두 죽어 있었다.
     같은 명시도로 올려 되살린다. 이식 계획 S2 가 정본 공용 CSS 에 동일 반영한다. */
  table.trades tbody td.num.pos { color: var(--bull); }
  table.trades tbody td.num.neg { color: var(--bear); }
`);

describe("C 공용 CSS 이식 무결성 (S2)", () => {
  const globalsSrc = readFileSync(GLOBALS, "utf8");
  const kitSrc = readFileSync(KIT, "utf8");

  const portedNorm = normalize(extractPortedBlock(globalsSrc));
  const kitNorm = normalize(extractKitBlock(kitSrc));

  it("td.num 교정 allowlist 는 이식본에 실재한다 (silent no-op 방지)", () => {
    expect(portedNorm).toContain(TD_NUM_FIX);
  });

  it("이식 블록은 allowlist 를 제외하면 _kit.html 공용 블록과 정규화 동일하다", () => {
    // allowlist(선행 공백 포함)를 걷어내면 정본과 완전히 일치해야 한다.
    const portedMinusAllowlist = portedNorm.replace(" " + TD_NUM_FIX, "");
    expect(portedMinusAllowlist).toBe(kitNorm);
  });
});
