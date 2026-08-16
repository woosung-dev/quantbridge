// 캐논 가드 3종이 **실제로 몇 파일을 읽는가**를 센다.
//
// ★왜 있나 (2026-08-16 layout-alignment). `no-raw-enum-labels.test.ts` 는 스캔 대상을
//   **디렉터리 경로 배열**로 정의하고 `walk()` 는 `existsSync` 가 false 면 조용히 건너뛴다.
//   그래서 `app/**/_components/` 를 `features/*/components/` 로 옮기면 스코프가 비고
//   **테스트는 초록으로 통과한다** — 이 레포가 반복해 덴 「빈 입력이 원하는 답」이다.
//   이동 전후로 이 수치를 비교해서, 줄어들면 배선이 죽은 것으로 판정한다.
//
// ★★**이 파일의 걷기 규칙은 각 테스트의 규칙과 정확히 같아야 한다.** 초판은 세 검사기 모두에
//   `.tsx` 전용 walk 를 썼는데 `design-canon-source.test.ts` 의 `productionFiles()` 는
//   **`.ts` 도 세고 `generated/` 를 제외**한다 — 그래서 336 을 236 으로 보고했다(2026-08-16
//   codex P2). 계측기가 대상과 다른 것을 세면 「줄었는가」 판정 자체가 무의미하다.
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

/** `design-canon-source.test.ts` 의 `productionFiles()` 와 같은 규칙 — `.ts`+`.tsx`, `generated/` 제외. */
function walkProduction(dir, out = []) {
  if (!existsSync(dir)) return out;
  for (const entry of readdirSync(dir)) {
    if (entry === "__tests__" || entry === "generated" || entry === "node_modules") continue;
    if (entry.startsWith(".")) continue;
    const full = join(dir, entry);
    const stat = statSync(full);
    if (stat.isDirectory()) walkProduction(full, out);
    else if (stat.isFile() && /\.(ts|tsx)$/.test(full) && !/\.(test|spec)\.(ts|tsx)$/.test(full))
      out.push(full);
  }
  return out;
}

// no-raw-enum-labels.test.ts `SCOPE_MARKERS` 와 **같은 목록**을 유지해야 한다.
// ★2026-08-16 ADR-035 이동 기준선(`origin/main` 의 테스트 목록으로 재측정):
//   no-raw-enum-labels 111 → 116 · design-canon-source 336 → 336.
//   ★종전에 적혀 있던 「112」는 이 계측기 초판이 목록에 `features/backtest·dashboard` 를
//     미리 넣어 과다 계상한 값이다. 기준선은 **테스트가 그때 실제로 쓰던 목록**으로 잰다.
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
const allSrc = walkProduction(SRC);

console.log("══ 캐논 가드 스코프 인구조사 ══");
console.log(
  `  no-raw-enum-labels  스캔 .tsx     : ${enumFiles.size}   (없는 디렉터리 ${missing}개)  [기준선 111]`,
);
console.log(`  no-internal-ids     스캔 .tsx     : ${userFacing.length}   [기준선 203]`);
console.log(`  design-canon-source 스캔 .ts/.tsx : ${allSrc.length}   [기준선 336]`);
console.log();
console.log("★이동 후 위 세 수가 **줄면** 검사기가 대상을 잃은 것이다 — 초록을 통과로 읽지 마라.");
