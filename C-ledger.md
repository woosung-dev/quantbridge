# 레인 C 원장 초안 — CONTROL 이 `docs/backlog.md` 에 병합한다

레인 B 가 `docs/backlog.md` 를 재구조화 중이라 이 레인은 원장을 직접 만지지 않는다.
아래 3건을 그대로 옮겨 넣으면 된다. **이 파일 자체는 병합 후 삭제 대상이다.**

---

## 1. [BL-781] — RESOLVED

### 고칠 것 — 본문의 낡은 문장 2곳 (러너가 바뀌었다, [ADR-036])

| 자리         | 지금                                                      | 고칠 값                                                      |
| ------------ | --------------------------------------------------------- | ------------------------------------------------------------ |
| `**Title:**` | …`Makefile` 이 `BETTER_AUTH_URL` 을 슬롯 포트로 안 맞춘다 | …**격리 task** 가 `BETTER_AUTH_URL` 을 슬롯 포트로 안 맞춘다 |
| `**Est:**`   | S (Makefile 2줄 + env 문서 1줄)                           | S (`mise.toml` 2줄 + env 문서 1줄)                           |

본문 「원인 / 영향」의 `grep BETTER_AUTH Makefile` = **0건** 은 2026-08-16 시점의 실측이므로
그대로 두고, 그 문장이 가리키던 파일이 `mise.toml` 로 옮겨졌다는 사실만 상태줄이 적는다.

### 새 상태줄

