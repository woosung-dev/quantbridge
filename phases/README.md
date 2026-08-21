# phases/ — 하네스 러너의 회차 정의

각 디렉터리 = phase 1개 = **브랜치 1개 = PR 1개**. 안의 step 은 **순차**로 돈다
(`step0` → `step1` → …, 앞 step 의 `summary` 가 다음 step 프롬프트에 누적된다).

★**`index.json` 은 순서가 아니라 목록이다.** 항목 사이에 의존이 없으면 서로 다른 워크트리에서
**동시에** 돌 수 있다. 러너(`tools/harness/execute.py`)는 인자로 받은 phase **하나만** 처리하므로,
병렬은 러너 안이 아니라 **밖 — 프로세스를 N벌 띄우는 것 — 에서 만들어진다.**
(출처 레포 jha0313/finsight 에서는 `0-foundation` → `1-core-loop` → … 처럼 **순번**이었다.
우리는 같은 파일을 병렬 묶음에도 쓴다. 어느 쪽인지는 아래 절이 말한다.)

## 앞선 병렬 묶음 — `fe3-*` 8벌 **완주** (2026-08-21 · PR #735~#743)

`apps/web` 의 **화면 계층**에 테스트가 0건이던 축이다. 소유 티켓 = **[BL-815]**(✅ Resolved).
가장 값이 컸던 것은 **`error.tsx` 7개** — `apps/web/AGENTS.md` §3/§6 이 **의무로 강제**하는데
9개 중 2개만 테스트가 있었다. **8/8 completed · 병합 충돌 0 · 변이 8/8 red** ·
`apps/web` **237 files / 1,647 → 247 files / 1,780 passed**(신규 10파일 **+133 케이스**) ·
전이 폐포 미도달 **53 → 32**. **대상 소스 전건 무변경.**
★열려 있는 묶음은 지금 **없다** — 다음 재료는 `docs/status.md` 의 살아 있는 「다음 행동」이 든다.

| phase                    | 대상                                                    | 새 테스트 파일 (`apps/web/`)                                 |
| ------------------------ | ------------------------------------------------------- | ------------------------------------------------------------ |
| `fe3-public-legal-pages` | `app/{disclaimer,terms,privacy,not-available}/page.tsx` | `src/app/__tests__/public-legal-pages.test.tsx`              |
| `fe3-dashboard-errors`   | `error.tsx` **7개**(dashboard 6 + invite 1)             | `src/app/(dashboard)/__tests__/error-boundaries.test.tsx`    |
| `fe3-query-provider`     | `components/providers/{query,app}-provider(s).tsx`      | `src/components/providers/__tests__/query-provider.test.tsx` |
| `fe3-onboarding-schema`  | `features/onboarding/schemas.ts` (persist 검증)         | `src/features/onboarding/__tests__/schemas.test.ts`          |
| `fe3-legal-geo-banner`   | `components/{legal-notice,geo-block}-banner.tsx`        | `src/components/__tests__/legal-geo-banner.test.tsx`         |
| `fe3-numeric-display`    | `components/tape/pnl-tape.tsx` + `tick-ruler.tsx`       | 각 `__tests__` 2파일                                         |
| `fe3-optimizer-view`     | `features/optimizer/components/optimizer-page-view.tsx` | `.../__tests__/optimizer-page-view.test.tsx`                 |
| `fe3-waitlist-admin`     | `waitlist-header.tsx` + `admin/waitlist-admin-view.tsx` | 각 `__tests__` 2파일                                         |

★★**경로에 `(dashboard)`·`[token]` 괄호가 들어가는 첫 묶음이다.** vitest CLI 필터는 그 경로를
**정상 처리한다**(실측 4건) — 깨지는 것은 **셸 따옴표**다. AC 의 경로는 **작은따옴표**로 감싼다.
★**큰따옴표 이스케이프(`\"`)를 쓰지 마라** — 러너가 AC 를 `bash -c` 로 돌리는데 거기서
`syntax error near unexpected token '('` 로 죽는다(2026-08-21 CONTROL 이 착수 전에 밟았다).

