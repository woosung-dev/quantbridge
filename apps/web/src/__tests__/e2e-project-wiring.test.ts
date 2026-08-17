// 모든 e2e spec 이 playwright project 에 **정확히 하나** 물려 있는지 동결한다.
//
// ★왜 필요한가. `playwright.config.ts` 의 project 는 `testMatch` 정규식으로 spec 을 고른다.
// 그 목록이 **파일명 열거식**이면, 새 spec 을 추가하고 목록에 안 적었을 때 그 spec 은
// **발견조차 되지 않는다** — 테스트가 0건 실행돼도 playwright 는 초록이다. 설정 파일의
// 주석이 스스로 그 위험을 경고하고 있었다("열거식 testMatch 라 파일명을 여기 넣지 않으면
// spec 이 발견조차 안 된다 (coverage 함정)"). 실제로 `sprint55-optimizer-bayesian` 이
// 고아가 된 전력이 있다.
//
// ★반대 방향도 막는다. 한 spec 이 **두 project** 에 물리면 같은 테스트가 중복 실행된다.
// 이 감사를 처음 돌렸을 때 `live-smoke.spec.ts` 가 정확히 그 상태였다 —
// `chromium` 의 `/smoke\.spec\.ts$/` 가 앵커가 없어 `live-smoke.spec.ts` 까지 잡았고,
// 전용 project(`chromium-live-smoke`)와 겹쳤다. 그래서 `pnpm e2e` 가 live-smoke 를
// 매번 덤으로 돌리고 있었다.
//
// ★이 테스트는 config 를 **파싱**하지 않고 **import** 한다 — 정규식을 문자열로 다시 쓰면
// 실제 배선이 아니라 내 복사본을 검사하게 된다(이 레포가 반복해서 밟은 함정).
//
// ★★**세 번째 구멍 — 「project 에 물렸다」는 「어디선가 돈다」가 아니다** ([BL-789], 2026-08-17).
// 위 두 감사는 spec ↔ project 배선만 본다. 그런데 `chromium-authed` 는 **PR CI 에서 한 번도
// 호출되지 않는다** — `.github/workflows/*.yml` 이 부르는 것은 `--project=chromium` ·
// `chromium-live-smoke` · `chromium-design-canon` 뿐이다. 즉 authed 계열 spec 20개는
// CI 실행 표면이 0 이고, **CI 전건 초록이 그 spec 들의 통과를 뜻하지 않는다.** 아래
// 「CI 실행 표면」 감사가 그 사실을 코드로 고정한다 — CI 에서 안 도는 project 는
// `LOCAL_ONLY` 에 **사유와 함께** 등재돼야 하고, 새 project 를 만들고 워크플로에 안
// 배선하면 빨개진다.
//
// ★★★**이 감사는 「무엇이 그것을 발화시키나」를 일곱 번 틀렸다** (2026-08-17 적대 리뷰 3회 실측).
// 일곱 다 fail-**open** 이었고 일곱 다 같은 병이다 — 「그렇게 적혀 있다」를 「그것이 돈다」로 읽었다:
//   ⑴ `- name: TODO --project=X 되살리기` 같은 **스텝 제목** → 이제 `run:` 본문만 본다(`runScripts`).
//   ⑵ schedule/dispatch 전용 워크플로의 배선 → 이제 `on:` 에 `pull_request` 계열이 있는 것만 센다.
//   ⑶ `--project` 없는 맨 `playwright test`(`pnpm e2e:all` 이 그 형태)를 「fail-closed 라 괜찮다」고
//      적었는데 다른 `--project=` 호출과 **공존**하면 fail-open → 이제 전 project 실행으로 센다.
//   ⑷ `run: echo --project=chromium-authed` 한 줄 → 이제 ⓐ `if: false` 인 job/step 을 지우고
//      ⓑ **playwright 를 실제로 부르는 명령 안에서만** `--project=` 를 센다.
//   ⑸ `LOCAL_ONLY` 사유를 `?.trim()` 으로만 재서 `"."` 한 글자면 면제됐다 → 이제 `[BL-NNN]`/
//      `[ADR-NNN]` 원장 식별자를 최소 1개 요구한다.
//   ⑹ **가장 심각** — `--project=${{ matrix.project }}` 가 이름 정규식(`[A-Za-z0-9_.:-]`)에 안 걸려
//      `named=[]` 가 되고 「맨 호출」 분기로 떨어져 **전 project 를 CI 실행으로 등록**했다. matrix 는
//      적대 문법이 아니라 정상 패턴이다 → 이제 `${{ … }}` 는 **모른다**로 두고 안 센다(fail-closed).
//   ⑺ 줄 끝 주석을 안 지워 ⓐ 살아 있는 호출의 `… # TODO --project=chromium-authed` 가 배선으로
//      읽혔고 ⓑ `if: false # 잠시 꺼둔다` 가 `DEAD_IF` 의 `\s*$` 에 안 걸려 죽은 스텝이 살아 있는
//      것으로 세졌다 → `stripYamlComments` 가 **공백 뒤의 `#`** 부터 자른다.
//
// ★★**이 감사가 재지 못하는 것** (거짓 안심을 만들지 않기 위해 명시한다 — 이 레포의 상습 사고다):
//   • **셸 제어흐름을 해석하지 않는다.** `false && playwright test --project=X` 처럼 **의도적으로
//     죽인** 호출도 배선으로 센다. 명령 분해는 **줄 단위**라 한 줄을 `&&`·`;`·`|` 로 이어 쓴 것은
//     하나의 명령이고, 그 줄이 playwright 를 부르면 같은 줄의 `--project=` 는 전부 배선이다.
//     ★**이 감사가 막는 것은 「사고」다** — 배선을 지움 · project 이름 오타 · 새 project 를 만들고
//     워크플로에 안 붙임. **적대적 저자가 아니다.** 단락 평가를 흉내 내던 판이 있었는데 그 모델링
//     자신이 새 fail-open 3건의 출처여서 걷어냈다(2026-08-17 CONTROL 판정).
//   • **`paths:` 필터를 해석하지 않는다.** `live-smoke.yml` 의 `paths:`(`:17`)는 `apps/web/src/**`
//     계열과 `apps/web/package.json`·`pnpm-lock.yaml` 뿐이라 **`apps/web/e2e/**` 만 고친 PR 에서는
//     0회 실행**인데, 이 감사는 「PR 트리거 + playwright 호출」만 보고 「돈다」로 센다.
//   • **job/step 의 `if:` 조건식을 평가하지 않는다.** 리터럴 `false` 만 죽은 것으로 본다(주석은
//     먼저 지우므로 `if: false # …` 도 잡는다). `if: needs.changes.outputs.frontend == 'true'` 처럼
//     입력에 따라 skip 되는 잡은 「돈다」로 센다 (`ci.yml` 의 e2e 잡이 정확히 그 형태다).
//   • **`uses:` 액션·재사용 워크플로를 따라가지 않고 `--project=${{ … }}` 값도 풀지 않는다.**
//     둘 다 「모른다」로 두므로 그 형태로**만** 배선하면 「아무 데서도 안 돈다」로 읽혀 빨개진다
//     = fail-closed. ★이 자리의 종전 주석이 「matrix 는 fail-closed」라 적었는데 ⑹ 대로
//     **정반대(fail-open)** 였다 — 주석이 코드보다 앞서 나간 실사고다.
//   • **주석 제거는 「공백 + `#`」만 본다.** 따옴표 안의 `#` 도 자르고(과다 절단 = fail-closed 방향)
//     공백 없는 `foo#bar` 는 못 자른다. 완전한 YAML 파싱은 하지 않는다 — 그 파서가 새 결함의 출처다.
//   ⇒ 이것들은 정적 YAML 파싱의 **원리적 한계**다. 완전 해결은 [BL-789] 2단계(실제 CI 배선 +
//     PR 체크에서의 실행 증거)에 속하고, 이 파일이 할 수 있는 것은 **한계를 적어 두는 것**뿐이다.
// ★그리고 이 파일 자신이 **CI 에서 안 돌 수 있었다** — `ci.yml` 의 `frontend` 필터가
// `apps/web/**` 뿐이라 **워크플로만 고친 PR** 에서는 이 감사가 통째로 skip 됐다(= 감사의
// 입력을 고치는 회차에 감사가 안 돈다). `ci.yml` 의 `frontend:` 필터와 `final-gates.sh` 의
// FE vitest 조건에 `.github/workflows/**` 를 넣어 닫았다.