```
**상태:** ✅ **Resolved (2026-08-16, `stage/bl780-781-gates` — 슬롯 2 실측).** 격리 슬롯에서
`pnpm e2e:authed` 가 **90 passed / rc=0 (4.1분)** 으로 돌았다. 수리 자체는 [ADR-036] 회차가
러너를 옮기면서 이미 들어가 있었고(`mise.toml:312` be-isolated · `:330` fe-isolated, 둘 다
`BETTER_AUTH_URL="http://localhost:${QB_FE_PORT}"` — **같은 표현식**), 이 회차가 한 것은 **증명**이다.
★**변이 2종이 서로 다른 사인을 냈다** — ⑴ `fe-isolated` 에서 그 줄을 빼면 `global.setup.ts` 가
`page.waitForURL` 60s timeout 으로 죽어 **authed 스위트가 아예 실행되지 않는다**(원인은
`POST /api/auth/sign-in/email` 이 `Origin: http://localhost:3102` 에 **403 `INVALID_ORIGIN`**).
⑵ FE·BE 를 서로 다르게 두면(`BETTER_AUTH_URL=:3999`) setup 은 **통과**하고 BE authed API 가
**전건 401** 이 되어 **12 failed / 78 passed** 다. 즉 두 결함은 증상이 갈린다.
★★**`curl` 은 이 검사를 안 거친다** — 같은 엔드포인트가 `Origin` 헤더 없이는 401
(`INVALID_EMAIL_OR_PASSWORD`, = 자격증명 검사까지 도달)을 낸다. 2026-08-16 회차가 `curl` 을 먼저
쳐 「인증은 된다」고 오판한 경로가 이것이다. **판정 증인은 브라우저다.**
`docs/reference/operations/worktree-parallel.md` §6 에 짝 규칙과 이 함정을 적었다.
```

---

## 2. [BL-780] — RESOLVED

```
**상태:** ✅ **Resolved (2026-08-16, `stage/bl780-781-gates`).** 케이스 ⑩ 의 음성 대조를 합성으로
세웠다. `final-gates.sh` 에 **`--dry-run` 한정** 영역 주입 훅 `QB_FG_FAKE_CHANGED` 를 두고
(실행 모드에서 이 변수를 주면 **rc=1 로 거부**한다 — 조용히 먹으면 그 순간 게이트 우회로가 된다),
⑩ 을 3절로 재작성했다: ⑴ 합성 음성(`docs/status.md` 만) → 「필수 아님」 ⑵ 합성 양성 BE 축
(`apps/api/src/probe.py`) → 「필수」 ⑶ 실물 양성(종전 `PROBE_SRC` 탐침 + `--allow-dirty`) → 「필수」.
⑶ 을 남긴 이유는 훅만 보는 항진명제가 되지 않게 하기 위해서다.
★**통제 실험으로 판별력을 확인했다** — `apps/web/` 을 건드린 커밋을 임시로 얹은 상태에서
**구판 rc=1(⑩ red, 사유 「diff 0 인데 필수다」) · 수정판 rc=0**. 되돌린 뒤 `apps/web` diff 가
없는 상태에서도 수정판 rc=0 이다.
★**변이 M6 신설** — 훅 대입문을 죽이면 ⑩ 이 red 다. 절 ⑴ 과 ⑵ 는 **서로 반대의 답**을 요구하므로
훅이 죽어 둘이 같은 실제 diff 를 보면 어느 트리에서든 반드시 한쪽이 깨진다 — **환경 독립 변이**다
(diff 있는 트리·없는 트리 양쪽에서 red 실측). `--mutants` = M1~M6 + N1 전건 판별.
```

---

## 3. 부트스트랩 안내문 — BL 없음, 이 회차에서 수리 완료

`tools/scripts/worktree-bootstrap.sh` 의 `Makefile`·`make` 언급 **7곳**을 고쳤다
(원안 프롬프트의 「6곳」은 `:305` 가 빠진 수치였다 — CONTROL 재측정이 맞다).

- `.worktree-slot` 헤더 = 「Makefile 이 `-include` 로 읽는다」 → 「`mise.toml` 의 task 가 `sed` 로
  읽는다」. 형식(`QB_SLOT = N`)은 그대로다.
- ★**`QB_MAIN_ROOT` 값과 그 설명 주석 2줄을 지웠다.** [ADR-036] 이 소비자를 없앴고
  `grep -rn 'QB_MAIN_ROOT'` 가 **자기 자신(쓰는 쪽) 1건**뿐이다. `assert-main-checkout.sh` 는 git 으로
  판정하고 메인 경로도 `dirname "$(git rev-parse --git-common-dir)"` 로 스스로 구한다.
  ★**이 삭제는 범위 초과다** (2026-08-16 CONTROL 판정). 이 레포 규약은 선재 사문을 지우지 말고
  **언급만** 하는 것이고, 이 회차의 과제는 「낡은 러너 안내를 고치는 것」이었지 사문 제거가 아니었다.
  소비자 0건이라는 근거 자체는 맞아서 되돌리지 않고 함께 정리했지만, 규약대로라면 언급에서
  멈췄어야 한다.
- 종결 배너 「Makefile 가드가 거부한다 — make 종료 코드 2」 → 「`assert-main-checkout.sh` 가드가
  거부한다 — 종료 코드 1」. **워크트리에서 `mise run up-isolated` 실측 rc=1** 로 확인했다.
  이 문장은 CONTROL 이 슬롯 1·2 를 부트스트랩할 때 그대로 출력된 **살아 있는 오보**였다.

`grep -nE 'Makefile|make ' tools/scripts/worktree-bootstrap.sh` = **1건(역사 서술)**.

---

## 4. CONTROL 에게 — 원장에 없던 관측 2건

1. **`apps/web/node_modules` 가 없는 상태로 이 워크트리를 넘겨받았다.** `mise run fe-isolated` 가
   `sh: next: command not found` 로 죽었다. 루트 `pnpm install` 은 `Already up to date` 인데
   이 레포에는 `pnpm-workspace.yaml` 이 없어 **`apps/web` 은 별도 프로젝트**다 — 거기서 따로
   깔아야 한다. ★**부트스트랩 자체는 이 경로를 덮는다** — 이 회차가 AC-10 확인차 재실행했더니
   `▶ 의존성 설치 … ✓ apps/web/node_modules` 를 정상 출력했다(rc=0). ⇒ 스크립트 결함이 아니라
   **슬롯 2 를 만들 때 deps 단계가 안 돈 것**이다(`--skip-deps` 였을 가능성). BL 로 올릴 사안은
   아니지만, 다음 부트스트랩에서 `--skip-deps` 를 쓰면 FE 레인이 그 자리에서 죽는다.
2. **포트 3101 을 다른 프로젝트가 쓰고 있다** — `nexus_clarification_admin` 컨테이너가
   `127.0.0.1:3101->3001` 로 떠 있다. **슬롯 1 의 FE 포트와 정면 충돌**한다. 슬롯 2 는 무관하다.