★**AC red 측정이 lane 하나를 폐기시켰다** — 초판 `fe3-root-error` 는 `src/app/error.tsx` 를
겨눴는데 그 파일에는 **이미 테스트가 있었다**. 판별력 0(rc=0)으로 드러나 교체했다 —
[LESSON-123] 이 말한 「프로브의 값은 안 된다를 미리 만나는 데 있다」의 두 번째 사례다.

## 앞선 병렬 묶음 — `fe2-*` 8벌 **완주** (2026-08-21 · PR #724~#732)

`apps/web` 의 **순수 판정 모듈**에 테스트가 0건이던 축이다. 소유 티켓 = **[BL-813]**(✅ Resolved).
1차(`ops2-*`)에서 가장 깨끗하게 끝난 셋이 `tools/scripts/lib/*.sh`(source 전용 순수 함수)였고,
FE 의 `src/lib/**` 이 같은 모양이었다. **여덟은 동시에 돌도록 설계됐고 그대로 돌았다** —
8/8 completed · blocked 0 · **병합 충돌 0** · 변이 8/8 red ·
`apps/web` vitest **227 files / 1,497 passed → 237 files / 1,647 passed**(신규 10파일 **+150 케이스**).
**대상 소스 전건 무변경.** ★열려 있는 묶음은 지금 **없다** — 다음 재료는 `docs/status.md` 의
살아 있는 「다음 행동」(B축 = FE 컴포넌트 클러스터)이 든다.

| phase                 | 대상                                                 | 새 테스트 파일 (`apps/web/`)                                                           | 짊어진 이슈 (근거)         |
| --------------------- | ---------------------------------------------------- | -------------------------------------------------------------------------------------- | -------------------------- |
| `fe2-proxy-gate`      | `src/proxy.ts` 공개/geo/세션 판정                    | `src/__tests__/proxy-gate.test.ts`                                                     | [ADR-034] · [BL-072]       |
| `fe2-route-matcher`   | `src/lib/route-matcher.ts` 앵커 계약                 | `src/lib/__tests__/route-matcher.test.ts`                                              | [ADR-034]                  |
| `fe2-auth-hooks`      | `src/lib/auth.ts` geo L3 · 탈퇴 fail-closed          | `src/lib/__tests__/auth-hooks.test.ts`                                                 | [LESSON-114] · codex P1/P2 |
| `fe2-auth-server`     | `src/lib/auth-server.ts` 실패 삼킴                   | `src/lib/__tests__/auth-server.test.ts`                                                | [ADR-034]                  |
| `fe2-builtin-hints`   | `src/lib/unsupported-builtin-hints.ts` (55 엔트리)   | `src/lib/__tests__/unsupported-builtin-hints.test.ts`                                  | Trust Layer (Sprint 21)    |
| `fe2-marketing-canon` | `src/lib/marketing-canon.ts` + `legal-links.ts`      | `src/lib/__tests__/marketing-canon.test.ts`                                            | [BL-776] · LESSON-063      |
| `fe2-lib-adapters`    | `src/lib/webhook-base.ts` + `zod-v4-resolver.ts`     | `src/lib/__tests__/{webhook-base,zod-v4-resolver}.test.ts`                             | [BL-268]                   |
| `fe2-ui-reactive`     | `src/store/ui-store.ts` + `hooks/use-media-query.ts` | `src/store/__tests__/ui-store.test.ts` · `src/hooks/__tests__/use-media-query.test.ts` | [BL-300] · [BL-775]        |

동시에 돌 수 있는 근거는 **파일 겹침 0** 이다 — 각 lane 은 자기 테스트 파일만 만들고 대상 소스 ·
`vitest.config.ts` · `tests/setup.ts` 를 건드리지 않는다(각 step 의 금지사항에 박혀 있다).
공용 헬퍼 모듈도 금지다 — 그것이 lane 사이의 유일한 공유 파일이 되기 때문이다.

★★**FE 에는 셸 lane 에 없던 전제가 하나 있다 — `server-only`.**
`src/lib/auth-server.ts` 의 `import "server-only"` 는 **vitest 에서 top-level throw** 다
(패키지 exports 맵이 `react-server` 조건에서만 빈 모듈을 준다). ★**`vi.mock("server-only")` 로는
못 막는다** — CJS 로 외부화돼 Node 의 require 가 먼저 돈다(2026-08-21 실측 FAIL).
그래서 **사전 배치 커밋**이 `apps/web/vitest.config.ts` 의 `resolve.alias` 로
`apps/web/tests/stubs/server-only.ts`(빈 모듈)에 매핑했다. lane 은 그 파일들을 건드리지 않는다.