import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

import config from "../../playwright.config";
import ciAuthedManifest from "../../e2e/ci-authed-manifest.json";

const E2E_DIR = path.resolve(__dirname, "../../e2e");
const REPO_ROOT = path.resolve(__dirname, "../../../..");
const WORKFLOW_DIR = path.join(REPO_ROOT, ".github/workflows");
const WEB_PACKAGE_JSON = path.resolve(__dirname, "../../package.json");
const CI_AUTHED_MANIFEST = ciAuthedManifest as {
  ci: string[];
  localOnly: Record<string, string>;
};

/**
 * CI 에서 **의도적으로** 안 도는 project — 이름 → 사유.
 *
 * ★사유 없이 넣지 마라. 이 상수는 「빠뜨린 것」과 「일부러 뺀 것」을 가르는 유일한 장치이고,
 * 사유가 없으면 다음 사람은 둘을 구분할 수 없다.
 * ★★사유에는 **`[BL-NNN]` 또는 `[ADR-NNN]` 원장 식별자가 최소 1개** 있어야 한다(`LEDGER_REF`).
 * 종전 계약은 「공백 아닌 문자열」뿐이라 `"."` 한 글자로도 전건 초록이었다(2026-08-17 적대 리뷰 실측).
 */
const LOCAL_ONLY: Record<string, string> = {
  "chromium-screen-evidence":
    "[BL-797] 1단계(로컬 산출)만 착수. CI 로 올리려면 둘이 더 필요하다 — ⑴ 스크린샷 baseline 이 " +
    "**플랫폼 의존**이라(`{platform}` 접미 · 맥에서 구운 `-darwin` 판을 리눅스 러너가 쓸 수 없다) " +
    "CI 용 `-linux` baseline 을 별도로 굽고 관리해야 하고 ⑵ 이 project 는 `next build` + " +
    "`next start` 프로덕션 서버를 상대로 도는데 현재 CI e2e 잡은 dev 서버만 띄운다. " +
    "★그래서 **CI 초록은 화면 증거 팩이 돌았다는 증거가 아니다** — 증인은 " +
    "`final-gates.sh` 의 `화면 증거 팩` 레그와 `pnpm screen-evidence` 뿐이다.",
};

/** PR 체크로 발화하는 트리거 — 이것이 없으면 「PR 이 초록이다」와 무관한 워크플로다. */
const PR_TRIGGERS = ["pull_request", "pull_request_target", "merge_group"];

/**
 * `LOCAL_ONLY` 사유가 만족해야 하는 계약 — 원장 식별자 1개 이상.
 *
 * ★이 레포에서 「왜 CI 에 안 올렸나」는 **원장이** 답한다. 번호를 요구하면 사유가
 * 되짚을 수 있는 것이 되고, 그 BL 이 닫힐 때 면제도 같이 걷힌다. 산문만으로는 그게 안 된다.
 */
const LEDGER_REF = /\[(?:BL|ADR)-\d{1,4}\]/;

/**
 * YAML 주석 제거 — 통줄 주석은 줄째, **줄 끝 주석은 공백 뒤의 `#` 부터** 자른다.
 *
 * ★★줄 끝 주석은 적대 문법이 아니라 정상 문법이다. 안 지우면 둘이 샜다(파일 머리 ⑺).
 * ★한계: 따옴표 안의 `#` 도 자르고(과다 절단 = fail-closed 방향) 공백 없는 `foo#bar` 는 못 자른다.
 */
