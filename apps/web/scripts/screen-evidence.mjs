#!/usr/bin/env node
// [BL-797] 화면 증거 팩 — 오케스트레이터.
//
//   pnpm screen-evidence           # 대조 + 리포트 산출 (게이트가 부르는 모드)
//   pnpm screen-evidence:update    # baseline(스크린샷 + 수치) 갱신
//
// 하는 일 다섯:
//   ⑴ `next build` — 측정은 **프로덕션 산출물**을 상대로 한다(dev 는 Turbopack 이 모듈 단위로
//      쪼개 서빙해서 바이트가 캐시 상태에 따라 흔들리고 dev 표시기가 화면에 얹힌다).
//   ⑵ `next start` 로 그 산출물을 띄운다.
//   ⑶ `playwright --project=chromium-screen-evidence` — 화면·번들 바이트·API 요청 수를 잰다.
//   ⑷ 서버를 내린다(실패해도 반드시).
//   ⑸ **before(`origin/main` 의 git blob) ↔ after(이 브랜치의 커밋된 baseline)** 를 표 하나로.
//
// ★★**before 는 추론이 아니라 git blob 이다.** 「머지 기준에서 한 번 더 빌드·캡처」하는 방식도
//   있었지만(레인 파일의 갈래 ⑴), 그러려면 `origin/main` 워크트리 + node_modules + 두 번째
//   빌드가 필요하고 그 전체가 「재현 가능한가」를 다시 증명해야 한다. baseline 을 커밋해 두면
//   before 는 `git show origin/main:<파일>` 한 줄이고 **정확히 머지 기준**이다.
//   대가는 하나 — 화면을 바꾼 회차는 `:update` 를 한 번 돌려야 한다. 그 갱신분이 곧 after 다.
//
// ★신호 게이트 4종과 달리 이것은 **`--pre-pr` 안에서 도는 실 게이트**다. 유예 대상이 아니다.
import { execFileSync, spawn, spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { buildReport } from "./screen-evidence-lib.mjs";

const WEB_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const CONFIG = JSON.parse(readFileSync(path.join(WEB_ROOT, "e2e/screen-evidence.config.json"), "utf8"));
const REPO_ROOT = path.resolve(WEB_ROOT, "../..");
/** 레포 루트 기준 경로 — `git show <ref>:<경로>` 가 요구하는 형태다. */
const REPO_REL = (p) => path.relative(REPO_ROOT, path.resolve(WEB_ROOT, p));

const UPDATE = process.argv.includes("--update");
/**
 * before 를 읽어 올 참조. 기본은 머지 기준이다.
 *
 * ★바꿀 수 있게 둔 이유는 하나뿐이다 — **이 게이트가 main 에 착륙하기 전에는 `origin/main` 에
 *   baseline 파일 자체가 없어서** 모든 라우트가 「신규」로만 나오고 델타를 한 번도 못 보여준다.
 *   판별력을 증명하려면 「baseline 이 있는 참조」와 대조할 수 있어야 한다. 착륙 후에는 기본값이
 *   맞으므로 게이트는 이 변수를 **설정하지 않는다**.
 */
const BASE_REF = process.env.SCREEN_EVIDENCE_BASE_REF?.trim() || "origin/main";
/** blob URL 에 쓰는 이름 — `origin/main` 은 원격 추적 참조라 GitHub 에는 그 이름이 없다. */
const BASE_BRANCH = BASE_REF.replace(/^origin\//, "");
const RUN = (process.env.PW_ARTIFACT_RUN?.trim() || "screen-evidence").replace(
  /[^A-Za-z0-9._-]/g,
  "-",
);
const OUT_DIR = path.join(WEB_ROOT, CONFIG.outputRoot, /^\.+$/.test(RUN) ? "-" : RUN);
const MEASURED_DIR = path.join(OUT_DIR, CONFIG.measuredDir);
const BASELINE_ABS = path.join(WEB_ROOT, CONFIG.baseline);

const die = (message) => {
  console.error(`\n✗ 화면 증거 팩 — ${message}\n`);
  process.exit(1);
};

function git(args, { allowFail = false } = {}) {
  try {
    return execFileSync("git", args, { cwd: REPO_ROOT, encoding: "buffer", stdio: ["ignore", "pipe", "pipe"] });
  } catch (error) {
    if (allowFail) return null;
    throw error;
  }
}

/** 워크트리 슬롯 — 병렬 레인이 같은 포트를 잡지 않게 한다. */
function worktreeSlot() {
  const file = path.join(REPO_ROOT, ".worktree-slot");
  if (!existsSync(file)) return 0;
  const m = readFileSync(file, "utf8").match(/^QB_SLOT\s*=\s*(\d+)\s*$/m);
  return m ? Number(m[1]) : 0;
}

function run(command, args, { env = {}, cwd = WEB_ROOT } = {}) {
  // ★파이프를 쓰지 않는다. 이 레포는 `| tail` 로 **tail 의 종료 코드**를 읽어 정반대 보고를
  //   낸 사고를 일곱 번 겪었다. stdio 를 그대로 물려주고 status 를 직접 본다.
  return spawnSync(command, args, { stdio: "inherit", env: { ...process.env, ...env }, cwd });
}

async function isListening(url) {
  try {
    await fetch(url, { redirect: "manual", signal: AbortSignal.timeout(2_000) });
    return true;
  } catch {
    return false;
  }
}

async function waitForServer(url, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(url, { redirect: "manual" });
      if (res.status > 0) return;
    } catch {
      // 아직 안 떴다.
    }
    await new Promise((r) => setTimeout(r, 300));
  }
  throw new Error(`${url} 이 ${timeoutMs}ms 안에 응답하지 않았다.`);
}