★**AC 4종(FE 판)** — ⑴ `pnpm test -- --run <파일>`(부재 시 **rc=1**) ⑵
`test "$(pnpm exec vitest list <파일> | grep -c ' > ')" -ge N`(**파일별** 양성 대조 · 부재 시 rc=1)
⑶ `pnpm exec eslint <파일>`(부재 시 rc=2) ⑷ `pnpm exec tsc --noEmit`.
★모든 AC 가 `cd apps/web &&` 로 시작한다 — 러너는 AC 를 **워크트리 루트**에서 `bash -c` 로 돈다.

★**착수 전 AC red 를 잴 때 각 AC 를 서브셸에 넣어라** — `cd apps/web` 이 잔류하면 뒤 lane 의 조회가
전부 깨지고 **빈 문자열이 rc=0 으로 통과**한다(2026-08-21 CONTROL 이 첫 판에서 밟았다).

### 앞선 병렬 묶음 — `ops2-*` 8벌 **완주** (2026-08-21 · PR #712~#720)

[ADR-037] §① 이 「검사기 복귀 시 함께 복귀」라 적어 둔 자기시험 `*-test.sh` **14종** 중
**대상 스크립트가 아직 살아 있는 7종**의 잔여(4벌) + **짝 하네스가 애초에 없던 인접 4종**이다.
소유 티켓 = **[BL-812]**(✅ Resolved). **여덟은 동시에 돌도록 설계됐고 그대로 돌았다** — 8/8 completed · retry 0 · blocked 0 · **병합 충돌 0** · 변이 10/10 red · `apps/api/tests/scripts/` **0건 → 138 passed + 2 xfailed**.
★이 묶음은 닫혔다. **열려 있는 묶음 = `fe2-*` 8벌**(아래).

| phase                   | 대상                                    | 새 테스트 파일 (`apps/api/tests/scripts/`) | 짊어진 이슈                     |
| ----------------------- | --------------------------------------- | ------------------------------------------ | ------------------------------- |
| `ops2-prepush-guard`    | `lib/pre-push-ref-guard.sh` 판정 순서   | `test_pre_push_ref_guard.py`               | Golden Rule · [BL-554]·[BL-555] |
| `ops2-notify-telegram`  | `lib/notify-telegram.sh` seam·토큰 침묵 | `test_notify_telegram_lib.py`              | [BL-768]                        |
| `ops2-mise-shim`        | `lib/mise-shim-path.sh` PATH 계산       | `test_mise_shim_path.py`                   | [BL-785] · [BL-791] gap 고정    |
| `ops2-soak-watch`       | `soak-watch.sh` 지문·신선도             | `test_soak_watch.py`                       | [BL-737]                        |
| `ops2-soak-restart`     | `soak-restart.sh` `ps` rc 3값           | `test_soak_restart.py`                     | [BL-656]                        |
| `ops2-stack-migrate`    | `soak-stack.sh` `_migrate` 대상 증명    | `test_soak_stack_migrate.py`               | [BL-743]                        |
| `ops2-db-backup-retain` | `db-backup.sh` `--status`·`_retain`     | `test_db_backup_retain.py`                 | [BL-767]                        |
| `ops2-logs-follow`      | `soak-logs-follow.sh` 회전·커서         | `test_soak_logs_follow.py`                 | [BL-619]                        |

동시에 돌 수 있는 근거는 **파일 겹침 0** 이다 — 각 lane 은 자기 테스트 파일 하나만 만들고
대상 스크립트·`conftest.py`·`shards.json` 을 건드리지 않는다(각 step 의 금지사항에 박혀 있다).
공용 헬퍼 모듈도 금지다 — 그것이 lane 사이의 유일한 공유 파일이 되기 때문이다.