function stripYamlComments(text: string): string {
  return text
    .split("\n")
    .filter((line) => !/^\s*#/.test(line))
    .map((line) => line.replace(/\s+#.*$/, ""))
    .join("\n");
}

function matchAll(text: string, re: RegExp): string[] {
  return [...text.matchAll(re)].map((m) => m[1] ?? "");
}

/**
 * 리터럴로 죽은 조건만 센다 — `if: false` · `if: ${{ false }}` · 따옴표 형태.
 * ★줄 끝 주석은 `stripYamlComments` 가 **먼저** 지우므로 `if: false # 잠시 꺼둔다` 도 여기 걸린다.
 */
const DEAD_IF = /^(\s*)(-\s+)?if:\s*['"]?(?:\$\{\{\s*)?false(?:\s*\}\})?['"]?\s*$/;

/**
 * `if: false` 로 **명백히 죽은** job/step 을 통째로 지운다.
 *
 * ★★죽은 스텝에 `--project=` 를 적어 두면 종전 감사는 「CI 에서 돈다」로 셌다. 그건
 * 「돌았다고 적혀 있는데 실제로는 0건」 — 이 파일이 세 번 고쳐 온 병 그 자체다.
 * ★블록 범위는 `if:` 의 **키 컬럼**(대시를 포함해 센다) 이상 들여쓰기가 이어지는 구간이고,
 * `if:` 는 `run:` 앞에 올 수도 뒤에 올 수도 있으므로 **앞쪽으로도** 넓혀야 한다.
 * ★★앞쪽 경계는 **들여쓰기만으로 정하면 안 된다**. `- if: false` 처럼 `if:` 가 대시 위에
 * 있으면 그 줄이 곧 항목의 시작이라 볼 것이 없는데, 들여쓰기만 보면 **앞 스텝의 `run:` 이
 * 같은 컬럼**이라 살아 있는 이웃을 지운다. 반대로 `- run: … / if: false` 처럼 대시 줄에
 * `run:` 이 붙어 있으면 그 머리줄을 안 지워 **죽은 호출이 살아남는다**(fail-open). 그래서
 * ⑴ 대시 위의 `if:` 는 앞쪽을 안 보고 ⑵ 아니면 같은 항목의 **머리줄까지** 지운다.
 * ★한계: 리터럴 `false` 만 죽은 것으로 본다. 조건식(`needs.*`·`github.*`)은 평가하지 않고
 * 「돈다」로 센다 — `ci.yml` 의 e2e 잡이 그 형태라 반대로 하면 실 배선이 상시 red 다(파일 머리 참조).
 */
function stripDeadBranches(text: string): string {
  const lines = text.split("\n");
  const indentOf = (line: string): number => line.length - line.trimStart().length;
  const dead = new Set<number>();

  for (let i = 0; i < lines.length; i++) {
    const head = DEAD_IF.exec(lines[i] ?? "");
    if (!head) continue;
    const dashLen = (head[2] ?? "").length;
    const keyCol = (head[1] ?? "").length + dashLen;
    dead.add(i);

    // 앞쪽 — `- if: false` 는 그 줄이 항목의 시작이라 앞을 안 본다.
    if (dashLen === 0) {
      for (let j = i - 1; j >= 0; j--) {
        const line = lines[j] ?? "";
        if (line.trim() === "") {
          dead.add(j);
          continue;
        }
        const item = /^(\s*)(-\s+)/.exec(line);
        if (item && (item[1] ?? "").length + (item[2] ?? "").length === keyCol) {
          dead.add(j); // 같은 항목의 머리줄(`- run: …`) — 여기까지가 이 스텝이다
          break;
        }
        if (indentOf(line) >= keyCol) {
          dead.add(j);
          continue;
        }
        break; // 상위 블록 — 남의 것이다
      }
    }

    // 뒤쪽 — 같은 블록이 이어지는 동안.
    for (let j = i + 1; j < lines.length; j++) {
      const line = lines[j] ?? "";
      if (line.trim() === "" || indentOf(line) >= keyCol) {
        dead.add(j);
        continue;
      }
      break;
    }
  }
  return lines.filter((_, i) => !dead.has(i)).join("\n");
}

/**
 * 이 워크플로가 **PR 체크로 발화하는가** — 최상위 `on:` 에 `pull_request` 계열이 있는가.
 *
 * ★★없으면 「CI 에서 돈다」로 세면 안 된다. `trust-layer-nightly.yml`(schedule+dispatch) 나
 * `nightly-real-broker.yml`(dispatch 전용) 에 `--project=chromium-authed` 를 배선하는 것만으로
 * 이 감사를 통과시킬 수 있었고, 그때도 **PR CI 는 authed 를 0회 돈다** — 이 절이 막으려던
 * 거짓 초록 그 자체다(2026-08-17 적대 리뷰가 실측으로 재현).
 * ★`push:` 는 세지 않는다 — 머지 **뒤**에 도는 트리거라 PR 을 막지 못한다.
 * ★키가 `"on":` 로 따옴표에 싸인 형태도 받는다(`nightly-real-broker.yml` 이 그렇다).
 */
function isPullRequestGated(workflowText: string): boolean {
  const lines = stripYamlComments(workflowText).split("\n");
  for (let i = 0; i < lines.length; i++) {
    const head = /^(["']?)on\1\s*:(.*)$/.exec(lines[i] ?? "");
    if (!head) continue;
    const block = [head[2] ?? ""]; // `on: [push, pull_request]` 인라인 형태
    for (let j = i + 1; j < lines.length; j++) {
      const line = lines[j] ?? "";
      if (line.trim() === "") continue;
      if (!/^\s/.test(line)) break; // 다음 최상위 키
      block.push(line);
    }
    const text = block.join("\n");
    return PR_TRIGGERS.some((t) => new RegExp(`\\b${t}\\b`).test(text));
  }
  return false;
}

/**
 * 워크플로에서 **`run:` 스텝의 셸 본문만** 뽑는다.
 *
 * ★★`name:`·`if:`·`env:` 같은 스칼라 값은 실행이 아니다. YAML 본문 전체를 정규식으로 훑으면
 * `- name: TODO 언젠가 --project=chromium-authed 를 되살릴 것` 같은 **스텝 제목**이 배선으로
 * 읽힌다 — 이 파일이 주석에 대해 막아 둔 병이 다른 문법으로 그대로 남아 있었다(적대 리뷰 실측).
 * `ci.yml`·`live-smoke.yml` 은 이미 `- name: Run live smoke (chromium-live-smoke project)` 같은
 * 서술형 스텝명을 쓰므로 가상의 위험이 아니다.
 *
 * ★한계: `uses:` 액션의 `with:` 인자로 playwright 를 부르는 형태는 모델링하지 않는다. 그 경우
 * 「아무 데서도 안 돈다」로 읽혀 아래 본체 단언 ⑷ 가 빨개진다 = fail-closed.
 *
 * ★★**접기(`>`)와 그대로(`|`)를 구분해야 한다.** `ci.yml` 의 e2e 스텝이 `run: >` 로 한 명령을
 * 두 줄에 쓴다 — 이것을 줄바꿈으로 이어 붙이면 `pnpm exec playwright test` 와
 * `--project=…` 가 **다른 명령**으로 쪼개져 「`--project` 없는 맨 호출」로 오독된다
 * (실제로 첫 구현이 그렇게 읽어 authed 를 「CI 에서 돈다」로 판정했다).
 */
function runScripts(text: string): string[] {
  const lines = text.split("\n");
  const out: string[] = [];
  for (let i = 0; i < lines.length; i++) {
    const head = /^(\s*(?:-\s+)?)run:(.*)$/.exec(lines[i] ?? "");
    if (!head) continue;
    const keyCol = (head[1] ?? "").length;
    const first = (head[2] ?? "").trim();
    const isIndicator = /^[|>][-+]?\d*$/.test(first);
    // `|` = 그대로(줄이 곧 명령) · `>` 와 지시자 없는 평문 = 접기(줄이 공백으로 이어진다).
    const joiner = first.startsWith("|") ? "\n" : " ";
    const body = first === "" || isIndicator ? [] : [first];
    let j = i + 1;
    for (; j < lines.length; j++) {
      const line = lines[j] ?? "";
      if (line.trim() === "") continue;
      if (line.length - line.trimStart().length <= keyCol) break;
      body.push(line.trim());
    }
    i = j - 1;
    out.push(body.join(joiner));
  }
  return out;
}

/**
 * 셸 본문을 **줄 단위** 명령으로 쪼갠다. 도달 가능성은 따지지 않는다 — 그냥 다 본다.
 *
 * ★역슬래시 줄바꿈은 먼저 잇는다. 안 그러면 `playwright test \` + `--project=X` 가 두 명령이
 * 되고, 앞 조각이 「`--project` 없는 맨 호출」로 읽혀 전 project 실행으로 오판된다(fail-open).
 *
 * ★★**셸 제어흐름은 해석하지 않는다** (2026-08-17 CONTROL 판정). 한때 `&&`/`||` 단락 평가와
 * `;`·파이프 토큰을 흉내 내는 판이 있었지만, 그것이 막으려던 `false && playwright test` 는
 * **적대적 저자만** 쓰는 형태인 반면 그 모델링 자신이 새 fail-open 3건을 낳아 걷어냈다.
 * 그래서 한 줄 안의 `&&`·`;`·`|` 는 경계가 아니고, 그 줄이 playwright 를 부르면 같은 줄의
 * `--project=` 는 전부 배선으로 센다(`echo --project=X && playwright test` 는 과다 계수).
 */
function commands(script: string): string[] {
  return script
    .replace(/\\\n/g, " ")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

/**
 * 워크플로 본문이 **실제로 실행하는** playwright project 이름.
 *
 * ★주석을 먼저 지운다. `ci.yml` 은 「P1 4라우트는 전부 authed 라 로컬 `pnpm e2e:authed` 몫이고
 * CI 에는 없다」 같은 산문을 갖고 있다 — 산문을 배선으로 읽으면 이 감사는 정확히 반대 답을 낸다.
 * 이 레포는 **주석 문자열이 감사기를 통과시킨 사고**를 이미 겪었다(2026-08-16 layout-alignment).
 * ★줄 끝 주석도 지운다 — 한계는 `stripYamlComments` 참조.
 *
 * ★`pnpm <script>` 도 푼다 — `package.json` 스크립트가 `--project=` 를 품고 있으면 그것도 실행이다.
 * ★★`--project` **없는** `playwright test` 는 **전 project 실행**으로 센다. `package.json` 의
 * `e2e:all` 이 정확히 그 형태다. 종전 주석은 이것을 「모델링 안 함 = fail-closed」라고 적었는데
 * 반대였다 — 다른 `--project=` 호출과 공존하면 `direct` 가 비지 않아 ABORT 도 안 걸리고,
 * authed 가 CI 에서 실제로 도는데도 `LOCAL_ONLY` 의 「CI 에서 안 돈다」가 거짓인 채 초록이 된다.
 *
 * ★★★**`--project=` 는 playwright 를 실제로 부르는 명령 안에서만 센다** (2026-08-17 2차 적대
 * 리뷰). 종전에는 명령 종류를 안 보고 전부 실행으로 등록해서 `run: echo --project=chromium-authed`
 * **한 줄**이면 「CI 에서 authed 가 돈다」로 판정했다 — playwright 는 0회 돈다. 이제 ⑴ `if: false`
 * 인 job/step 을 통째로 지우고(`stripDeadBranches`) ⑵ 남은 명령 중 playwright 를 부르는 것만 본다.
 * ★「호출이다」의 판정은 ⓐ 명령**줄** 어딘가에 `playwright test` 가 있거나(부분 매치 —
 * `pnpm exec …`·`npx …` 를 다 받으려는 것이고, 대가로 같은 줄에 섞인 산문의 `--project=` 도
 * 세진다) ⓑ 그 명령이 부른 `pnpm` 스크립트가 (전이적으로) playwright 를 부르는 경우다.
 * ★★`--project` 값이 `${{ … }}` 표현식이면 **모른다**로 두고 그 호출에서 아무것도 안 센다.
 * 판정 못 하는 형태를 안 세는 것이 fail-closed 다 — 실행을 놓치면 그 project 는 「아무 데서도
 * 안 돈다」로 읽혀 본체 단언 ⑷ 가 빨개진다. 반대로 「모르니 맨 호출 = 전 project」로 떨어지면
 * matrix 배선 한 줄이 전 project 를 CI 실행으로 등록한다(파일 머리 ⑹).
 */
function executedProjects(
  workflowText: string,
  scripts: Record<string, string>,
  allProjects: string[],
): Set<string> {
  const out = new Set<string>();
  /** pnpm 스크립트 이름 → 그 본문이 playwright 를 부르는가 (순환 방지 겸 메모). */
  const scriptInvokes = new Map<string, boolean>();

  /** @returns 이 셸 본문이 playwright 를 한 번이라도 부르는가. */
  const walk = (script: string): boolean => {
    let invokesPlaywright = false;
    for (const cmd of commands(script)) {
      // pnpm 스크립트를 먼저 푼다 — 그 본문이 playwright 를 부르면 이 명령도 playwright 호출이다.
      let viaScript = false;
      for (const name of matchAll(cmd, /\bpnpm(?:\s+run)?\s+([A-Za-z0-9:_-]+)/g)) {
        if (!scriptInvokes.has(name)) {
          scriptInvokes.set(name, false); // 순환 방지 — 재귀 중에는 「아직 모름」
          const body = scripts[name];
          scriptInvokes.set(name, body ? walk(body) : false);
        }
        if (scriptInvokes.get(name)) viaScript = true;
      }

      const direct = /\bplaywright\s+test\b/.test(cmd);
      if (!direct && !viaScript) continue; // ★playwright 를 안 부르는 명령의 `--project=` 는 실행이 아니다
      invokesPlaywright = true;

      const named = matchAll(cmd, /--project(?:=|\s+)([A-Za-z0-9_.:-]+)/g).filter(Boolean);
      // ★`--project=${{ matrix.project }}` — 값을 모른다. 「맨 호출 = 전 project」로 떨어지면
      //   matrix 배선 한 줄이 전 project 를 CI 실행으로 등록한다(fail-open). 모르면 안 센다.
      const templated = /--project(?:=|\s+)["']?\$\{\{/.test(cmd);
      if (named.length > 0) for (const n of named) out.add(n);
      else if (direct && !templated) for (const n of allProjects) out.add(n); // 맨 호출 = 전 project
    }
    return invokesPlaywright;
  };

  for (const runBody of runScripts(stripDeadBranches(stripYamlComments(workflowText))))
    walk(runBody);
  return out;
}

/** `dependencies` 를 따라 전이 폐포 — CI 가 부른 project 의 dependency 도 CI 에서 돈다. */
function withDependencies(seed: Set<string>): Set<string> {
  const deps = new Map(
    (config.projects ?? []).map((p) => [p.name ?? "", (p.dependencies ?? []) as string[]]),
  );
  const out = new Set(seed);
  const queue = [...seed];
  while (queue.length > 0) {
    for (const d of deps.get(queue.shift() as string) ?? []) {
      if (!out.has(d)) {
        out.add(d);
        queue.push(d);
      }
    }
  }
  return out;
}

/**
 * `e2e/` **재귀** spec 목록 (codex P2).
 *
 * ★playwright 는 `testDir` 아래를 재귀 수집한다. 직속 파일만 훑으면 앞으로 생길
 * `e2e/foo/new.spec.ts` 가 고아여도 이 감사가 초록이다 — 감사가 막으려던 바로 그 구멍이
 * 감사 자신에게 생긴다.
 */
function specFiles(dir = E2E_DIR, prefix = "e2e"): string[] {
  const out: string[] = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const rel = `${prefix}/${entry.name}`;
    if (entry.isDirectory()) {
      if (entry.name === "node_modules" || entry.name === ".auth") continue;
      out.push(...specFiles(path.join(dir, entry.name), rel));
    } else if (entry.name.endsWith(".spec.ts")) {
      out.push(rel);
    }
  }
  return out.sort();
}

/**
 * playwright 가 그 파일을 이 project 에 넣는가 — testMatch/testIgnore 를 실제 값으로 평가.
 *
 * ★**모델링할 수 없는 형태는 통과시키지 않고 던진다** (codex P2). playwright 는 string 패턴을
 * glob 으로, 경로를 절대경로로 다룬다. 여기서 그걸 `endsWith` 로 흉내 내면 감사는 초록인데
 * 실제 배선은 다른 상태가 만들어질 수 있다. 현재 배선은 전부 RegExp 라 정확하고, 누군가
 * string/glob 을 도입하는 순간 **조용히 부정확해지는 대신 빨개진다.**
 */
function matches(pattern: unknown, relPath: string): boolean {
  if (pattern instanceof RegExp) return pattern.test(relPath);
  if (Array.isArray(pattern)) return pattern.some((p) => matches(p, relPath));
  if (pattern === undefined || pattern === null) return false;
  throw new Error(
    `이 감사는 RegExp 패턴만 충실히 모델링한다. 받은 것: ${JSON.stringify(pattern)}\n` +
      "playwright 의 glob/절대경로 의미론과 어긋날 수 있으므로 통과시키지 않는다. " +
      "패턴을 RegExp 로 바꾸거나, 이 함수를 playwright 실제 의미론으로 확장해라.",
  );
}

function owningProjects(relPath: string): string[] {
  return (config.projects ?? [])
    .filter((p) => {
      const name = p.name ?? "";
      if (name === "setup") return false; // global.setup.ts 전용 — spec 이 아니다
      if (!matches(p.testMatch, relPath)) return false;
      if (p.testIgnore && matches(p.testIgnore, relPath)) return false;
      return true;
    })
    .map((p) => p.name ?? "(unnamed)");
}

function projectSpecFileNames(projectName: string): string[] {
  return specFiles()
    .filter((relPath) => owningProjects(relPath).includes(projectName))
    .map((relPath) => path.basename(relPath))
    .sort();
}

describe("e2e project 배선", () => {
  it("모든 spec 이 정확히 한 project 에 속한다", () => {
    const files = specFiles();
    expect(files.length).toBeGreaterThan(10); // 음성 대조 — 수집이 죽으면 여기서 잡는다

    const orphans: string[] = [];
    const duplicates: Array<[string, string[]]> = [];

    for (const f of files) {
      const owners = owningProjects(f);
      if (owners.length === 0) orphans.push(f);
      else if (owners.length > 1) duplicates.push([f, owners]);
    }

    expect(
      { orphans, duplicates },
      `고아(어느 project 에도 안 물려 실행조차 안 됨): ${JSON.stringify(orphans)}\n` +
        `중복(두 project 에서 같은 spec 을 돌림): ${JSON.stringify(duplicates)}`,
    ).toEqual({ orphans: [], duplicates: [] });
  });

  it("authed project 는 열거식이 아니라 잔여 전체를 가져간다", () => {
    // ★열거식으로 되돌아가면 새 authed spec 이 다시 조용히 누락된다.
    //   `testMatch` 에 개별 파일명이 나열돼 있으면 빨개진다.
    const authed = (config.projects ?? []).find((p) => p.name === "chromium-authed");
    expect(authed, "chromium-authed project 가 사라졌다").toBeTruthy();

    const src = String(authed?.testMatch);
    expect(
      src.includes("trading-ui") || src.includes("dogfood-flow"),
      `chromium-authed.testMatch 가 파일명을 열거하고 있다: ${src}\n` +
        "잔여 전체를 가져가고 다른 project 몫만 testIgnore 로 빼는 형태여야 한다.",
    ).toBe(false);
  });

  it("authed 전용 도달성 setup 만 chromium-authed 를 막는다", () => {
    const projects = config.projects ?? [];
    const reachability = projects.find((p) => p.name === "setup-authed-reachability");
    const authed = projects.find((p) => p.name === "chromium-authed");
    const publicChromium = projects.find((p) => p.name === "chromium");

    expect(reachability, "authed 도달성 setup project 가 사라졌다").toBeTruthy();
    expect(reachability?.testMatch).toEqual(/authed-reachability\.setup\.ts$/);
    expect(reachability?.dependencies).toEqual(["setup", "setup-identity"]);
    expect(authed?.dependencies).toEqual(["setup-authed-reachability"]);
    expect(publicChromium?.dependencies).toEqual(["setup-identity"]);
  });
});

describe("chromium-authed spec 실행 표면 ([BL-789])", () => {
  // ★★**매니페스트가 SSOT 라는 것 자체를 재는 시험** (2026-08-18 적대 리뷰 P2).
  //   위 시험은 매니페스트 ↔ playwright config 만 대조한다. 그것만으로는
  //   **CI 가 그 매니페스트를 실제로 소비하는지**를 아무도 안 본다 — 워크플로를 spec 하드코딩으로
  //   되돌려도 project 축 감사는 `chromium-authed` 가 돈다는 것만 보고 통과한다.
  //   그러면 매니페스트는 「적어 두기만 하고 아무도 안 읽는 목록」이 되고, 이 회차가 없앤 바로
  //   그 병(적혀 있는 것 ≠ 도는 것)이 한 겹 위에서 재발한다.
  it("authed 를 부르는 CI 명령은 매니페스트에서 spec 을 뽑는다 — 파일명을 워크플로에 박지 않는다", () => {
    const bodies: string[] = [];
    for (const file of readdirSync(WORKFLOW_DIR).filter((f) => /\.ya?ml$/.test(f))) {
      const text = readFileSync(path.join(WORKFLOW_DIR, file), "utf8");
      if (!PR_TRIGGERS.some((t) => new RegExp(`^\\s*${t}:`, "m").test(text))) continue;
      for (const body of runScripts(stripDeadBranches(stripYamlComments(text)))) {
        if (/\bplaywright\s+test\b/.test(body) && /--project(?:=|\s+)chromium-authed\b/.test(body)) {
          bodies.push(body);
        }
      }
    }

    // ★양쪽이 비면 ABORT. 「부르는 곳이 없다」를 「계약을 지켰다」로 읽지 않는다.
    if (bodies.length === 0) {
      throw new Error(
        "ABORT — PR 에서 발화하는 워크플로 중 `--project=chromium-authed` 를 부르는 명령이 0개다. " +
          "잡이 지워졌거나 이 파서가 못 읽고 있다. 둘 다 초록이어선 안 된다.",
      );
    }

    for (const body of bodies) {
      expect(
        body.includes("ci-authed-manifest.json"),
        `authed 를 부르는 CI 명령이 매니페스트를 안 읽는다:\n${body}`,
      ).toBe(true);
      expect(
        /\be2e\/[A-Za-z0-9._-]+\.spec\.ts\b/.test(body),
        `authed CI 명령에 spec 파일명이 직접 박혀 있다 — SSOT 는 ci-authed-manifest.json 하나다:\n${body}`,
      ).toBe(false);
    }
  });

  it("config 가 고른 authed spec 은 CI 또는 사유 있는 localOnly 에 정확히 한 번씩 등재된다", () => {
    const { ci, localOnly } = CI_AUTHED_MANIFEST;
    const localOnlyNames = Object.keys(localOnly);

    if (ci.length === 0 && localOnlyNames.length === 0) {
      throw new Error("ABORT — ci와 localOnly가 모두 비어 authed spec 감사 입력이 없다.");
    }

    const overlap = ci.filter((name) => Object.hasOwn(localOnly, name));
    expect(
      overlap,
      `ci와 localOnly에 동시에 등재된 authed spec: ${JSON.stringify(overlap)}`,
    ).toEqual([]);

    expect(
      Object.entries(localOnly)
        .filter(([, reason]) => !LEDGER_REF.test(reason))
        .map(([name]) => name),
      "localOnly 사유에는 [BL-NNN]/[ADR-NNN] 원장 식별자가 필요하다.",
    ).toEqual([]);

    const manifestNames = [...ci, ...localOnlyNames].sort();
    const authedNames = projectSpecFileNames("chromium-authed");
    const duplicateFileNames = authedNames.filter(
      (name, index) => authedNames.indexOf(name) !== index,
    );
    expect(
      duplicateFileNames,
      "매니페스트는 파일명만 쓰므로 chromium-authed 아래 동명 spec은 허용하지 않는다.",
    ).toEqual([]);

    expect(
      manifestNames.filter((name) => !authedNames.includes(name)),
      "매니페스트에 실제 chromium-authed spec 파일이 아닌 이름이 있다.",
    ).toEqual([]);
    expect(
      authedNames.filter((name) => !manifestNames.includes(name)),
      "chromium-authed 대상 spec이 ci/localOnly 어느 쪽에도 등재되지 않았다.",
    ).toEqual([]);
  });
});

const ALL_PROJECTS = ["chromium", "chromium-authed", "chromium-design-canon"];

describe("CI 실행 표면 ([BL-789])", () => {
  it("주석·스텝 이름 같은 **산문**은 실행으로 세지 않는다", () => {
    // ★양성/음성 대조를 같이 둔다. 이 감사의 판별력은 「산문을 배선으로 읽지 않는다」에
    //   달려 있으므로 그것을 따로 증명한다. 픽스처는 인라인이다 — 실파일 문구에 앵커를
    //   걸면 그 문구가 바뀌는 순간 이 시험이 무엇을 재는지 알 수 없게 된다.
    const scripts = { "e2e:authed": "playwright test --project=chromium-authed" };
    const fixture = [
      "jobs:",
      "  e2e:",
      "    steps:",
      "      # P1 4라우트는 전부 authed 라 로컬 `pnpm e2e:authed` 몫이고 CI 에는 없다.",
      "      - name: TODO 언젠가 --project=chromium-authed 를 되살릴 것",
      "        run: |",
      "          # pnpm exec playwright test --project=chromium-design-canon",
      "          pnpm exec playwright test --project=chromium",
    ].join("\n");

    expect(executedProjects(fixture, scripts, ALL_PROJECTS)).toEqual(new Set(["chromium"]));

    // 음성 대조 ① — 주석을 안 지우면 답이 달라진다(= 주석 제거가 하중을 받고 있다).
    expect(executedProjects(fixture.replace(/^(\s*)#/gm, "$1"), scripts, ALL_PROJECTS)).toEqual(
      new Set(["chromium", "chromium-design-canon"]),
    );

    // 음성 대조 ② — **같은 문자열**을 `run:` 으로 옮기면 잡힌다. 즉 위 결과가
    //   「못 찾아서」가 아니라 「스텝 제목이라서」임을 증명한다(항진명제 차단).
    const asRun = fixture.replace(
      "      - name: TODO 언젠가 --project=chromium-authed 를 되살릴 것",
      "      - run: pnpm exec playwright test --project=chromium-authed",
    );
    expect(executedProjects(asRun, scripts, ALL_PROJECTS)).toEqual(
      new Set(["chromium", "chromium-authed"]),
    );
  });

  it("playwright 를 부르지 않는 명령의 `--project=` 는 실행이 아니다", () => {
    // ★★착취 재현: `run:` 안이라도 `echo` 한 줄이면 종전 감사는 「CI 에서 돈다」로 셌다.
    //   playwright 는 0회 돈다 — 「그렇게 적혀 있다」를 「그것이 돈다」로 읽은 네 번째 문법.
    expect(
      executedProjects("      - run: echo --project=chromium-authed", {}, ALL_PROJECTS),
    ).toEqual(new Set());

    // 음성 대조 ① — **같은 인자**를 진짜 호출에 붙이면 잡힌다(못 찾은 게 아님을 증명).
    expect(
      executedProjects(
        "      - run: pnpm exec playwright test --project=chromium-authed",
        {},
        ALL_PROJECTS,
      ),
    ).toEqual(new Set(["chromium-authed"]));

    // 음성 대조 ② — `pnpm` 스크립트 경유는 여전히 센다. 새 규칙이 판별력을 죽이지 않았다.
    expect(
      executedProjects(
        "      - run: pnpm e2e:authed",
        { "e2e:authed": "playwright test --project=chromium-authed" },
        ALL_PROJECTS,
      ),
    ).toEqual(new Set(["chromium-authed"]));

    // 음성 대조 ③ — 같은 명령줄에 진짜 호출과 산문이 **공존**하면 진짜 호출만 남는다.
    expect(
      executedProjects(
        "      - run: |\n          echo --project=chromium-authed\n          pnpm exec playwright test --project=chromium",
        {},
        ALL_PROJECTS,
      ),
    ).toEqual(new Set(["chromium"]));
  });

  it("셸 제어흐름은 해석하지 않는다 — `false &&` 로 죽인 호출도 배선으로 센다", () => {
    // ★★**이것은 통과가 목표인 시험이 아니라 「우리가 안 재는 것」의 명세다.**
    //   `false && …` 는 적대적 저자만 쓰는 형태고, 그것을 잡으려던 단락 평가 모델링 자신이
    //   새 fail-open 3건의 출처였다(2026-08-17 CONTROL 판정). 그래서 걷어냈고, 대가로
    //   **의도적으로 죽인 호출이 배선으로 세진다.** 이 단언이 그 대가를 코드에 고정한다 —
    //   나중에 누가 단락 평가를 되살리면 여기가 빨개지고 이 주석을 읽게 된다.
    expect(
      executedProjects(
        "      - run: false && pnpm exec playwright test --project=chromium-authed || true",
        {},
        ALL_PROJECTS,
      ),
    ).toEqual(new Set(["chromium-authed"]));

    // ★정당한 가드도 같은 규칙으로 **돈다**고 센다. `pnpm install && playwright test` 를
    //   죽었다고 세면 실 배선이 거짓 red 였다 — 모델링을 걷어내며 그 위험도 같이 사라졌다.
    expect(
      executedProjects(
        "      - run: pnpm install --frozen-lockfile && pnpm exec playwright test --project=chromium",
        {},
        ALL_PROJECTS,
      ),
    ).toEqual(new Set(["chromium"]));

    // ★실 배선 대조 — `e2e:authed` 스크립트가 `node -e "…" && playwright test` 형태다.
    //   픽스처만 재면 실제 문법에 대해 아무 말도 못 한다.
    const realAuthed = (
      JSON.parse(readFileSync(WEB_PACKAGE_JSON, "utf8")) as { scripts?: Record<string, string> }
    ).scripts?.["e2e:authed"];
    expect(realAuthed, "package.json 에 e2e:authed 가 없다 — 대조가 항진명제가 된다").toBeTruthy();
    expect(
      executedProjects(
        "      - run: pnpm e2e:authed",
        { "e2e:authed": realAuthed ?? "" },
        ALL_PROJECTS,
      ),
    ).toEqual(new Set(["chromium-authed"]));
  });

  it("`if: false` 인 job/step 은 실행으로 세지 않는다", () => {
    const step = [
      "jobs:",
      "  e2e:",
      "    steps:",
      "      - if: false",
      "        run: pnpm exec playwright test --project=chromium-authed",
      "      - run: pnpm exec playwright test --project=chromium",
    ].join("\n");
    expect(executedProjects(step, {}, ALL_PROJECTS)).toEqual(new Set(["chromium"]));

    // `if:` 가 `run:` **뒤에** 와도 같은 스텝이다(YAML 은 키 순서를 안 가린다).
    const trailing = [
      "jobs:",
      "  e2e:",
      "    steps:",
      "      - name: dead",
      "        run: pnpm exec playwright test --project=chromium-authed",
      "        if: false",
      "      - run: pnpm exec playwright test --project=chromium",
    ].join("\n");
    expect(executedProjects(trailing, {}, ALL_PROJECTS)).toEqual(new Set(["chromium"]));

    // ★대시 줄에 `run:` 이 붙고 `if: false` 가 뒤따르는 형태 — 머리줄까지 지워야 한다.
    //   들여쓰기만 보면 `- run:` 이 키 컬럼보다 얕아 **죽은 호출이 살아남았다**(fail-open).
    const headRun = [
      "jobs:",
      "  e2e:",
      "    steps:",
      "      - run: pnpm exec playwright test --project=chromium-authed",
      "        if: false",
      "      - run: pnpm exec playwright test --project=chromium",
    ].join("\n");
    expect(executedProjects(headRun, {}, ALL_PROJECTS)).toEqual(new Set(["chromium"]));

    // ★반대 방향 — `- if: false` 는 그 줄이 항목의 시작이라 **앞 스텝을 건드리면 안 된다**.
    //   들여쓰기만으로 앞으로 넓히면 앞 스텝의 `run:` 이 같은 컬럼이라 같이 죽었다(거짓 red).
    const prevAlive = [
      "jobs:",
      "  e2e:",
      "    steps:",
      "      - name: live",
      "        run: pnpm exec playwright test --project=chromium",
      "      - if: false",
      "        run: pnpm exec playwright test --project=chromium-authed",
    ].join("\n");
    expect(executedProjects(prevAlive, {}, ALL_PROJECTS)).toEqual(new Set(["chromium"]));

    // job 통째로 죽은 경우 — 뒤따르는 살아 있는 job 은 안 건드린다.
    const job = [
      "jobs:",
      "  dead:",
      "    if: false",
      "    steps:",
      "      - run: pnpm exec playwright test --project=chromium-authed",
      "  live:",
      "    steps:",
      "      - run: pnpm exec playwright test --project=chromium",
    ].join("\n");
    expect(executedProjects(job, {}, ALL_PROJECTS)).toEqual(new Set(["chromium"]));

    // ★★착취 재현 — `if: false # 잠시 꺼둔다`. `DEAD_IF` 는 `\s*$` 로 끝나서 줄 끝 주석이
    //   붙는 순간 안 걸렸고, **죽은 스텝이 살아 있는 것**으로 세졌다(fail-open, 적대 리뷰 실측).
    //   줄 끝 주석은 적대적 문법이 아니라 사람이 실제로 쓰는 형태다.
    const commented = step.replace("      - if: false", "      - if: false # 잠시 꺼둔다");
    expect(commented).toContain("# 잠시 꺼둔다"); // 치환이 샜으면 항진명제가 된다
    expect(executedProjects(commented, {}, ALL_PROJECTS)).toEqual(new Set(["chromium"]));

    // ★음성 대조 — `if:` 가 **조건식**이면 죽은 것이 아니다. 실 워크플로가 전부 이 형태라
    //   여기를 죽었다고 세면 `ci.yml` 의 e2e 잡이 통째로 사라져 감사가 상시 red 다.
    expect(
      executedProjects(
        job.replace("    if: false", "    if: needs.changes.outputs.frontend == 'true'"),
        {},
        ALL_PROJECTS,
      ),
    ).toEqual(new Set(["chromium", "chromium-authed"]));
  });

  it("살아 있는 호출의 **줄 끝 주석**은 배선이 아니다", () => {
    // ★★착취 재현: 통줄 주석만 지우던 때는 이 TODO 가 배선으로 읽혀 「CI 에서 authed 가 돈다」였다.
    const live =
      "      - run: pnpm exec playwright test --project=chromium # TODO --project=chromium-authed 되살리기";
    expect(executedProjects(live, {}, ALL_PROJECTS)).toEqual(new Set(["chromium"]));

    // 음성 대조 — `#` 만 떼면 **같은 문자열**이 잡힌다(못 찾은 게 아니라 주석이라서임을 증명).
    expect(executedProjects(live.replace(" # TODO", " TODO"), {}, ALL_PROJECTS)).toEqual(
      new Set(["chromium", "chromium-authed"]),
    );
  });

  it("`--project=${{ … }}` 표현식은 「모른다」로 두고 전 project 실행으로 세지 않는다", () => {
    // ★★★가장 심각했던 fail-open 의 착취 재현 — 값이 이름 정규식에 안 걸려 `named=[]` 가 되고
    //   「맨 호출」 분기로 떨어져 **전 project 가 CI 실행으로** 등록됐다(LOCAL_ONLY 를 비워도 초록).
    const matrix = "      - run: pnpm exec playwright test --project=${{ matrix.project }}";
    expect(executedProjects(matrix, {}, ALL_PROJECTS)).toEqual(new Set());

    // 따옴표로 감싼 형태도 같다.
    expect(
      executedProjects(
        '      - run: pnpm exec playwright test --project="${{ matrix.project }}"',
        {},
        ALL_PROJECTS,
      ),
    ).toEqual(new Set());

    // 음성 대조 ① — 같은 자리에 리터럴 이름이면 잡힌다(파서가 죽어서 빈 게 아님을 증명).
    expect(
      executedProjects(
        matrix.replace("${{ matrix.project }}", "chromium-authed"),
        {},
        ALL_PROJECTS,
      ),
    ).toEqual(new Set(["chromium-authed"]));

    // 음성 대조 ② — 표현식과 리터럴이 공존하면 **읽은 것만** 센다(모르는 쪽은 안 센다).
    expect(
      executedProjects(
        "      - run: pnpm exec playwright test --project=chromium --project=${{ matrix.extra }}",
        {},
        ALL_PROJECTS,
      ),
    ).toEqual(new Set(["chromium"]));
  });

  it("LOCAL_ONLY 사유는 원장 식별자를 품어야 한다", () => {
    // ★★착취 재현: 종전 계약은 `?.trim()` 뿐이라 `"."` 한 글자로 어떤 project 든 면제됐다.
    expect(LEDGER_REF.test(".")).toBe(false);
    expect(LEDGER_REF.test("CI 에 올리기 어려워서 뺐다")).toBe(false); // 산문만으론 부족
    expect(LEDGER_REF.test("[BL-789] 1단계만 착수")).toBe(true);
    expect(LEDGER_REF.test("[ADR-034] 가 CI 인증 secret 을 0개로 만들었다")).toBe(true);

    // 실 등재분이 계약을 만족하는가 — 안 그러면 아래 본체 감사의 ⑶ 이 상시 red 다.
    expect(
      Object.entries(LOCAL_ONLY)
        .filter(([, reason]) => !LEDGER_REF.test(reason))
        .map(([name]) => name),
    ).toEqual([]);
  });

  it("`--project` 없는 `playwright test` 는 전 project 실행으로 센다", () => {
    // ★`package.json` 의 `e2e:all` 이 이 형태다. 모델링하지 않으면 authed 가 CI 에서
    //   실제로 도는데도 감사가 못 본다(fail-open).
    const bare = "      - run: pnpm exec playwright test";
    expect(executedProjects(bare, {}, ALL_PROJECTS)).toEqual(new Set(ALL_PROJECTS));

    // 스크립트 경유도 같다.
    const viaScript = "      - run: pnpm e2e:all";
    expect(executedProjects(viaScript, { "e2e:all": "playwright test" }, ALL_PROJECTS)).toEqual(
      new Set(ALL_PROJECTS),
    );

    // 음성 대조 — `playwright install` 은 실행이 아니다.
    expect(
      executedProjects("      - run: pnpm exec playwright install --with-deps chromium", {}, [
        ...ALL_PROJECTS,
      ]),
    ).toEqual(new Set());
  });

  it("PR 에서 발화하지 않는 워크플로는 CI 실행으로 세지 않는다", () => {
    const nightly = ["on:", "  schedule:", '    - cron: "0 18 * * *"', "  workflow_dispatch:"].join(
      "\n",
    );
    const dispatchOnly = ['"on":', "  # schedule:", '  #   - cron: "0 18 * * *"', "  workflow_dispatch:"].join("\n"); // prettier-ignore
    const pr = ["on:", "  pull_request:", "    branches: [main]"].join("\n");

    expect(isPullRequestGated(nightly)).toBe(false);
    expect(isPullRequestGated(dispatchOnly)).toBe(false); // `"on":` 따옴표 형태
    expect(isPullRequestGated(pr)).toBe(true);
    expect(isPullRequestGated(["on: [push, pull_request]"].join("\n"))).toBe(true); // 인라인 flow
    expect(isPullRequestGated(["on:", "  push:", "    branches: [main]"].join("\n"))).toBe(false);

    // ★실파일 대조 — 픽스처만 재면 실 워크플로 문법에 대해 아무 말도 못 한다.
    expect(
      isPullRequestGated(readFileSync(path.join(WORKFLOW_DIR, "ci.yml"), "utf8")),
      "ci.yml 이 PR 게이트가 아니라고 나왔다 — 파서가 죽었거나 트리거가 바뀌었다.",
    ).toBe(true);
  });

  it("모든 project 는 PR CI 에서 실제로 돌거나 LOCAL_ONLY 에 사유와 함께 등재돼 있다", () => {
    const projectNames = (config.projects ?? []).map((p) => p.name ?? "").filter(Boolean);
    const workflows = readdirSync(WORKFLOW_DIR).filter(
      (f) => f.endsWith(".yml") || f.endsWith(".yaml"),
    );
    const scripts = (
      JSON.parse(readFileSync(WEB_PACKAGE_JSON, "utf8")) as { scripts?: Record<string, string> }
    ).scripts;

    // ★양쪽이 비면 ABORT. 0건을 「일치」로 읽으면 판별력이 0 이다(이 레포 상습 사고).
    if (projectNames.length === 0) throw new Error("ABORT — playwright project 를 0개 읽었다.");
    if (workflows.length === 0) throw new Error(`ABORT — ${WORKFLOW_DIR} 에 워크플로가 0개다.`);
    if (!scripts) throw new Error(`ABORT — ${WEB_PACKAGE_JSON} 에 scripts 가 없다.`);

    const anyWorkflow = new Set<string>(); // 트리거 무관 — 오타 검출용
    const direct = new Set<string>(); // PR 게이트 워크플로만 — 「CI 초록」의 근거
    const prGated: string[] = [];
    for (const f of workflows) {
      const text = readFileSync(path.join(WORKFLOW_DIR, f), "utf8");
      const names = executedProjects(text, scripts, projectNames);
      for (const n of names) anyWorkflow.add(n);
      if (!isPullRequestGated(text)) continue;
      prGated.push(f);
      for (const n of names) direct.add(n);
    }
    if (prGated.length === 0)
      throw new Error("ABORT — PR 에서 발화하는 워크플로를 0개 골랐다. 트리거 파서가 죽었다.");
    if (direct.size === 0)
      throw new Error(
        "ABORT — PR 워크플로에서 실행되는 playwright project 를 0개 추출했다. 파서가 죽었다.",
      );

    const inCI = withDependencies(direct);

    // ⑴ 워크플로가 부르는 이름이 config 에 실재하는가 (오타 = 조용한 0건 실행).
    //   ★여기만 트리거를 안 본다 — nightly 의 오타도 「돈다고 적혀 있는데 0건」이다.
    expect(
      [...anyWorkflow].filter((n) => !projectNames.includes(n)),
      `워크플로가 존재하지 않는 project 를 부른다 — playwright 는 그것을 0건으로 돌고 초록이다.`,
    ).toEqual([]);

    // ⑵ LOCAL_ONLY 가 낡지 않았는가 (사라진 project 의 면제가 남아 있으면 다음 신설을 가린다).
    expect(
      Object.keys(LOCAL_ONLY).filter((n) => !projectNames.includes(n)),
      "LOCAL_ONLY 에 config 에 없는 project 가 남아 있다. 지워라.",
    ).toEqual([]);

    // ⑶ 면제 사유가 계약을 만족하는가 — 원장 식별자 없는 사유는 면제가 아니다.
    //   ★종전 검사는 `?.trim()` 뿐이라 `"."` 한 글자로 전건 초록이었다(2026-08-17 적대 리뷰).
    expect(
      Object.entries(LOCAL_ONLY)
        .filter(([, reason]) => !LEDGER_REF.test(reason ?? ""))
        .map(([name]) => name),
      "LOCAL_ONLY 사유에 [BL-NNN]/[ADR-NNN] 원장 식별자가 없다.\n" +
        "「왜 CI 에 안 올렸나」는 원장이 답한다 — 번호를 적어야 그 BL 이 닫힐 때 면제도 같이 걷힌다.",
    ).toEqual([]);

    // ⑷ 본체 — PR CI 에서 실행되지도, 면제되지도 않은 project 는 아무 데서도 안 도는 것이다.
    expect(
      projectNames.filter((n) => !inCI.has(n) && !LEDGER_REF.test(LOCAL_ONLY[n] ?? "")),
      "이 project 는 PR 에서 발화하는 워크플로 어디에서도 실행되지 않는다.\n" +
        "워크플로에 --project= 로 배선하거나, LOCAL_ONLY 에 **사유와 함께** 등재해라.\n" +
        `PR 게이트 워크플로: ${JSON.stringify(prGated.sort())}\n` +
        `그것들이 실제로 부르는 것: ${JSON.stringify([...direct].sort())}`,
    ).toEqual([]);

    // ⑸ 면제와 실행이 겹치면 LOCAL_ONLY 사유가 거짓이다.
    //   ★`direct` 가 아니라 `inCI` 로 잰다 — 전이 dependency 로만 CI 에 편입된 project 는
    //     ⑷ 가 `inCI` 로 통과시키므로, 이 단언이 `direct` 만 보면 「로컬 전용」이라는 **거짓 사유**가
    //     그대로 늙는다(2026-08-17 적대 리뷰). 두 단언의 기준을 같은 집합으로 맞춘다.
    expect(
      Object.keys(LOCAL_ONLY).filter((n) => inCI.has(n)),
      "LOCAL_ONLY 인데 PR CI 에서 실제로 돈다(직접 호출 또는 dependency 경유) — 사유가 거짓이 됐으니 목록에서 빼라.",
    ).toEqual([]);
  });
});
