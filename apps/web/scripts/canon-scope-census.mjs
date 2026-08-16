// 캐논 가드 3종이 **실제로 몇 파일을 읽는가**를 센다.
//
// ★왜 있나 (2026-08-16 layout-alignment). `no-raw-enum-labels.test.ts` 는 스캔 대상을
//   **디렉터리 경로 배열**로 정의하고 `walk()` 는 `existsSync` 가 false 면 조용히 건너뛴다.
//   그래서 `app/**/_components/` 를 `features/*/components/` 로 옮기면 스코프가 비고
//   **테스트는 초록으로 통과한다** — 이 레포가 반복해 덴 「빈 입력이 원하는 답」이다.
//   이동 전후로 이 수치를 비교해서, 줄어들면 배선이 죽은 것으로 판정한다.
//
// 사용: cd apps/web && node scripts/canon-scope-census.mjs
import { existsSync, readdirSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const SRC = resolve(dirname(fileURLToPath(import.meta.url)), "..", "src");

/** `no-raw-enum-labels.test.ts` 의 walk 와 같은 규칙 — .tsx, __tests__/점파일 제외, 테스트 파일 제외. */
function walkTsx(dir, out = []) {
  if (!existsSync(dir)) return out;
  for (const entry of readdirSync(dir)) {
    if (entry === "__tests__" || entry.startsWith(".")) continue;
    const full = join(dir, entry);
    const stat = statSync(full);
    if (stat.isDirectory()) walkTsx(full, out);
    else if (
      stat.isFile() &&
      full.endsWith(".tsx") &&
      !full.endsWith(".test.tsx") &&
      !full.endsWith(".spec.tsx")
    )
      out.push(full);
  }
  return out;
}

// no-raw-enum-labels.test.ts `SCOPE_MARKERS` 와 **같은 목록**을 유지해야 한다.
// ★2026-08-16 ADR-035 이동 기준선: 구 목록(app/**/_components 8종 포함) 112 → 신 목록 116.
const ENUM_LABEL_DIRS = [
  join("features", "backtest", "components"),
  join("features", "trading", "components"),
  join("features", "dashboard", "components"),
  join("features", "optimizer", "components"),
  join("features", "strategy", "components"),
  join("features", "live-sessions", "components"),
];

const enumFiles = new Set();
let missing = 0;
for (const d of ENUM_LABEL_DIRS) {
  const abs = join(SRC, d);
  if (!existsSync(abs)) missing += 1;
  for (const f of walkTsx(abs)) enumFiles.add(f);
}

// no-internal-ids.test.ts `getUserFacingFiles()` — root=src, subdirs app/components/features.
function walkUserFacing(dir, out = []) {
  if (!existsSync(dir)) return out;
  for (const entry of readdirSync(dir)) {
    if (entry === "__tests__" || entry.startsWith(".")) continue;
    const full = join(dir, entry);
    const stat = statSync(full);
    if (stat.isDirectory()) {
      walkUserFacing(full, out);
      continue;
    }
    if (!stat.isFile() || !full.endsWith(".tsx")) continue;
    if (full.endsWith(".test.tsx") || full.endsWith(".spec.tsx")) continue;
    const name = full.slice(full.lastIndexOf("/") + 1);
    const userFacing =
      name === "page.tsx" ||
      name === "layout.tsx" ||
      full.includes("/_components/") ||
      (full.includes("/components/") && !full.includes("/components/ui/")) ||
      full.includes("/features/");
    if (userFacing) out.push(full);
  }
  return out;
}

const userFacing = [];
for (const sub of ["app", "components", "features"]) walkUserFacing(join(SRC, sub), userFacing);

// design-canon-source.test.ts — src 전체를 걷고, 예외 화이트리스트가 **경로 키**다.
const allSrc = walkTsx(SRC);

console.log("══ 캐논 가드 스코프 인구조사 ══");
console.log(`  no-raw-enum-labels  스캔 .tsx : ${enumFiles.size}   (없는 디렉터리 ${missing}개)`);
console.log(`  no-internal-ids     스캔 .tsx : ${userFacing.length}`);
console.log(`  design-canon-source 스캔 .tsx : ${allSrc.length}`);
console.log();
console.log("★이동 후 위 세 수가 **줄면** 검사기가 대상을 잃은 것이다 — 초록을 통과로 읽지 마라.");