★**대상을 tmp 로 돌리는 방식이 lane 마다 다르다.** 진짜 파일을 그대로 부르는 넷
(`lib/` 3종은 **source 전용**이라 `bash -c '. lib; fn'` · `db-backup` 은 env)과, 경로가
`SCRIPT_DIR`/`ROOT` 파생이라 못 바꾸는 넷(`soak-watch`·`soak-restart`·`soak-stack`·
`soak-logs-follow`)은 **`tmp_path` 아래 가짜 레포에 복사해서** 돈다. 진짜 경로를 겨누면
이 레포의 소크 앵커·커서·백업 디렉터리를 덮어쓴다.

★**외부 명령만 PATH 스텁**(`docker`·`oci`·`uv`·`timeout`) — `awk`/`sed`/`grep` 은 대상이
쓰는 것이라 스텁하면 대상을 안 재게 된다.

### 앞선 묶음 (완주)

`ops-*` 6벌 (2026-08-20 · PR #703~#709) — 운영 스크립트 6종의 판정 로직 **0건 → 72 passed +
1 xfailed**. `runner-*` 4벌 (2026-08-20 · PR #698~#702) — 러너 자신(`tools/harness/execute.py`)의
테스트 0건을 `apps/api/tests/harness/test_execute_{ac,retry,commit,boot}.py` **41건**으로 채웠다.

## 밤샘 루프 — 배치를 이어 돌릴 때 (2026-08-20 설계)

러너는 phase 하나만 처리한다. 여러 배치를 밤새 이어 돌리는 것은 **러너 밖 셸 루프**다.
★**착수 규약 3줄** (1차에서 사용자 지적으로 확정):

- ★**소유 BL 을 먼저 신설해 3면 등재해라**(`backlog.md` 섹션 + 인덱스 표 + `roadmap.md` 체크박스).
  BL 없이 돌면 「어느 이슈를 한 회차인가」에 좌표가 없다 — 2026-08-20 4회차가 그랬고
  [BL-812] 가 그 자리를 뒤늦게 메웠다. lane 마다 **짊어진 이슈**를 표로 적어라
  (닫히는 BL 과 근거·맥락으로 인용하는 BL 을 **갈라 적어라** — 후자를 「다시 닫았다」고 쓰지 마라)
- **step 파일 템플릿의 최근 선례 = `phases/ops2-prepush-guard/step0.md`**(2026-08-21 8/8 완주).
  형식 정본은 `.claude/commands/harness.md`
- **마감에 화면을 회수해라** — `herdr pane close <ID>` 로 보드·로그 pane 을 닫는다.
  회차가 끝난 뒤에도 떠 있는 보드는 **다음 세션이 현행으로 오독한다**(소크 상비 참조가
  「낡은 T0 를 남기지 마라」로 적어 둔 것과 같은 병이다)

★**저작이 상한이다** — 밤에 도는 분량은 저녁에 저작해 둔 분량뿐이고, 그래서 재료는
**동형(同型)**이어야 한다(같은 대상 종류 × 같은 종류의 일). 이질적인 티켓 N건은 저작이 안 된다.

배치 루프가 하는 일 — 2026-08-20 6 lane 회차에서 **손으로 한 순서 그대로**다:

1. `phases/index.json` 의 `pending` 에서 cap N 개를 꺼낸다 (**웨이브를 저작하지 마라** —
   배치는 동시 실행 상한 + 체크포인트일 뿐이다)
2. lane 마다 워크트리 생성 + `worktree-bootstrap.sh --adopt-env --skip-deps` + `apps/api` `uv sync`
3. ★**착수 전 AC red 확인** — rc=0 인 lane 은 **판별력이 0** 이므로 큐에서 빼고 기록한다
4. 러너 N벌 `nohup` 병렬 → `wait` (대화 세션 타임아웃이 러너를 죽인다)
5. ★**변이 red 확인** — red 가 아니면 PR 을 올리지 말고 `unverified` 로 기록한다
   (2026-08-20 에 이 축이 「옳은 단언 + 잘못된 픽스처」 1건을 잡았다)
6. `--push` + `gh pr create` → **CI 가 밤새 대신 돈다.** 아침에 결과가 이미 있다
7. ★`git worktree remove` 로 **슬롯을 회수**한다 — 슬롯은 1..12 뿐이라 회수 없이는 3배치째에 막힌다
8. 시간 상한이 남았으면 1로

★**1차 실주행(2026-08-21 · 8 lane)이 더한 것 5줄** — 다음 회차는 이것부터 읽어라:

1. ★★**`xfail(strict=True)` 는 코드 변경과 같은 등급의 주장이다.** 「이 제품 코드가 지금 틀렸다」를
   원장에 박고 누가 고치면 XPASS 로 red 를 낸다. **AC·변이·사람 diff 세 층이 전부 통과시킨다** —
   `xfail` 은 rc 를 0으로 유지하고, 변이는 대개 다른 축을 겨누며, 대상 무변경이면 diff 가
   「테스트만 늘었다」로 보인다. ⇒ **세션이 남긴 xfail 은 전건 코드 대조**해라([LESSON-121]).
   1차에서 3건 중 1건이 phantom 이었다(픽스처가 `alembic history` 화살표 의미를 뒤집었다).
2. ★**픽스처가 외부 도구 출력을 모사하면 그 형식을 실측해 주석에 좌표와 함께 박아라.**
   판별 방법은 문서가 아니라 **그 도구를 한 번 돌려 보는 것**이다.
3. ★**CONTROL 의 검증 스크립트는 `bash -c` 로 돌려라** — zsh 는 unquoted 확장을 단어분할하지
   않아 `for x in ${v//|/ }` 이 한 덩어리로 돌고 **실재하는 것을 「부재」로** 보고한다(1차에서 밟았다).
4. ★★**`mergeStateStatus: CLEAN` 은 「CI 가 통과했다」가 아니다.** 이 레포에는 required status
   check 가 없어 **체크가 도는 중에도 CLEAN 이고 머지가 된다.** 1차 마감에서 실제로 밟았다 —
   폴링 루프의 **재시도 예산이 조용히 소진**되자 그 뒤 `CLEAN` 만 보고 머지했고, 그 시점
   backend 는 `in_progress` 였다(결과는 사후에 success 였지만 **그것은 운이다**).
   ⇒ 머지 조건은 **`gh run view <id> --json conclusion` = `success`** 로 재라.
   ★그리고 **「예산 소진」과 「초록」을 같은 분기에 두지 마라** — 소진이면 **머지하지 말고 보고**해라
   (「볼 창이 없으면 통과」와 같은 fail-open 이다).
   ★`gh pr checks` 의 **`no checks reported` 도 초록이 아니다** — push 직후엔 체크가 아직 안 생겨서
   「pending 0건」으로 읽힌다. **체크가 생겼는지(행 수 ≥ 2)를 먼저 확인**해라.
   ★`gh pr merge` **직후** 나머지 PR 의 `mergeStateStatus` 는 `UNKNOWN` 이 된다(GitHub 재계산).
   `UNKNOWN` 이면 건너뛰지 말고 CLEAN 이 될 때까지 폴링해라 — 1차에서 7건을 한 번 건너뛰었다.
5. ★**FE lane 은 `--skip-deps` 만으로 안 돈다** — `apps/web` 에서 `pnpm install --frozen-lockfile`
   이 필요하다(실측 **6초**, pnpm store 하드링크). BE lane 은 `apps/api` `uv sync` 그대로.

★**2차 실주행(2026-08-21 · FE 8 lane)이 더한 것 5줄:**

1. ★★★**착수 전 프로브의 값은 「된다」가 아니라 「안 된다」를 새벽 전에 만나는 데 있다.**
   `src/lib/auth-server.ts` 는 `import "server-only"` 가 **vitest 에서 top-level throw** 라 import
   조차 불가능했고, ★**`vi.mock("server-only", () => ({}))` 로도 안 막힌다** — CJS 로 외부화돼
   **Node 의 require 가 먼저 실행**하므로 vitest 의 mock 레지스트리를 지나간다. 저작 전에 재지
   않았으면 그 lane 은 통째로 죽었다. **대상이 프레임워크 경계(server-only · next/\*\* · DB 풀)를
   물면 lane 을 쓰기 전에 import 한 줄을 실제로 돌려 봐라.**
2. ★★**step 파일에 「이렇게 나올 것이다」를 쓰면 그것이 사실상 AC 가 된다.** `fe2-builtin-hints`
   step0 이 프로토타입 키에 「fallback 이 나온다」고 적었는데 **거짓**이었고(객체 리터럴이
   `Object.prototype` 을 상속해 `{name}` 만 나온다), 세션은 시킨 대로 단언해 AC 3회 red 로 `error`.
   **테스트가 아니라 내 기대가 틀린 것이다.** 복구는 §4 그대로 — 검시 → **실측표를 step 에 박고**
   → `pending` 복귀 → 재실행. 드러난 결함은 [BL-814] 로 올렸다.
   ⇒ **재지 않은 기대는 step 에 쓰지 말고 「관측한 것을 박아라」로만 지시해라.**
3. ★★**macOS bash 3.2 에는 연관 배열이 없다.** `declare -A` 가 실패하면 `T[key]=v` 는 **산술 첨자
   0** 으로 해석돼 **전부 index 0 을 덮어쓴다.** 2차에서 PR 7건이 **같은 제목·본문**으로 올라갔다.
   ⇒ lane 별 텍스트는 **배열이 아니라 파일**(`$SP/<lane>.title`·`.body`)로 갈라라.
4. ★**CONTROL 검증 루프의 각 단계를 서브셸에 넣어라.** AC 는 `cd apps/web && …` 로 시작하는데
   그것을 루프 안에서 `eval` 하면 **cwd 가 잔류**해 뒤 lane 의 조회가 전부 깨지고 **빈 문자열이
   rc=0 으로 통과**한다(2차 첫 판이 7 lane 을 그렇게 「초록」으로 읽었다). `( cd "$ROOT" && eval … )`.
5. ★**변이가 초록이면 테스트를 의심하기 전에 변이가 런타임에 닿았는지부터 재라.**
   2차에서 `_HINTS[name] as undefined` 를 심었는데 **타입 소거**라 아무 일도 안 일어났다.
   대상이 TS 면 **타입 수준 변이는 변이가 아니다** — 값·분기를 바꿔라(레포 3번째 실증).

★**3차 실주행(2026-08-21 · FE 화면 8 lane)이 더한 것 4줄:**

1. ★★★**「AC red 측정」은 판별력 검사가 아니라 재료 실사이기도 하다.** 3차 초판 lane 1 이
   `src/app/error.tsx` 를 겨눴는데 **rc=0** 이 나왔다 — 그 파일에는 **이미 테스트가 있었다**(4 케이스).
   ⇒ **저작 전에 「이 대상이 정말 미커버인가」를 AC 로 한 번 재라.** 전이 폐포 도구가
   `app/error.tsx` 를 「도달」로 이미 표시하고 있었는데 내가 목록을 눈으로 읽다 놓쳤다.
2. ★★**세션이 `blocked` 를 쓰면 그것은 대개 내 step 이 틀렸다는 신호다.**
   `fe3-public-legal-pages` 가 「법무 4페이지 전부 `metadata` 를 갖는다」를 만족시키려면 대상을
   고쳐야 하는데 그것이 금지라 멈췄다. **틀린 것은 세션이 아니라 내 기대**였고
   `/not-available` 에 진짜로 `metadata` 가 없었다(→ [BL-816]). ⇒ `blocked` 를 「자격증명 문제」로만
   읽지 마라 — **step 의 사실 주장을 먼저 코드로 대조해라**([LESSON-122]).
3. ★★**경로에 `(` · `[` 가 들어가면 AC 는 작은따옴표로 감싸라.** Next.js 라우트 그룹
   (`(dashboard)`)과 동적 세그먼트(`[token]`)가 그렇다. **`\"` 로 감싸면 러너의 `bash -c` 에서
   `syntax error near unexpected token '('` 로 죽는다** — 파일이 생겨도 실패할 AC 다.
   ★**vitest CLI 필터 자체는 괄호 경로를 정상 처리한다**(실측 4건) — 처음엔 vitest 글롭 문제로
   오진했다가 **대조군**(괄호 없는 경로)으로 갈랐다.
4. ★★**CONTROL 의 검사기는 셸이 아니라 python 으로 써라.** 2·3차에서 내 셸 검사기가 **여섯 번**
   무증거·오작동을 냈다 — `cd` 잔류로 빈 AC 가 rc=0 · zsh 단어분할 · **bash 3.2 에 연관 배열 부재**
   (PR 7건이 같은 본문) · **같은 이유로 `mapfile` 부재**(검사기가 「테스트 0파일 clean」을 출력) ·
   AC 생성기의 `\"` · 타입 수준 변이. **macOS 의 bash 는 3.2 다 — 4.x 문법은 없다.**

★**자동 머지는 하지 않는다.** 「마지막 강력 검증」(사람 diff + 머지)은 아침의 몫이다.
★`blocked` 는 즉시 알린다(자격증명 등 사람만 풀 수 있는 것) — 나머지는 아침에 몰아 본다.
★**화면은 pane 2개면 된다** — 상태 보드 + `dispatch.log`. lane 당 `tail -f` 6벌은 새벽에 못 읽는다.
`herdr pane split --current --direction right --ratio 0.3` · `herdr pane run <ID> <cmd>` ·
`herdr notification show <제목> --sound done`. ★워크트리는 `herdr worktree create` 가 아니라
`worktree-bootstrap.sh` 로 만든다 — herdr 은 슬롯·env·테스트DB 를 모르고, 워크트리마다 탭이
생겨 [ADR-030] 이 걷어낸 함대 모델로 돌아간다.

## 이 저장소의 바인딩

`/harness` 커맨드는 프로젝트에 무관하게 쓰이도록 되어 있다. 이 저장소에서 그 자리에 들어가는 값은 아래다.

| 축             | 값                                                                                                                |
| -------------- | ----------------------------------------------------------------------------------------------------------------- |
| 러너           | `tools/harness/execute.py`                                                                                        |
| BE 테스트 AC   | `cd apps/api && uv run --env-file .env.local pytest <대상> -q`                                                    |
| BE 린터 AC     | `cd apps/api && uv run ruff check <대상>`                                                                         |
| FE AC          | `cd apps/web && pnpm test -- --run <대상>` · `pnpm tsc --noEmit` · `pnpm build`                                   |
| 브랜치 규약    | `feat/harness-<phase>` — `feat/` 접두는 push 가드 화이트리스트라 협상 불가                                        |
| 규칙 주입 파일 | `CONTEXT.md` · `AGENTS.md` · `apps/api/AGENTS.md` · `apps/web/AGENTS.md` (하나라도 없으면 러너가 시작을 거부한다) |
| 워크트리 준비  | `git worktree add <경로> -b feat/harness-<phase>` → 그 안에서 `tools/scripts/worktree-bootstrap.sh --adopt-env`   |
| 타임아웃       | `QB_HARNESS_CODEX_TIMEOUT` · `QB_HARNESS_AC_TIMEOUT`                                                              |

**AC 에 넣으면 안 되는 것** — 이 저장소의 구조적 제약이다:

- **서버 기동을 요구하는 검증** — 포트가 lane 사이에서 충돌한다
- **celery 경유 검증** — worker 컨테이너가 메인 체크아웃의 소스를 mount 하므로 워크트리에서는
  **내 코드가 아니라 메인 코드가 돈다**(침묵 실패)
- **`mise run up|down|migrate|seed`** — 컨테이너와 앱 DB 는 1벌 공유라 함께 깨진다
- **환경 변수 통째 소싱 없는 pytest** — DB 가드가 거부한다(rc=3)
- **BE 전량 pytest** — lane 수만큼 곱해진다. 광역 회귀는 CI 와 사람의 통합 검수가 본다

**러너가 도는 동안** 같은 체크아웃에서 다른 세션이 작업하면 안 된다(공유 작업 트리).

## 실행

```bash
python3 tools/harness/execute.py <phase-dir> [--push]     # 순차 — phase 하나
```

병렬은 워크트리마다 위 명령을 `nohup … &` 로 띄우고 각 `phases/<dir>/index.json` 을 폴링한다.
★띄우는 셸의 PATH 에 `uv` 가 있어야 한다 — 러너는 AC 를 **비로그인 `bash -c`** 로 돌린다.
★워크트리에는 `.venv` 가 따로 필요하다 — `tools/scripts/worktree-bootstrap.sh --adopt-env`.

저작 규약(step 파일 형식 · AC 규약 §C-5a~5e)의 정본 = `.claude/commands/harness.md`.
산출물(`runs/`)은 `.gitignore` 가 막는다.
