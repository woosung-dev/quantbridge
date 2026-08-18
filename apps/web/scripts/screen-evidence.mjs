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
 * authed leg 를 함께 돌린다 ([BL-797], 2026-08-18).
 *
 * ★**옵트인인 것은 의도다.** 공개 leg 는 자체 `next build` 만으로 돌아 `--pre-pr` 에서 유예 없이
 *   도는데, authed 는 BE 와 로그인 세션을 요구한다. 항상 켜면 그 전제가 없는 중간 검사에서
 *   공개 측정까지 함께 죽는다. `final-gates.sh` 는 이 플래그를 **유예 집합의 authed 레그**에서만 준다.
 */
const AUTHED = process.argv.includes("--authed");
/** 이번 실행이 그 라우트를 재는가. authed 행은 `--authed` 일 때만 범위에 든다. */
const inScope = (metrics) => (AUTHED ? true : metrics?.authed !== true);
const scopeOf = (routes) =>
  Object.fromEntries(Object.entries(routes ?? {}).filter(([, m]) => inScope(m)));
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

/**
 * `.env.local` 을 읽어 **명시적 override** 로 넘긴다.
 *
 * ★★★**왜 필요한가 (2026-08-18 실측).** `next start` 는 production 모드라 Next 가
 *   `.env.production.local` 을 `.env.local` **보다 우선**해서 읽는다. 이 레포의 그 파일은
 *   실제 배포 값이다 — `NEXT_PUBLIC_API_URL=https://qb-api.woosung.dev` ·
 *   `NEXT_PUBLIC_ENABLE_TEST_ORDER=false` · `BETTER_AUTH_URL=https://qb.woosung.dev`.
 *   그리고 `NEXT_PUBLIC_*` 는 **빌드 타임에 번들로 인라인**된다.
 *   ⇒ 종전 baseline 은 **gitignore 된 개인 파일에 의존해** 구워졌다. 그 파일이 없는 사람이
 *   같은 커밋에서 재면 다른 바이트가 나오고, 게이트는 그것을 「화면이 달라졌다」로 인쇄한다.
 *   authed 확장이 그것을 드러냈다 — 로그인이 **프로덕션 auth DB** 를 치려다 500 이 났다.
 * ★환경변수는 `.env*` 파일 전부를 이기므로, 여기서 넘기면 결정성이 회복된다.
 *
 * ★★★**전환이 만든 델타의 원인 — 내 첫 설명은 틀렸다** (적대 리뷰가 반증, 실측으로 확정).
 *   공개 3라우트가 각 +0.2 kB(gzip 후) 움직였는데, 나는 그것을 「`NEXT_PUBLIC_*` 문자열이
 *   인라인되니까」로 적었다. **부호가 반대다** — 새 값이 더 **짧다**(`https://qb-api.woosung.dev`
 *   → `http://localhost:8000`). 그리고 문자열 치환은 `totalRequests` +1 을 만들 수 없다.
 *   실측(같은 커밋에서 그 변수 하나만 바꿔 두 번 빌드): `NEXT_PUBLIC_ENABLE_TEST_ORDER`
 *   `false` → `.next/static` js/css **3,286,670 B** · `true` → **3,299,506 B**.
 *   ⇒ 진짜 원인은 **기능 플래그가 켜지며 dead code elimination 이 풀린 것**이다(+12,836 B 비압축).
 *   ★이것이 이 게이트가 존재하는 이유를 스스로 보여 준다 — **「설명됐다」와 「설명이 있다」는 다르다.**
 */
