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

// ★★**이 스크립트는 실패할 수 있어야 한다.** 초판은 숫자만 찍고 `process.exit` 가 한 번도 없었다
//   — 즉 「줄었는지 봐라」라고 인쇄만 하고 아무것도 막지 않는 제안이었다(2026-08-16 적대 리뷰).
//   계측기 자신이 통과/실패를 못 내면, 그것을 게이트에 넣을 수도 없고 사람이 눈으로 봐야 한다.
// ★기준선은 `origin/main`(ADR-035 이동 직전)에서 각 테스트의 **실제 목록**으로 잰 값이다.
//   줄면 실패, 늘면 통과 — 늘리는 것은 언제나 안전하다.
const BASELINE = {
  "no-raw-enum-labels": 111,
  "no-internal-ids": 203,
  "design-canon-source": 336,
};
const ACTUAL = {
  "no-raw-enum-labels": enumFiles.size,
  "no-internal-ids": userFacing.length,
  "design-canon-source": allSrc.length,
};
const LABEL = {
  "no-raw-enum-labels": "스캔 .tsx    ",
  "no-internal-ids": "스캔 .tsx    ",
  "design-canon-source": "스캔 .ts/.tsx",
};

console.log("══ 캐논 가드 스코프 인구조사 ══");
const shrunk = [];
for (const [name, base] of Object.entries(BASELINE)) {
  const now = ACTUAL[name];
  const mark = now < base ? "✗ 줄었다" : "✓";
  const extra = name === "no-raw-enum-labels" ? `  (없는 디렉터리 ${missing}개)` : "";
  console.log(
    `  ${name.padEnd(19)} ${LABEL[name]} : ${String(now).padStart(4)}  [기준선 ${base}]  ${mark}${extra}`,
  );
  if (now < base) shrunk.push(`${name}: ${base} → ${now}`);
}
console.log();

if (missing > 0) {
  console.error(`✗ 목록에 있는 디렉터리 ${missing}개가 실재하지 않는다 — 스코프가 조용히 비었다.`);
}
if (shrunk.length > 0) {
  console.error(`✗ 스코프가 줄었다:\n  ${shrunk.join("\n  ")}`);
}
if (missing > 0 || shrunk.length > 0) {
  console.error(
    "\n검사기가 대상을 잃었다. 파일을 옮겼다면 각 테스트의 스코프 목록을 함께 고치고,\n" +
      "의도적으로 줄인 것이라면 이 스크립트의 BASELINE 을 같은 커밋에서 내려라.",
  );
  process.exit(1);
}
console.log("✓ 세 검사기 모두 기준선 이상 — 스코프가 줄지 않았다.");