function readBaselineFrom(ref) {
  const blob = git(["show", `${ref}:${REPO_REL(CONFIG.baseline)}`], { allowFail: true });
  if (!blob) return null;
  return JSON.parse(blob.toString("utf8")).routes ?? {};
}

function readBaselineHere() {
  if (!existsSync(BASELINE_ABS)) return null;
  return JSON.parse(readFileSync(BASELINE_ABS, "utf8")).routes ?? {};
}

/** 스냅샷 파일의 플랫폼 접미는 playwright 가 붙인다. 같은 규칙으로 되짚는다. */
const snapshotFile = (name) => {
  const ext = path.extname(name);
  return `${CONFIG.snapshotDir}/${name.slice(0, -ext.length)}-${process.platform}${ext}`;
};

async function main() {
  const slot = worktreeSlot();
  const port = CONFIG.serverPortBase + slot;
  const baseURL = `http://localhost:${port}`;

  console.log(`▶ 화면 증거 팩 — run=${RUN} slot=${slot} port=${port} mode=${UPDATE ? "update" : "check"}`);

  // ★★포트가 이미 물려 있으면 **거기서 멈춘다.** `next start` 는 EADDRINUSE 로 죽는데 아래
  //   `waitForServer` 는 「누군가 응답한다」만 보므로 그대로 통과하고, 그러면 이 게이트는
  //   방금 만든 빌드가 아니라 **남아 있던 서버**를 잰다. 이 레포는 같은 병을
  //   `final-gates.sh` 의 정체성 프로브로 한 번 고쳤다(:3000 의 남의 앱을 검사한 사고).
  if (await isListening(`http://localhost:${port}/`))
    die(
      `:${port} 가 이미 응답한다. 앞선 회차가 남긴 \`next start\` 일 가능성이 크다.\n` +
        `  그대로 두면 **방금 만든 빌드가 아니라 그 서버**를 재고 초록이 난다.\n` +
        `  정리: lsof -ti :${port} | xargs kill`,
    );

  // ⑴ 빌드. **캐시된 `.next` 를 재사용하지 않는다** — 낡은 산출물로 잰 숫자는 이 게이트가
  //    막으려는 「측정 없이 판단」 그 자체다.
  const build = run("pnpm", ["exec", "next", "build"]);
  if (build.status !== 0) die(`\`next build\` 가 rc=${build.status} 로 실패했다. 번들을 잴 수 없다.`);

  // ⑵ 프로덕션 서버.
  // ★`next start` 는 `output: "standalone"` 설정 때문에 경고를 한 줄 찍지만 **정상 서빙한다**
  //   (2026-08-17 실측: `/` 200 · `/_next/static/chunks/*.js` 200 28,559B). standalone 산출물은
  //   `.next/static` 을 스스로 안 품어서 그쪽으로 띄우면 자산이 404 가 되고 번들 바이트가 0 이 된다.
  const server = spawn("pnpm", ["exec", "next", "start", "-p", String(port)], {
    cwd: WEB_ROOT,
    env: { ...process.env, BETTER_AUTH_URL: baseURL },
    stdio: ["ignore", "pipe", "pipe"],
  });
  let serverLog = "";
  server.stdout.on("data", (c) => (serverLog += c));
  server.stderr.on("data", (c) => (serverLog += c));

  let playwrightStatus = null;
  try {
    await waitForServer(`${baseURL}/`, 60_000);
    console.log(`  프로덕션 서버 준비됨 — ${baseURL}`);

    // ⑶ 측정. 회차 폴더를 먼저 비운다 — 앞 회차 측정 JSON 이 남아 있으면 이번에 실패한
    //    라우트가 **지난번 값으로 표에 실린다**(빈 결과가 초록으로 새는 그 병).
    rmSync(MEASURED_DIR, { recursive: true, force: true });
    mkdirSync(MEASURED_DIR, { recursive: true });

    const args = ["exec", "playwright", "test", "--project=chromium-screen-evidence"];
    if (UPDATE) args.push("--update-snapshots");
    const pw = run("pnpm", args, {
      env: {
        PLAYWRIGHT_BASE_URL: baseURL,
        PW_ARTIFACT_RUN: RUN,
        ...(UPDATE ? { SCREEN_EVIDENCE_UPDATE: "1" } : {}),
      },
    });
    playwrightStatus = pw.status;
  } finally {
    server.kill("SIGTERM");
  }

  const measuredFiles = existsSync(MEASURED_DIR)
    ? readdirSync(MEASURED_DIR).filter((f) => f.endsWith(".json"))
    : [];
  if (measuredFiles.length === 0)
    die(
      "라우트를 한 건도 측정하지 못했다.\n" +
        `  playwright rc=${playwrightStatus}\n` +
        "  ★빈 측정은 「변화 없음」이 아니다. 서버 로그 마지막 20줄:\n" +
        serverLog.split("\n").slice(-20).join("\n"),
    );

  const measured = {};
  for (const f of measuredFiles) {
    const m = JSON.parse(readFileSync(path.join(MEASURED_DIR, f), "utf8"));
    measured[m.path] = {
      firstLoadBytes: m.firstLoadBytes,
      apiRequests: m.apiRequests,
      totalRequests: m.totalRequests,
      screenshot: m.screenshot,
    };
  }

  if (UPDATE) {
    if (playwrightStatus !== 0)
      die(`갱신 모드인데 playwright 가 rc=${playwrightStatus} 로 실패했다 — baseline 을 쓰지 않는다.`);
    writeFileSync(
      BASELINE_ABS,
      `${JSON.stringify(
        {
          _comment:
            "[BL-797] 화면 증거 팩 baseline. `pnpm screen-evidence:update` 가 쓴다 — 손으로 고치지 마라. " +
            "이 파일의 origin/main 판이 PR 리포트의 **before** 이고, 이 브랜치 판이 **after** 다.",
          platform: process.platform,
          routes: Object.fromEntries(Object.entries(measured).sort(([a], [b]) => a.localeCompare(b))),
        },
        null,
        2,
      )}\n`,
      "utf8",
    );
    console.log(`\n✓ baseline 갱신 — ${path.relative(REPO_ROOT, BASELINE_ABS)} (라우트 ${Object.keys(measured).length}건)`);
    console.log("  스크린샷도 함께 갱신됐다. 둘 다 커밋해야 PR 이 after 를 인쇄한다.");
    return;
  }

  if (playwrightStatus !== 0)
    die(
      `playwright 가 rc=${playwrightStatus} 로 실패했다.\n` +
        "  화면·번들·요청 수 중 하나가 커밋된 baseline 과 다르다. 의도한 변경이면:\n" +
        "    pnpm screen-evidence:update   (그 갱신분이 곧 PR 이 인쇄할 after 다)",
    );

  // ⑸ before ↔ after. after 는 워킹트리의 커밋된 baseline 이고, 방금 라이브 측정이 그것을
  //    검증했다(spec ⑸). before 는 같은 파일의 `origin/main` 판이다.
  const after = readBaselineHere();
  if (!after) die(`baseline 이 없다 — ${path.relative(REPO_ROOT, BASELINE_ABS)}. \`:update\` 를 먼저 돌려라.`);
  const before = readBaselineFrom(BASE_REF);

  const screenshots = {};
  for (const route of new Set([...Object.keys(before ?? {}), ...Object.keys(after)])) {
    const name = after[route]?.screenshot ?? before?.[route]?.screenshot;
    if (!name) die(`${route}: baseline 에 스냅샷 이름이 없다.`);
    const rel = snapshotFile(name);
    const headBlob = existsSync(path.join(WEB_ROOT, rel)) ? readFileSync(path.join(WEB_ROOT, rel)) : null;
    const baseBlob = git(["show", `${BASE_REF}:${REPO_REL(rel)}`], { allowFail: true });
    screenshots[route] = {
      basePath: REPO_REL(rel),
      headPath: REPO_REL(rel),
      // ★바이트 비교로 충분하다. 양쪽 다 **커밋된 산출물**이지 그 자리에서 렌더한 것이 아니라
      //   안티앨리어싱 잡음이 낄 자리가 없다. 픽셀 비교는 spec 이 이미 했다(라이브 vs baseline).
      changed: !baseBlob || !headBlob ? true : !baseBlob.equals(headBlob),
    };
  }

  const notes = [
    `측정: 프로덕션 빌드(\`next build\` + \`next start\`) · 뷰포트 1280×720 · fullPage · ${process.platform}`,
    "first-load JS = 그 화면이 받은 `/_next/static/**.{js,css}` 의 **전송 바이트**(gzip 후) 합 — 폰트 제외",
    "요청 수 = `networkidle` + 1초 창 안의 건수. API 는 `/api/v1/` 부분집합이고, 공개 라우트는 실측 0이라 전체 요청 수가 계수기의 생존 앵커다",
    "실패 응답이 하나라도 있으면 「변화」가 아니라 **측정 오염**으로 red 를 낸다([BL-786] 의 성질을 재사용)",
    "★공개 라우트만이다. authed 화면은 [BL-789] 로 CI 불가이고 로컬에서도 실데이터가 픽셀을 흔든다 — 이 표에 없다.",
  ];

  let report;
  try {
    report = buildReport({
      before: before ?? {},
      after,
      screenshots,
      repoSlug: CONFIG.repoSlug,
      baseRef: BASE_BRANCH,
      headRef: git(["rev-parse", "--abbrev-ref", "HEAD"]).toString("utf8").trim(),
      notes,
    });
  } catch (error) {
    die(error.message);
  }

  mkdirSync(OUT_DIR, { recursive: true });
  const reportPath = path.join(OUT_DIR, "report.md");
  writeFileSync(reportPath, `${report.markdown}\n`, "utf8");
  console.log(`\n${report.markdown}\n`);
  console.log(`✓ 리포트 — ${path.relative(REPO_ROOT, reportPath)} (라우트 ${report.rows.length}건 · 변경 ${report.changedCount}건)`);
  console.log("  PR 코멘트로 올리기: gh pr comment --body-file " + path.relative(REPO_ROOT, reportPath));
}

main().catch((error) => die(error.stack ?? String(error)));