function localEnvOverrides() {
  const file = path.join(WEB_ROOT, ".env.local");
  if (!existsSync(file)) return {};
  const out = {};
  for (const line of readFileSync(file, "utf8").split("\n")) {
    const m = /^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$/.exec(line);
    if (!m) continue;
    let value = m[2].trim();
    const quoted = /^([\x27"])(.*)\1$/.exec(value);
    if (quoted) value = quoted[2];
    out[m[1]] = value;
  }
  return out;
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
  const rel = REPO_REL(CONFIG.baseline);

  // ★ref 를 아예 해석 못 하면 그것은 「baseline 이 아직 없다」가 아니라 **설정 오류**다.
  //   이 줄이 없으면 오타 하나가 before 를 통째로 지우고 「전부 신규」로 초록이 난다 —
  //   CONTROL 이 실측으로 확인했다(2026-08-17: `refs/heads/does-not-exist-xyz` 가 rc=0 이었다).
  if (!git(["rev-parse", "--verify", "--quiet", `${ref}^{commit}`], { allowFail: true })) {
    die(
      `base ref 를 해석할 수 없다: ${ref}\n` +
        "  ★이것을 「baseline 없음」으로 낮추면 모든 델타가 사라진 채 초록이 난다.",
    );
  }

  const blob = git(["show", `${ref}:${rel}`], { allowFail: true });
  if (blob) return JSON.parse(blob.toString("utf8")).routes ?? {};

  // ★「그 ref 에 baseline 이 아직 없다」와 「있는데 못 읽었다」는 다르다.
  //   둘을 같게 null 로 낮추면 ref 오타·손상 blob 이 전부 「신규」로 보고되고 rc=0 이 난다
  //   (codex 적대 리뷰 P2, 2026-08-17). 실재하는데 못 읽으면 죽는다.
  const listed = git(["ls-tree", "--name-only", ref, rel], { allowFail: true });
  if (listed && listed.toString("utf8").trim() !== "") {
    die(
      `${ref}:${rel} 이 실재하는데 읽지 못했다.\n` +
        "  ★이것을 「baseline 없음」으로 낮추면 모든 델타가 사라진 채 초록이 난다.",
    );
  }
  return null;
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

/**
 * authed 측정의 전제 셋을 **측정 전에** 잰다. 하나라도 없으면 죽는다.
 *
 * ★★조용한 skip 을 두지 않는 이유 — 이 게이트에서 「안 쟀다」와 「변경 없음」은 **같은 Δ=0** 으로
 *   보인다. 이 레포는 그 병을 소크 게이트 C4(볼 창이 없으면 통과)와 `tool-pin-audit`(핀 0건이면
 *   통과)에서 두 번 밟았다. 전제가 없으면 초록을 내지 않는다.
 * ★★★**포트를 보는 곳이 둘이다** — BE 의 `FRONTEND_URL`(CORS allow_origins) 과
 *   `BETTER_AUTH_URL`(JWKS 취득 + JWT issuer). 러너는 `next start` 를 `serverPortBase + slot`
 *   에 띄우므로 개발용 `:3000` 을 아는 BE 로는 **CORS 가 조용히 거부**한다. 2026-08-18 night4 가
 *   같은 비대칭으로 두 번 오진했다("서버가 안 떴다" → 실제로는 포트 불일치).
 */
async function assertAuthedPrereqs(baseURL, localEnv) {
  // ★storageState 부재는 **죽일 일이 아니다** (codex 적대 리뷰 P2, 2026-08-19). 그 파일을 만드는
  //   것은 authed project 의 `setup` dependency 이고, 그것은 **이 프로브 뒤에** 돈다. 여기서
  //   죽이면 fresh 워크스페이스는 setup 이 파일을 만들 기회를 영영 못 얻는다.
  //   ⇒ 안내만 남긴다. 실제로 못 만들면 그때 playwright 가 red 를 낸다(그쪽이 정확한 증인이다).
  const storage = path.join(WEB_ROOT, "e2e/.auth/storageState.json");
  const storageNote = existsSync(storage) ? "storageState 있음" : "storageState 없음 — setup 이 만든다";

  // ★★**빌드·서버에 준 것과 같은 값으로 잰다** (codex 적대 리뷰 P1, 2026-08-19).
  //   초판은 `process.loadEnvFile` 로 `.env.local` 을 읽고 `process.env` 에서 꺼냈는데,
  //   **`loadEnvFile` 은 이미 있는 키를 덮지 않는다**(실측 확인). 셸에 옛 `NEXT_PUBLIC_API_URL`
  //   이 남아 있으면 프로브는 **다른 API** 의 health·CORS 를 통과시키고, 브라우저는 실제 API 에
  //   CORS 로 막힌다. 그 실패는 `requestfailed` 라 spec 의 응답 수집에 안 잡히고, 번들 값이
  //   같으면 **초록**이 난다 — 이 게이트가 막으려는 바로 그 모양이다.
  const apiUrl = (localEnv.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");

  let health;
  try {
    health = await fetch(`${apiUrl}/health`, { signal: AbortSignal.timeout(5_000) });
  } catch (error) {
    die(
      `authed 측정 전제 — BE 에 닿지 않는다 (${apiUrl}/health): ${error.message}\n` +
        `  띄워라: cd apps/api && set -a; . ./.env.local; set +a; \\\n` +
        `    FRONTEND_URL=${baseURL} BETTER_AUTH_URL=${baseURL} uv run uvicorn src.main:app --port ${new URL(apiUrl).port}`,
    );
  }
  if (!health.ok) die(`authed 측정 전제 — BE \`/health\` 가 ${health.status} 다 (${apiUrl}).`);

  // ★CORS 프로브. 인증 없이 401 이 나도 **CORS 헤더는 붙으므로** 토큰 없이 잴 수 있다(실측 확인).
  //   양성/음성 대조: origin 이 맞으면 `access-control-allow-origin` 이 오고, 다르면 안 온다.
  let allowed = null;
  try {
    const res = await fetch(`${apiUrl}/api/v1/strategies`, {
      headers: { Origin: baseURL },
      signal: AbortSignal.timeout(5_000),
    });
    allowed = res.headers.get("access-control-allow-origin");
  } catch (error) {
    die(`authed 측정 전제 — CORS 프로브가 실패했다: ${error.message}`);
  }
  if (allowed !== baseURL)
    die(
      `authed 측정 전제 — BE 의 CORS origin 이 이 서버와 다르다.\n` +
        `  측정 서버: ${baseURL}\n` +
        `  BE 가 허용: ${allowed ?? "(헤더 없음 — 거부)"}\n` +
        `  ★BE 는 origin 을 **두 곳**에서 본다. 둘 다 맞춰라:\n` +
        `    FRONTEND_URL=${baseURL}    (CORS allow_origins — 단일 값이다)\n` +
        `    BETTER_AUTH_URL=${baseURL} (JWKS 취득 URL + JWT issuer)\n` +
        `  이대로 재면 화면이 데이터를 못 받고, 그 결과는 red 가 아니라 **더 가벼운 번들**로 보인다.`,
    );
  console.log(`  authed 전제 OK — BE ${apiUrl} · CORS origin ${allowed} · ${storageNote}`);
}

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
  const localEnv = localEnvOverrides();
  const localEnvCount = Object.keys(localEnv).length;
  if (localEnvCount > 0)
    console.log(`  .env.local override ${localEnvCount}건 주입 — .env.production.local 을 덮는다`);

  const build = run("pnpm", ["exec", "next", "build"], {
    env: { ...localEnv, BETTER_AUTH_URL: baseURL },
  });
  if (build.status !== 0) die(`\`next build\` 가 rc=${build.status} 로 실패했다. 번들을 잴 수 없다.`);

  // ⑵ 프로덕션 서버.
  // ★`next start` 는 `output: "standalone"` 설정 때문에 경고를 한 줄 찍지만 **정상 서빙한다**
  //   (2026-08-17 실측: `/` 200 · `/_next/static/chunks/*.js` 200 28,559B). standalone 산출물은
  //   `.next/static` 을 스스로 안 품어서 그쪽으로 띄우면 자산이 404 가 되고 번들 바이트가 0 이 된다.
  const server = spawn("pnpm", ["exec", "next", "start", "-p", String(port)], {
    cwd: WEB_ROOT,
    env: { ...process.env, ...localEnv, BETTER_AUTH_URL: baseURL },
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

    // ★authed leg 는 **공개 leg 가 성립한 뒤에** 돈다. 앞이 깨졌으면 전제 프로브에 시간을
    //   쓰지 않는다. 측정 JSON 은 같은 폴더에 쌓이고 아래에서 한꺼번에 읽는다.
    if (AUTHED && playwrightStatus === 0) {
      await assertAuthedPrereqs(baseURL, localEnv);
      const pwAuthed = run(
        "pnpm",
        ["exec", "playwright", "test", "--project=chromium-screen-evidence-authed"],
        {
          env: {
            PLAYWRIGHT_BASE_URL: baseURL,
            PW_ARTIFACT_RUN: RUN,
            ...(UPDATE ? { SCREEN_EVIDENCE_UPDATE: "1" } : {}),
          },
        },
      );
      playwrightStatus = pwAuthed.status;
    }
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
      ...(m.authed ? { authed: true } : {}),
    };
  }

  if (UPDATE) {
    if (playwrightStatus !== 0)
      die(`갱신 모드인데 playwright 가 rc=${playwrightStatus} 로 실패했다 — baseline 을 쓰지 않는다.`);
    // ★★**범위 밖 행을 보존한다.** `--authed` 없이 `:update` 를 돌리면 이번 실행은 공개
    //   라우트만 쟀는데, 그 결과로 baseline 을 덮어쓰면 authed 행이 **통째로 사라진다** —
    //   그리고 그 삭제는 다음 실행에서 「신규 라우트」로 보여 아무도 눈치채지 못한다.
    const existing = readBaselineHere() ?? {};
    const preserved = Object.fromEntries(Object.entries(existing).filter(([, m]) => !inScope(m)));
    // ★★**범위 안인데 이번에 안 잰 라우트는 「삭제」다 — 조용히 하지 않는다** (codex 적대 리뷰 P1,
    //   2026-08-19). `--authed` 로 돌리면 모든 행이 범위 안이라 위 `preserved` 가 비고, 그러면
    //   ROUTES 에서 한 건이 실수로 빠진 채 `:update` 를 돌린 회차가 **그 라우트를 baseline 에서
    //   지우고** 이후 검사는 그것을 요구하지 않는다 — 커버리지가 사라진 채 초록이 된다.
    //   check 모드의 키 집합 대조(`mjs` 아래)가 막는 것과 같은 사고를 update 모드가 열어 두면 안 된다.
    const dropped = Object.keys(existing).filter((k) => inScope(existing[k]) && !(k in measured));
    if (dropped.length > 0)
      die(
        `baseline 에 있던 라우트를 이번 실행이 재지 않았다: ${dropped.join(", ")}\n` +
          "  이대로 갱신하면 그 행이 **삭제**되고, 이후 게이트는 그 라우트를 요구하지 않는다.\n" +
          "  ★의도한 삭제라면 baseline 에서 그 키를 먼저 손으로 지우고 다시 돌려라 — 삭제는 명시적이어야 한다.\n" +
          "  ★의도하지 않았다면 spec 의 ROUTES 에서 그 라우트가 빠졌는지 확인해라.",
      );
    const nextRoutes = { ...preserved, ...measured };
    writeFileSync(
      BASELINE_ABS,
      `${JSON.stringify(
        {
          _comment:
            "[BL-797] 화면 증거 팩 baseline. `pnpm screen-evidence:update` 가 쓴다 — 손으로 고치지 마라. " +
            "이 파일의 origin/main 판이 PR 리포트의 **before** 이고, 이 브랜치 판이 **after** 다.",
          platform: process.platform,
          routes: Object.fromEntries(Object.entries(nextRoutes).sort(([a], [b]) => a.localeCompare(b))),
        },
        null,
        2,
      )}\n`,
      "utf8",
    );
    console.log(
      `\n✓ baseline 갱신 — ${path.relative(REPO_ROOT, BASELINE_ABS)} ` +
        `(이번에 잰 라우트 ${Object.keys(measured).length}건 · 범위 밖 보존 ${Object.keys(preserved).length}건)`,
    );
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
  const after = scopeOf(readBaselineHere());
  if (!after || Object.keys(after).length === 0) die(`baseline 이 없다 — ${path.relative(REPO_ROOT, BASELINE_ABS)}. \`:update\` 를 먼저 돌려라.`);

  // ★`measured` 는 「이번에 실제로 잰 것」이고 `after` 는 「커밋된 baseline 전체」다.
  //   둘이 어긋나면 재지 않은 라우트의 낡은 수치가 리포트에 정상 측정처럼 실린다 —
  //   ROUTES 에서 한 건이 빠져도 나머지가 통과하면 게이트가 초록이었다
  //   (codex 적대 리뷰 P2, 2026-08-17). 「일부만 봤다」를 「전부 봤다」로 인쇄하지 않는다.
  const measuredKeys = Object.keys(measured).sort();
  const afterKeys = Object.keys(after).sort();
  if (measuredKeys.join("\u0000") !== afterKeys.join("\u0000")) {
    const missing = afterKeys.filter((k) => !measuredKeys.includes(k));
    const extra = measuredKeys.filter((k) => !afterKeys.includes(k));
    die(
      "이번 실행이 잰 라우트 집합이 baseline 과 다르다 — 부분 측정을 전량으로 보고하지 않는다.\n" +
        `  baseline: ${afterKeys.join(", ") || "(없음)"}\n` +
        `  측정됨  : ${measuredKeys.join(", ") || "(없음)"}\n` +
        (missing.length ? `  ★안 잰 것: ${missing.join(", ")}\n` : "") +
        (extra.length ? `  ★baseline 에 없는 것: ${extra.join(", ")} — \`:update\` 를 돌려라\n` : ""),
    );
  }

  const before = scopeOf(readBaselineFrom(BASE_REF));

  const screenshots = {};
  for (const route of new Set([...Object.keys(before ?? {}), ...Object.keys(after)])) {
    const entry = after[route] ?? before?.[route];
    // ★수치 전용 라우트(`screenshot: null`)는 **명시적 null** 로 넘긴다 — `buildReport` 가
    //   `Object.hasOwn` 으로 「선언된 null」과 「키의 부재」를 가르므로, 여기서 continue 해
    //   키를 안 만들면 그쪽이 측정 실패로 판정해 던진다. 둘은 다른 상태다.
    if (entry && entry.screenshot === null) {
      screenshots[route] = null;
      continue;
    }
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
    "first-load JS = 그 화면이 받은 `/_next/static/**.{js,css}` 의 **전송 바이트**(gzip 후) 합 — 폰트 제외. ★`next build` 가 인쇄하는 동명 지표(초기 HTML 이 참조하는 청크)와 **다른 양**이다 — 이쪽은 idle 창 안에 도착한 전부라 그 **초집합**이고, 그래서 `next/dynamic` 으로 옮긴 청크도 마운트 시 도착하면 그대로 계수된다(지연 로딩 개선을 이 축으로는 못 잰다 — [BL-809])",
    "요청 수 = `networkidle` + 1초 창 안의 건수. API 는 `/api/v1/` 부분집합이고, 공개 라우트는 실측 0이라 전체 요청 수가 계수기의 생존 앵커다",
    "실패 응답이 하나라도 있으면 「변화」가 아니라 **측정 오염**으로 red 를 낸다([BL-786] 의 성질을 재사용)",
    AUTHED
      ? "authed 라우트는 **수치 전용**이다(화면 열이 `—`). 실데이터가 매 실행 픽셀을 흔들어 `maxDiffPixels: 0` 을 유지할 수 없고, 임계를 올리면 그 축은 글자 한 자 변경을 삼켜 존재 이유를 잃는다([BL-797])"
      : "★이번 실행은 **공개 라우트만** 쟀다. authed 행은 표에서 제외됐다 — 재려면 `--authed` 로 돌리고 BE 를 같은 origin 으로 띄워라",
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
