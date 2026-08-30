# QuantBridge — Refactoring Backlog

> **열린 백로그 — ACTIVE ∪ PARTIAL.** DEFERRED 는 [`backlog-deferred.md`](./backlog-deferred.md),
> RESOLVED 는 **파일이 아니라 삭제**다(`AGENTS.md` §6 — 끝난 것은 git 이 갖는다).
> ★**tombstone (ADR-026 §5).** 옛 본문이 가리키던 `_archived.md`(Resolved + stale 137건)·`_deferred.md`(부활 가능 8건)는
> 2026-08-06 문서 대개편에서 삭제됐다 — 원문 = `git show 0f0f0b06:docs/archive/refactoring-backlog/_archived.md`
> (`_deferred.md` 동일 경로). 그 뒤 강등분(2026-08-06 entry-set-divergence)의 본문 = `git show 23a9fcd4:docs/backlog.md`.
> ★`docs-audit.sh` 는 2026-08-19 [ADR-037] 로 철거됐다 — **치지 마라, 없다**(아래 검사기 절 참조).
> ★**2026-08-13 docs-diet.** RESOLVED **78건**의 본문을 접었다 — 각 섹션에 `### BL-nnn` 헤더 +
> `**Priority:**`(또는 `**우선순위:**`) + `**상태:**` + **원래 있던 경우에 한해** `**Title:**` 을 남기고
> 나머지는 `📦 본문 접힘` 1줄로 대체했다. 접힌 78건의 원문 전량 = `git show 8abd0d67:docs/backlog.md`.
> ★**수치는 여기 박지 않는다** — 이 헤더 자신이 파일 크기를 바꾸므로 박는 순간 stale 이다. `wc -m` 으로 재라.
>
> ---
>
> ★★★**2026-08-23 원장 다이어트 tombstone — 삭제된 것과 그 좌표.**
> **복원 좌표 = `git show 21e40d5c:docs/backlog.md`** (`backlog-deferred.md`·`backlog-resolved.md` 동일 SHA).
>
> | 무엇 | 몇 건 | 왜 |
> | --- | --- | --- |
> | `backlog-resolved.md` **파일 전체** | 159 | 끝난 것의 기록. git 이 이미 원문을 갖는다 |
> | DEFERRED 섹션 | 160 | **트리거가 「그 코드 만질 때 / 그게 필요해질 때」인 조건부 메모**. 원장에서 골라질 일이 없다 |
> | ACTIVE 섹션 | 10 | 사용자 결정 3건(아래)이 닫았다 — **BL-003 · BL-014 · BL-186 · BL-458 · BL-492 · BL-591 · BL-638 · BL-648 · BL-667 · BL-736** |
> | `status.md` ⓪ 표 취소선 행 | 43 | 끝난 일의 취소선이 매 세션 22k 토큰을 먹고 있었다 |
>
> **판정 근거 = 2026-08-23 사용자 결정 3건:**
> ⑴ **실자금(mainnet) 안 간다** — Bybit demo 만. money-path 「실자금 정밀도」 축을 닫는다
> ⑵ **Beta 외부 공개 당분간 안 연다** — 「사용자 수요 등장 시」 전제 항목을 닫는다
> ⑶ **멀티 거래소 안 한다** — Bybit 하나. OKX·Binance 전제 항목을 닫는다
> 셋 중 하나라도 뒤집히면 위 SHA 에서 해당 축을 되살려라 — **다시 쓰지 말고 되살려라.**
>
> ★★**2026-08-30 원장 트리아주 tombstone — 종결 12건(40 → 28).** 원문 = `git show 165b1e97:docs/backlog.md`(`backlog-deferred.md` 동일 SHA).
> **배치 1(5건) — 닫는 근거가 이미 자기 섹션 본문에 있었다:** [BL-453] 「⇒ 종결 후보다」 자기 선언(선언·사용 두 축 모두 CI 가드 green) ·
> [BL-371] 트리거 「post-Beta」가 결정 ⑵ 로 **발화 불가** · [BL-776] 2026-08-19 결정 「개방 유지 + 카피 수정」이 이미 닫음 ·
> [BL-792]·[BL-796] 트리거 대상이 레포에 **0건**.
> **배치 2(3건) — 2026-08-23 결정 3건이 트리거를 죽였다:** [BL-434] 잔여 근거가 [BL-437] **죽은 앵커**를 가리키고 남은 Partial-mode
> limit-TP 는 dogfood 실측 「Bybit flat 시 자동취소」 · [BL-661] 앞절 「실자금 전환 전」이 결정 ⑴ 로 사망하고 **조용한 실패는 이미 제거**
> (409 + 잔량 출력 + exit 3) · [BL-489] **처방이 없다** — 원장이 든 2-pass 가 고정점 논증으로 반증돼 착수하면 반증된 처방을 구현한다.
> **배치 3(4건) — 목적 달성 · 전제 소멸 · 중복:** [BL-641] **목적이 달성됐다**(2026-08-29 게이트
> `✓ 24.0182h ≥ 24h · 실격 0 · 누적 **3회** · exit 0 = PASS`)이고 이것이 선행이던 [BL-003] 은 결정 ⑴ 로 이미 삭제 ·
> [BL-519] **전제가 실태와 다르다** — 서버 API 는 컨테이너가 아니라 **systemd** 로 뜨고
> `tools/scripts/api-service.sh:152` 가 `Environment=PROMETHEUS_MULTIPROC_DIR=` 를 **이미 주입**한다
> (compose 에 `api:` 서비스는 여전히 없으므로 **컨테이너 API 로 가면 되살려라**) ·
> [BL-619] 관측 장치 배치 후 재관측 **0건**(15.30h 창 · 2분 공백 0) — 부검할 사건이 없다, 재발하면 새로 등재하는 것이 싸다 ·
> [BL-477] → **[BL-529] 로 병합**(같은 결함의 두 기술이었다 — 477 의 실측은 529 본문이 흡수).
> ⇒ **27건** — ACTIVE **2**([BL-835]·[BL-836]) · PARTIAL **2**([BL-529]·[BL-827]) · DEFERRED **23**.
> ★**[BL-774] 는 종결이 아니라 재판정**이다 — 마커 `⬜ Open`(판정어 5종 밖) → `⏳ DEFERRED` 로 고치고
> `backlog-deferred.md` 로 옮겼다. **2026-08-30 사용자 = TradingView 유료 플랜을 지금 결제하지 않는다**
> (webhook alert 는 유료 기능이라 실측 자체가 불가능) · 그리고 **결제하지 않는 사용자를 타겟팅하는 방향**을
> 검토 중이다 — 그 방향이 확정되면 webhook 은 주 경로가 아니게 된다(항목 본문 참조).
>
> ★**2026-08-30 추가 종결 1건 — [BL-476]**(공개 webhook 핸들러의 동기 CCXT 왕복 3회 = 실측 **+4.8초**).
> [BL-774] 와 **같은 축**이다 — 트리거가 「TradingView 실연동 전」인데 그 실연동은 **유료 플랜을 결제해야**
> 성립한다. 결제하지 않기로 한 이상 이 지연은 **발현하지 않는다**(2026-08-30 사용자 결정).
> ★**결제가 뒤집히면 [BL-774] 와 함께 되살려라** — 둘은 같은 회차에서 같이 열린다.
> 원문 = `git show ec26e28d:docs/backlog-deferred.md`.
>
> ⚠️★**BL-nnn 인용이 섹션을 못 찾는 것은 정상이다.** 이 다이어트로 **269종**이 새로 끊겼고,
> 그 전에도 **156종**이 이미 끊겨 있었다(2026-08-23 실측 — RESOLVED 아카이브·roadmap 전용 항목).
> 인용 1,507회를 고치는 대신 이 tombstone 하나로 닫는다. 끊긴 인용을 보면 위 SHA 를 열어라.
>
> ★★**어느 줄이 게이트에 집행되는지 실측했다 (변이 5종).** 「넉 줄 다 필수」는 **거짓**이다:
>
> | 지운 것            | `bl-audit` | 비고                                                  |
> | ------------------ | ---------- | ----------------------------------------------------- |
> | `### BL-nnn` 헤더  | **red**    | 「표 행만 있고 섹션이 없다」                          |
> | `**상태:**` 줄     | **red**    | 「표 행에 ✅ 인데 섹션은 ACTIVE」                     |
> | `**Priority:**` 줄 | **red**    | 「Pn 표에 실렸는데 섹션에서 우선순위를 못 읽었다」    |
> | `**Title:**` 줄    | green      | ★**집행되지 않는다** — 78건 중 **33건은 애초에 없다** |
> | `📦 본문 접힘` 줄  | green      | ★**집행되지 않는다** — 사람을 위한 표기다             |
>
> ⇒ 접기를 다시 할 때 **앞 셋은 반드시 남겨라.** 뒤 둘은 사라져도 게이트가 안 운다 — 사람이 지켜야 한다.
>
> ★★★**2026-08-21 — 이 파일이 언급하는 검사기 4종은 존재하지 않는다.** [ADR-037] 제로베이스가
> `bl-audit.sh` · `docs-audit.sh` · `bl-trigger-sweep.sh` · `final-gates.sh` 를 **2026-08-19 에
> 철거했다**(원문 = `git show harness-v1:tools/scripts/`). 아래 산문에 남은 그 이름들은 **당시의
> 이력**이지 지금 돌릴 명령이 아니다 — **치지 마라, 없다.**
> 지금 기계로 집행되는 것은 `tools/scripts/ledger-vitals.sh` **3축뿐**이다(다음 행동 ≤1 ·
> ⓪ 표 행 **≥1**(2026-08-25 사용자 결정으로 ≥3 에서 내렸다) · RESOLVED 역류 0). 나머지 규칙(원장 3분할 · `**상태:**` 줄 · 3면 일치 · 줄 길이
> 상한)은 **규칙으로 남았고 사람이 지킨다.** 판정어별 목록이 필요하면 `grep '^### BL-'` 과
> `grep '^\*\*상태:\*\*'` 로 직접 세라. 복귀는 **재입힘 규칙**(문서화된 사고 1건 = 슬림 복귀 1건) 경유다.

> ★★★**2026-08-18 수명 분리 완료 ([BL-779]).** 원장은 **파일 둘**이고 **축은 판정어**다 —
> 본 파일 = **ACTIVE ∪ PARTIAL** · [`backlog-deferred.md`](./backlog-deferred.md) = **DEFERRED**.
> ~~`backlog-resolved.md` = **RESOLVED**~~ → **2026-08-23 파일째 삭제** — RESOLVED 는 파일이 아니라
> **지운다**(`AGENTS.md` §6). 복원 좌표는 이 헤더 위 「원장 다이어트 tombstone」이 갖는다.
> ★**이 분할은 이제 산문이다** — 집행하던 `bl-audit.sh` 「파일 배치」 축이 [ADR-037] 로 철거됐다.
> 2026-08-16 의 1차 분할도 산문이라 그 뒤 닫힌 **13건이 전부 이 파일에 다시 쌓였다** — 같은 일이
> 다시 일어날 수 있으니 **항목을 옮길 때 판정어를 먼저 보라.**
>
> ★★**2026-08-30 — 인덱스 표(`## P0`·`## P3`)와 `## Cross-reference`·`## Beta 오픈 번들` 절을 지웠다.**
> 원문 = `git show 165b1e97:docs/backlog.md`. 근거: ⑴ 인덱스 표는 **RESOLVED 파일이 있던 시절의 장치**다
> (「본문은 옮기고 표 행은 남긴다」) — RESOLVED = 삭제가 된 2026-08-23 이후 존재 이유가 없다 ·
> ⑵ P0 표는 데이터 행이 **0**이었고 P3 표 2행([BL-557]·[BL-616])은 **섹션이 딴 파일**이라 `#bl-nnn`
> 앵커가 아무 데도 안 닿았다([BL-801] 이 접두사 시도를 이미 되돌렸다) ·
> ⑶ Cross-reference 표가 인용하던 BL(026·023·014·015·010·025·022)은 **전부 섹션이 없다** — 정보 0.
> ⇒ **분류 축은 이제 판정어 하나다.** Pn 은 각 섹션의 `**Priority:**` 줄이 갖는다.
>
> **신규 sprint 진입 시 본 문서 review 의무** — 각 BL 의 trigger 가 도래했는지 확인하고, 도래한 것은
> `docs/status.md` ⓪ 표에 행으로 올린다(그 표가 유일한 진입점 — 「active TODO.md」는 없는 파일이다).
> DEFERRED 도 6-8주마다 재평가한다.

> ★이 수치는 손으로 세지 말고 기계적으로 재라 — 직전까지 "49 active" 로 여러 스프린트 동안 stale 했고, 그 다음 표기 "86 active / 전체 135" 도 실측(217 섹션)과 어긋나 있었다. **산식은 이제 문서 주석이 아니라 스크립트다:**
>
> ★**아래 명령은 2026-08-19 [ADR-037] 로 철거됐다 — 치지 마라.** 대체를 함께 적는다.
>
> ★★**판정어는 낱말이 아니라 마커다** — 상태줄은 `⏳ 대기 (트리거 미도래)` · `✅ Resolved` ·
> `🔵 ACTIVE` · `🟡 부분 Resolved` 로 쓴다. **`grep -oE 'ACTIVE|DEFERRED|…'` 로 세면 9건만
> 잡히고 나머지 351건을 놓친다**(2026-08-21 실측 — 내가 먼저 밟았다). 마커로 세라.
>
> ```bash
> # ✗ 없다: bl-audit.sh · bl-trigger-sweep.sh · docs-audit.sh · final-gates.sh
> #        (원문 = git show harness-v1:tools/scripts/)
> # ✓ 섹션 수 — 원장 3종을 한 벌로
> grep -ch '^### BL-' docs/backlog.md docs/backlog-deferred.md | paste -sd+ - | bc
> # ✓ 판정어 집계 — 마커 기준 (셸 로케일이 이모지를 흘리므로 python 으로 센다)
> python3 -c "
> import re,pathlib,collections
> M={'⏳':'DEFERRED','✅':'RESOLVED','🔵':'ACTIVE','🟡':'PARTIAL','❓':'UNKNOWN'}
> c=collections.Counter()
> for f in ['docs/backlog.md','docs/backlog-deferred.md']:
>     for s in re.split(r'^### (?=BL-)', pathlib.Path(f).read_text(), flags=re.M)[1:]:
>         m=re.search(r'^\*\*상태:\*\*(.*)\$', s.split(chr(10)+'### ')[0], re.M)
>         c[next((v for k,v in M.items() if m and k in m.group(1)), 'NONE')]+=1
> print(c)"
> ```
>
> **2026-08-30 실측** — 섹션 **28** · `🔵 ACTIVE` **3** · `🟡 PARTIAL` **1** · `⏳ DEFERRED` **24**.
> ★이 수치는 커밋마다 낡는다 — **손으로 세지 말고 위 명령을 다시 돌려라.**
>
> ★**2026-08-10 부터 판정어가 다섯이다** — `ACTIVE / DEFERRED / PARTIAL / RESOLVED / UNKNOWN`([ADR-028](./adr/028-backlog-deferred-verdict.md)). `DEFERRED`(상태줄 `⏳ **대기 (트리거 미도래)**`)는 🟡 와 마찬가지로 **active 로 세지 않는다.** 종전에는 「조건이 아직 안 왔다」를 적을 낱말이 없어 열린 항목이 **전부 ACTIVE** 로 떨어졌고, 그래서 ACTIVE 159 는 작업량이 아니라 **셈하는 규칙이 만든 수**였다(전량 판정 후 **9**). 미도래의 경계는 **외생 조건**(사용자 승인·cutover·Beta·소크·외부 관측·미해결 선행 BL)**과 동승 조건**(「그 파일을 다음에 열 때」류 — 단독 착수 시 값이 0이라고 트리거 자신이 선언한 것) **둘 다**를 포함한다. 3면에서 DEFERRED 는 **ACTIVE 와 같은 「미완」 쪽**이다. 각 섹션의 `**트리거 판정:**` 줄이 **무엇이 막는지**를 적는다.
>
> ★**낡은 산식(인라인 awk)은 폐기했다.** 그것은 "섹션 본문 어딘가에 `Resolved` 문자열이 있으면 RESOLVED" 였고, 그래서 **cross-ref 한 줄이 항목을 지웠다** — `BL-003`(P0, 열려 있음)이 자기 섹션의 `BL-004 ✅ Resolved` 두 줄 때문에 RESOLVED 로 집계돼 **공식 산식이 P0 active 를 0 으로 보고하고 있었다**(BL-499·BL-535 도 같은 뿌리). 새 산식의 SSOT 는 각 섹션의 `**상태:**` / `**Status:**` **줄 하나**이고, 근거가 없으면 추측하지 않고 **UNKNOWN 으로 남긴다**. 🟡 부분 Resolved 는 종전대로 active 로 세지 않는다.

---

## 분류 차원

### Priority

| 라벨   | 의미                                               | 예시                                                      |
| ------ | -------------------------------------------------- | --------------------------------------------------------- |
| **P0** | dogfood-blocker / H1 종료 gate                     | submitted watchdog, mainnet runbook, 본인 1~2주 dogfood   |
| **P1** | risk-mitigation / 알려진 broken bug 패턴 재발 위험 | commit-spy 도메인 확장, Redis lease, Auth circuit breaker |
| **P2** | hardening / nice-to-have 가 아닌 "건강도" 작업     | cardinality allowlist, dogfood 통합 dashboard             |
| **P3** | nice-to-have / 컨벤션 정합 / 미래 path             | zod import 정정, Path γ/δ                                 |

### Trigger 유형

- **time-based** — Sprint N+ / Q2 / H2 말 등 시점 명시
- **event-based** — "after dogfood week 1", "Beta 5명 onboarding 후" 등 외부 사건
- **dependency-based** — 다른 BL 또는 외부 자원 (예: Bybit mainnet API key) 후
- **on-demand** — 특정 PR / sprint 안에서 발견 시 즉시

---

## 운영 규약

> ★**2026-08-30 재작성.** 종전 3절은 **현행 규칙과 정면으로 충돌**하고 있었다 — 「해소 시
> `**Status:** ✅ Resolved` 를 달고 6줄 ledger 를 남긴다」는 2026-08-23 의 「RESOLVED 는 삭제다」와
> 반대고, 「본 문서 P0 섹션 전체 review」·「`_deferred.md` 재평가」·「active TODO.md 로 승격」은
> 셋 다 **없는 대상**을 가리켰다. 원문 = `git show 165b1e97:docs/backlog.md`.

### 신규 항목 추가

1. `### BL-NNN` 섹션을 만든다. **필수 4줄** = `**Title:**` · `**Priority:**` · `**Trigger:**` · `**상태:**`(판정어 마커).
   다음 ID = `grep -ho 'BL-[0-9]*' docs/backlog*.md | sort -u | tail -1` 의 다음 번호. **ID 재사용 금지.**
2. `**트리거 판정:**` 줄에 **무엇이 막는지**를 적는다. 이 줄이 없으면 다음 세션이 도래 여부를 처음부터 다시 조사한다.
3. 출처는 `파일:라인` 또는 커밋 SHA. **장문의 재현·반증·대안 서사는 여기 쓰지 마라** — 커밋 메시지가 정본이다.
4. 판정어가 DEFERRED 면 [`backlog-deferred.md`](./backlog-deferred.md) 에 쓴다. **파일이 곧 축이다.**

### 항목 해소

★**RESOLVED 는 마킹이 아니라 삭제다**(2026-08-23 · `AGENTS.md` §6). 끝난 항목은 섹션을 **지우고**
헤더 tombstone 에 「무엇을 · 왜 닫았나 · 원문 SHA」 한 줄을 남긴다. 6줄 ledger 를 남기던 옛 절차는
폐기됐다 — **그 절차가 이 파일을 124KB 로 만든 원인이다.**

### Trigger 도래 확인

1. 열린 항목 전건의 `**트리거 판정:**` 을 읽는다 — 그 줄이 도래/미도래의 근거를 갖는다.
2. `backlog-deferred.md` 는 **6-8주마다** 재평가한다.
3. 도래한 것은 `docs/status.md` ⓪ 표에 행으로 올린다 — **그 표가 유일한 진입점**이다.
4. ★**닫을 때 원장 밖도 함께 보라** — 이 회차가 [BL-453]·[BL-641] 두 건에서 「원장 본문이 이미
   종결 근거를 적어 두었는데 아무도 안 닫은」 상태를 발견했다.

---

## 변경 이력

> ★**2026-08-23 강등 tombstone.** 변경 이력 312줄(2026-04~08)을 **삭제**했다 — 원장의 변경 이력은
> **git log 가 정본**이고 여기 다시 적는 것은 순수 중복이었다.
> 원문 = `git show 21e40d5c:docs/backlog.md` (`## 변경 이력` 절).
> 앞으로 이 절에는 **원장의 구조가 바뀔 때만** 한 줄 적는다 — 항목 추가·상태 변경은 적지 마라.

- **2026-08-30** — 원장 트리아주. 항목 **40 → 28**(종결 12 + [BL-477]→[BL-529] 병합 + [BL-774] 재판정) · **인덱스 표 축 폐지**(P0·P3·Cross-reference·Beta 번들 삭제 — 분류 축은 판정어 하나) · 운영 규약 3절 재작성(현행 규칙과 충돌하고 있었다) · 헤더에서 끝난 회차 산문 151줄 삭제. `backlog.md` **855 → 300줄**. 헤더의 tombstone 참조
- **2026-08-23** — 원장 다이어트. RESOLVED 파일 삭제 · DEFERRED 183→23 · ACTIVE 26→16 · 인덱스 표 70행 정리. 판정 근거 = 사용자 결정 3건(실자금 안 감 · Beta 안 염 · 멀티 거래소 안 함). 헤더의 tombstone 참조
- **2026-08-18** — 원장 3분할([BL-779]) — ACTIVE∪PARTIAL / DEFERRED / RESOLVED 세 파일

---

## 열린 항목 — ACTIVE ∪ PARTIAL

> ★**DEFERRED 는 여기 없다** — [`backlog-deferred.md`](./backlog-deferred.md) 가 갖는다(축 = 판정어).
> ★**2026-08-30 tombstone.** 이 자리에 있던 `## Deferred` 헤더 + `BL-005` 표 1행 + [BL-641] 의 MTBF 층화
> 산문 27줄을 지웠다 — 헤더는 **ACTIVE 3건을 「Deferred」 아래 두고 있었고**(배치 오류), 표 행의 본문은
> `backlog-deferred.md` 에 있으며, MTBF 산문은 주인([BL-641])이 종결돼 고아였다.
> 원문 = `git show 165b1e97:docs/backlog.md`.

### BL-529

**Title:** 같은 Bybit uid 를 두 계정 행이 스윕해 청산 원장이 2배로 적재된다
**Category:** Trading / 데이터 위생
**Priority:** P2
**Trigger:** 전략 누적 지표를 신뢰해야 할 때
**Est:** S
**상태:** 🟡 부분 해결 — 스윕 uid dedup(BL-605)과 화면 문구는 구현됐다 — 잔여는 등록 시 uid 중복 경고와 이미 쌓인 거울 행/중복 계정 행 정리(사용자 승인). (2026-08-09 status-triage-mass 코드 대조)
**트리거 판정:** 미도래 — 동승 조건(전략 누적 지표를 신뢰해야 할 때) + 2026-08-11 사용자 결정. 거울 행 정리 경로가 2026-08-11 에 닫혔다 (2026-08-11 bl-703-partial-verdicts)

★★**2026-08-30 — 구 [BL-477] 을 여기로 병합했다(그쪽 섹션 삭제 · 원문 = `git show 165b1e97:docs/backlog.md`).**
둘은 **같은 결함의 두 기술**이었다 — 「같은 서브계정의 API 키 2개」(477)와 「같은 uid 를 두 계정 행이 스윕」(529)이
같은 문장이다. 477 에만 있던 실측을 여기 흡수한다:

| 무엇                     | 실측 (2026-08-11 ledger-truth)                                                                       |
| ------------------------ | ---------------------------------------------------------------------------------------------------- |
| 두 계정의 `exchange_uid` | **둘 다 `558689281`** (`0277c150` · `19a8166a`)                                                       |
| `0277c150` 의 의존 행    | `exchange_exits` **290** · `orders` **2** · `live_signal_sessions` **1** (★「읽기 전용 계정」이 아니다) |
| FK 제약                  | `ondelete="RESTRICT"` **×3** — `trading/models.py:244` · `:509` · `:785`                              |
| DELETE 핸들러            | `trading/router.py:274-291` → `svc._repo.delete()` 직행. `IntegrityError` 핸들러가 **router·service 양쪽 0건** |

⇒ 「계정 행을 지우면 자연 소멸」은 **「지금 누르면 500」**이다. **2026-08-11 사용자 결정 = 삭제하지 않는다.**
그러므로 남은 처방은 **⑴ 등록 시 uid 중복 경고 · ⑵ 귀속을 `(exchange, exchange_order_id)` 기준으로 재조회**이고,
그 앞에 `router.py:288` 이 **409** 를 내게 하는 것이 선행이다(현재 500 은 「왜 안 되는지」를 안 알려 준다).
★손익 이중 계상은 **없다** — `aggregate_closed_pnl`(`exchange_exit_repository.py:43-59`)이 계정 스코프이고
세션 손익은 `orders.realized_pnl` 을 센다. 아픈 곳은 **귀속·알림 표면**(`unattributed_count` 부풀림)이다.
**출처:** 2026-07-28 live-outcome-parity 실측

**원인 / 영향:** `exchange_exits` 실측 — 계정 행이 2개(`0277c150` / `19a8166a`)인데 **둘 다 같은 Bybit uid** 를 가리켜 같은 청산이 계정별로 2행 적재된다. 한쪽은 32행 전부 `matched_order_id IS NULL` 이다.

- 세션 단위 표면은 **무해**하다(한 세션 = 한 계정).
- 전략 누적과 계정 진단에서 **`unattributed_count` 가 부풀려진다**(실측 37 중 다수가 거울 행).
- `aggregate_closed_pnl` 은 계정 스코프라 안전하지만, 계정을 안 거는 새 집계를 만들면 즉시 2배가 된다.

**권장 접근:** 등록 시 거래소 uid 중복을 감지해 경고하거나, 스윕을 uid 단위로 dedupe 한다. 화면은 그때까지 "계정 행마다 중복 적재될 수 있음" 을 명시한다(이번 스프린트에서 문구 반영).
**Risk:** 🟢

**🔁 재확인 (2026-07-29, live-close-completeness 리뷰):** 거울 행이 **실재로 재확인**됐다 — `exchange_exits` 분류 집계에서 `ours` **30행**과 `unknown` **30행**이 건수뿐 아니라 **net 합계까지 −27.6870 으로 동일**했다. 같은 청산이 계정 행 2개에 각각 적재된다는 BL 본문의 진단과 일치한다.

★이 확인은 live-close-completeness 플랜(W4)이 "등재 내용 보강만" 으로 약속했으나 **그 PR 에서 누락**됐고, 사후 Spec 리뷰가 잡아 여기 반영한다. 스코프를 줄인 게 아니라 **적어놓고 안 한 것**이므로 같은 누락이 반복되지 않도록 기록해 둔다.

---

### BL-827

**Title:** 계약 drift 게이트가 CI 밖이라 2주간 아무도 안 봤고, PoC 생성물은 그 소스와 어긋난 채 굳었다
**Category:** Tooling / OpenAPI 계약
**Priority:** P3
**출처:** 2026-08-25 BL-822 PR #828 의 `/code-review` 발견 (코드 대조 확인)

**증상 (실측):** `mise run openapi-check` 가 `.github/workflows/ci.yml` 어디에서도 호출되지 않는다(`grep openapi ci.yml` = 0건). 그래서 BL-822 회차가 `export_openapi.py` 를 돌리자 **이 회차와 무관한 선행 drift** 가 딸려 나왔다 — `ClosePositionConflictResponse` · `RestingEntriesConflictDetail` · `/close` 409 응답이 커밋된 계약에 빠져 있었다(코드 유입은 `6784fceb`/PR #809). 2단(orval 부분집합)도 같은 처지고, 거기서 파생되는 `apps/web/src/lib/api-contract-poc/generated/**`(orval + openapi-typescript)는 **재생성 자체가 아무 절차에도 없어** `completed_trades` 가 0건이다(소스인 `openapi.poc.json` 에는 있다). 생성기 설정은 `apps/web/orval.poc.config.ts` 로 실재한다.
**동승 항목:** `deriveTradeCounts`(`apps/web/src/features/backtest/trade-counts.ts`)가 `Math.max(0, total - completed)` 로 **두 저장소(trades 테이블 vs JSONB)의 불일치를 조용히 0 으로 눌러** 준다. `apps/api/src/backtest/schemas.py` 가 문서화한 불변식 `num_trades == completed_trades + total_open_trades` 를 `_to_detail` 도 테스트도 단언하지 않는다.
**권장 접근:** ⑴ `openapi-check` 를 CI backend 잡에 얹는다(~~2단까지~~ → 아래 2026-08-30 결정으로 **1단만**). ⑵ ~~PoC 생성물을 계약에서 재생성하거나, 비교 산출물로서의 수명이 끝났으면 **삭제**한다([ADR-031] PoC 결론 확인 필요)~~ → **2026-08-30 사용자 결정 = 삭제**. ⑶ `_to_detail` 에 `direction_counts[0] >= m.num_trades` 위반을 관측 로그로 남긴다(응답을 깨지 말고).

★★★**2026-08-30 재측정 — 이 섹션의 「스키마 3개」가 이미 낡았다.** 지금 drift 는 **845줄**이고 빠진 것은 스키마가 아니라 **엔드포인트 4종 전량**이다: `/api/v1/llm/models` · `/api/v1/strategies/generate` · `/api/v1/strategies/{id}/brief` · `/api/v1/strategies/{id}/brief/narrative`. 즉 [ADR-040]·[ADR-041]·[ADR-042] + PR #843 이 **회차 4개에 걸쳐 계약 밖으로 나갔고 아무도 못 봤다.** 게이트가 CI 밖인 대가가 「2주」가 아니라 「축 하나 통째」로 커졌다.

★★**착수 전 함정 하나가 실측으로 사라졌다.** `mise run openapi-check` 는 `.env.local` 을 통째로 소싱하는데 **CI 엔 `.env.local` 이 없다**(이 레포가 이미 밟은 함정) ⇒ 「CI 한 줄」이 거짓일 위험이 있었다. 2026-08-30 에 CI backend 잡이 **이미 갖고 있는 env 8종만으로** `uv run python scripts/export_openapi.py --check` 를 돌려 rc=1(= drift 검출, 설정 크래시 아님)을 확인했다 — `TRADING_ENCRYPTION_KEYS` 가 그 잡에 이미 있다. **전제 성립: 정말로 한 줄이다.**

★**PoC 삭제 파급 = 7좌표**(2026-08-30 전수). ⑴ `apps/web/src/lib/api-contract-poc/**`(생성물 2 + 자체 테스트 `zod-v4-coexist.test.ts`) ⑵ `apps/web/orval.poc.config.ts` ⑶ `contracts/openapi/poc/openapi.poc.json` ⑷ `tools/scripts/openapi-poc-filter.py` ⑸ `apps/api/tests/scripts/test_openapi_poc_filter.py` ⑹ `mise.toml` 의 `openapi-check` **2단 → 1단** ⑺ 문서 4곳(`docs/api/endpoints.md` · [ADR-031] · [ADR-035]:155 · 이 섹션). ★`zod-v4-coexist.test.ts` 는 **PoC 전용**임을 확인했다 — 생성 스키마가 사라지면 잴 대상이 없다(독립 가치 0).

★**곁다리 — 문서가 게이트 부재를 가리고 있었다.** `docs/api/endpoints.md:31` 이 「`mise run openapi-check` 가 drift 를 막고, CI **`backend_static` 잡**이 같은 검사를 한다」고 적는다. **그 잡은 존재하지 않는다.** 이 줄을 함께 지워라 — 안 지우면 다음 사람이 또 「게이트가 있다」고 읽는다.

★**2026-08-30 ⑴⑵ 종결**(n14 lane `ci-gates` · PR #850 → 통합 #851 `4b270510`). ⑴ `ci.yml` backend 잡에 `export_openapi.py --check` 와 `uv run mypy src` 를 **차단 게이트**로 얹었다(`ruff` 다음 · `pytest` 앞 · `continue-on-error` 없음). ⑵ PoC 7좌표 삭제 완료. 계약 파일은 **+848줄**로 재생성돼 엔드포인트 4종이 돌아왔고, `mise run openapi-check` 는 2단 → **1단**이 됐다. `endpoints.md` 의 유령 잡(`backend_static`) 문장도 지웠다.
★**동승으로 mypy 3건을 수리했고 그중 하나는 타입 흠이 아니라 잠복 결함이었다** — [BL-836]. `classify_script().track` 의 도메인에 `"unknown"` 이 있는데 `StrategyBriefResponse.track` 은 `Literal["S","A","M"] | None` 이라, `unknown` 이 나오면 응답 생성에서 ValidationError = **brief 500** 이었다(기존 `try/except` 밖에서 난다).
★**게이트가 실제로 도는 것을 CI 가 증인으로 세웠다** — 통합 PR #851 의 backend 잡이 두 스텝을 포함해 green. 머지 후 main 재측정도 둘 다 rc=0.

**상태:** 🟡 PARTIAL — ⑴⑵ 종결(2026-08-30). **남은 것은 ⑶ 뿐이다** — `_to_detail` 에 `direction_counts[0] >= m.num_trades` 위반을 **관측 로그**로 남기는 일(응답은 깨지 말 것). 위 「동승 항목」의 `deriveTradeCounts` 침묵 보정이 그 근거다
**트리거 판정:** 도래 (⑶ 은 단독 착수 가능 — 게이트 축이 닫혔으므로 남은 것은 관측 한 줄이다)

---

### BL-835

**Title:** 위저드의 indicator 변환 진입점이 `supported` 분기에만 있어, 미지원 builtin 을 함께 가진 indicator 는 버튼을 못 본다
**Category:** FE / Strategy
**Priority:** P3
**출처:** 2026-08-30 n14 `convert-reach` lane 의 diff 를 사람이 읽다가 발견 (코드 대조 확인)

**증상 (실측):** `parse-result-panel.tsx` 가 변환 버튼을 **`SupportedBody` 안에서만** 렌더한다. 그런데 그 분기의 게이트는 `supported = status === "ok" && unsupported_builtins.length === 0` 이다. ⇒ `declaration.kind === "indicator"` 이면서 **미지원 builtin 을 함께 가진** 스크립트는 `UnsupportedBody` 로 떨어져 **변환 버튼이 안 보인다.** 그 사용자는 [BL-834] ⑶ 이 없애려던 바로 그 경로 — 백테스트를 제출해 422 를 받아야만 버튼을 만나는 경로 — 로 되돌아간다.
**권장 접근:** 변환 블록을 두 분기의 **공통 자리**(카드 본문)로 올린다. ★조건은 `declaration.kind` 하나로 유지해라 — `unsupported_builtins` 를 조건에 섞으면 「indicator 가 아닌데 미지원인 스크립트」에까지 indicator→strategy 변환을 권하게 된다.

**상태:** 🔵 ACTIVE — 2026-08-30 등재, 미수리
**트리거 판정:** 도래 (단독 착수 가능 · FE 한 파일)

---

### BL-836

**Title:** `track == "unknown"` 이 브리핑을 500 으로 만들던 잠복 결함이 수리됐는데 그 경로를 재는 테스트가 0건이다
**Category:** BE / Strategy
**Priority:** P3
**출처:** 2026-08-30 n14 `ci-gates` lane 의 mypy 수리 diff 를 사람이 읽다가 발견 (코드 대조 확인)

**증상 (실측):** `ast_classifier.py:31` 의 `Track = Literal["S", "A", "M", "unknown"]` 인데 `StrategyBriefResponse.track` 은 `Literal["S","A","M"] | None` 이다. `_extract_brief_parts` 는 `classify_script(source).track` 을 **그대로** 실어 보냈으므로, `_classify_track` 이 `"unknown"` 을 내는 스크립트(선언이 `strategy`/`indicator`/`library` 어느 것도 아닌 경우)는 응답 생성 시 pydantic ValidationError → **`GET /strategies/{id}/brief` 가 500** 이었다. ★그 함수의 `try/except` 는 이것을 못 잡는다 — 예외가 `try` 본문이 아니라 **응답 조립 시점**에 난다.
**수리:** 2026-08-30 에 `"S"/"A"/"M"` 멤버십을 통과한 값만 싣고 나머지는 `None` 으로 떨어뜨리도록 좁혔다(PR #850). 그 함수 docstring 의 「실패는 조용히 빈 값」 계약과 일치한다.
**남은 것:** **그 경로를 재는 테스트가 없다.** 지금 초록은 「`unknown` 이 안 난다」가 아니라 「아무도 안 재고 있다」다 — mypy 가 아니었으면 아무도 못 봤다는 것이 이 항목의 요지다.
**권장 접근:** `unknown` 을 내는 최소 Pine 소스로 `GET /{id}/brief` 가 **200 · `track: null`** 임을 단언하는 테스트 1건. 양성 대조로 `strategy()` 소스가 `track: "S"` 를 내는 것을 같이 재라.

**상태:** 🔵 ACTIVE — 2026-08-30 등재, 결함은 수리됨 · **회귀 테스트 미작성**
**트리거 판정:** 도래 (단독 착수 가능 · 테스트 1건)

---

### BL-837

**Title:** BybitPrivateStream supervisor 가 예상 밖 예외로 죽으면 stream 이 **lease 를 쥔 채** 영구 침묵한다
**Category:** Backend / trading (websocket)
**Priority:** P1
**출처:** 2026-08-30 아키텍처 감사 gap sweep — `realtime-ws` 축 (CONTROL 코드 대조 확인)

**증상 (실측):** `bybit_private_stream.py:313` 이 `self._supervisor_task = asyncio.create_task(self._supervisor_loop())` 로 감시 루프를 띄우는데 **`add_done_callback` 이 없다.** `_supervisor_loop` 이 잡는 예외는 `BybitAuthError`(fatal, return) · `ConnectionClosed`/`OSError`(재시도) · `CancelledError`(return) **셋뿐**이므로, 그 밖의 예외는 task 에 저장된 채 **아무도 안 읽는다** — `__aenter__` 는 첫 연결만 기다리고 돌아가고, 다음 관측 시점은 종료(`_wait_supervisor_done`)다. 그 사이 `websocket_task.py:144` 의 `async with lease:` 가 **`ws:lease:{account_id}` 를 계속 갱신**하므로 다른 워커가 넘겨받지도 못한다. ⇒ **private order stream 이 조용히 끊긴 채 failover 도 막힌 상태**가 된다. 라이브에서 이것은 체결을 못 보는 상태다.
**권장 접근:** supervisor task 에 done-callback 을 달아 ⑴ 예외를 로그+metric 으로 표면화하고 ⑵ `stop_event` 를 set 해 `async with lease:` 가 lease 를 놓게 한다. ★`track_pending_alert` 가 alert task 에 대해 이미 하는 것과 같은 패턴이다 — 그것을 선례로 삼아라.
**Risk:** 🟠 (라이브 신호 경로 — 수리 자체가 소크 리스크다. 회귀 = `tests/tasks/test_first_connect_race.py` 인접)

**상태:** 🔵 ACTIVE — 2026-08-30 등재, 미수리
**트리거 판정:** 도래 (단독 착수 가능)

---

### BL-839

**Title:** 느린 WS 클라이언트 1개가 전 사용자의 realtime pubsub listener 를 정지시킨다
**Category:** Backend / realtime
**Priority:** P2
**출처:** 2026-08-30 아키텍처 감사 gap sweep — `realtime-ws` 축

**증상:** `realtime/manager.py:72` 의 `send_to_user` 가 timeout 없이 `await` 한다. 단일 listener 태스크가 pubsub 메시지를 순차 배분하므로, TCP 창이 막힌 클라이언트 하나가 **모든 사용자의 실시간을 정지**시킨다.
**권장 접근:** per-send `asyncio.wait_for` + 초과 시 그 연결만 드롭. 큐를 새로 만들지 말고 timeout 부터 재라(측정 없이 큐를 넣으면 지연만 옮긴다).

**상태:** 🔵 ACTIVE — 2026-08-30 등재, 미수리
**트리거 판정:** 도래

---

### BL-840

**Title:** public ticker circuit breaker 는 쓰기만 하고 아무도 읽지 않는다 — block 키가 무효다
**Category:** Backend / tasks
**Priority:** P2
**출처:** 2026-08-30 아키텍처 감사 gap sweep — `realtime-ws` 축

**증상:** `tasks/websocket_task.py:152` 경로가 circuit breaker 상태를 기록하지만 **그 키를 읽어 차단하는 소비자가 없다.** 게이트가 있다고 믿는 상태에서 게이트가 없는 것이 이 항목의 요지다.
**권장 접근:** 읽는 쪽을 붙이거나, 안 쓸 것이면 쓰기까지 걷어낸다. ★**둘 중 하나로 끝내라** — 반쪽으로 두면 다음 사람이 또 「보호되고 있다」로 읽는다.

**상태:** 🔵 ACTIVE — 2026-08-30 등재, 미수리
**트리거 판정:** 도래

---

### BL-841

**Title:** `codex-block-dangerous.sh` 가 `jq` 실패 시 fail-open — `rm -rf /` 를 그대로 통과시킨다
**Category:** Ops / 가드
**Priority:** P2
**출처:** 2026-08-30 아키텍처 감사 gap sweep — `infra-ops` 축

**증상:** `tools/scripts/hooks/codex-block-dangerous.sh:16` 이 `jq` 파싱 실패 시 차단이 아니라 **통과**로 떨어진다. 위험 명령 차단기가 fail-open 이면 그것은 차단기가 아니다.
**권장 접근:** 파싱 실패 = 차단(fail-closed). ★음성 대조로 「깨진 입력이 실제로 막히는가」를 먼저 재라.

**상태:** 🔵 ACTIVE — 2026-08-30 등재, 미수리
**트리거 판정:** 도래

---

### BL-842

**Title:** `TimescaleProvider` 가 갭을 못 메우면 **짧은 시리즈**를 돌려주고, 백테스트는 요청한 기간으로 라벨된다
**Category:** Backend / market_data
**Priority:** P2
**출처:** 2026-08-30 아키텍처 감사 gap sweep — `market-data` 축

**증상 3종 (같은 파일):**
⑴ `providers/timescale.py:70` — 거래소가 갭을 못 채우면 짧은 시리즈를 그대로 반환한다. 결과 행에는 **요청 기간**이 적히므로 사용자는 좁은 창에서 돈 백테스트를 넓은 창의 결과로 읽는다.
⑵ `:75` — `pg_advisory_xact_lock` 이 fetch 구간이 아니라 **엔진 실행 전체** 동안 잡혀 있고 `lock_timeout` 이 없다. 옵티마이저/스트레스 테스트가 그 락을 길게 물면 다른 실행이 무한 대기한다.
⑶ `:109` — 빈 결과가 `DatetimeIndex` 가 아니라 `RangeIndex` 를 갖는다. 같은 무-데이터 입력이 `FixtureProvider` 에서는 깨끗이 실패하는데 이쪽에서는 다르게 흐른다.
**권장 접근:** ⑴ 은 「채운 실제 구간」을 결과에 싣는 것이 먼저다(조용히 좁히지 말고 보이게 한다). ⑵ 는 락 범위를 fetch 로 좁히고 `lock_timeout` 을 건다. ⑶ 은 빈 시리즈도 `DatetimeIndex` 로 통일.

**상태:** 🔵 ACTIVE — 2026-08-30 등재, 미수리
**트리거 판정:** 도래

---

### BL-843

**Title:** BL-084 prefork 가드가 `src/common/` 을 **하드코딩 2개 이름**으로 스코프해 `telegram_alert.py` 의 module-level Semaphore 를 못 본다
**Category:** Backend / 가드 신선도
**Priority:** P2
**출처:** 2026-08-30 아키텍처 감사 gap sweep — `test-architecture` 축 (CONTROL 실측: module-level Semaphore 는 `common/alert.py:49` · `common/telegram_alert.py:48` **2건**)

**증상:** `tests/tasks/test_no_module_level_loop_bound_state.py:58` 의 스캔 대상이 디렉터리가 아니라 **이름 목록**이라, 목록에 없는 `telegram_alert.py` 는 검사 밖이다. `apps/api/AGENTS.md` §9 는 allowlist 가 「현재 1건」이라고 적지만 실제 module-level Semaphore 는 **2건**이다.
**권장 접근:** 스코프를 `src/common/**` 디렉터리로 바꾸고 allowlist 를 명시 2건으로 갱신 + 문서의 「1건」 정정. ★목록형 스코프는 **파일이 사라져도 조용히 통과**한다 — 이 레포에서 반복된 유형이다.

**상태:** 🔵 ACTIVE — 2026-08-30 등재, 미수리
**트리거 판정:** 도래

---

### BL-844

**Title:** FE 실시간이 4401 재시도에서 **같은 캐시 토큰**을 다시 보내 영구 정지된다
**Category:** FE / realtime
**Priority:** P2
**출처:** 2026-08-30 아키텍처 감사 gap sweep — `fe-shared` 축

**증상:** `lib/ws-client.ts:156` 의 4401(인증 실패) 1회 재시도가 **토큰 캐시를 비우지 않고** 재연결하므로 같은 만료 토큰을 다시 보낸다. 두 번째 4401 이후 재시도가 끝나 실시간이 영구 정지한다. 동승 결함 — `lib/auth-client.ts:70` 의 `clearAuthTokenCache()` 가 **in-flight fetch 를 못 막아** 로그아웃 직후 JWT 가 다시 캐시된다.
**권장 접근:** 4401 재시도 전에 캐시 무효화 + 새 토큰 강제 취득. `clearAuthTokenCache` 는 세대 카운터(generation)를 올려 in-flight 응답을 버리게 한다.

**상태:** 🔵 ACTIVE — 2026-08-30 등재, 미수리
**트리거 판정:** 도래

---

### BL-845

**Title:** CI 가 Playwright spec **31개 중 1개**만 돈다 — 문서는 이 격차를 「1개」로 적어 두었다
**Category:** Ops / CI 커버리지
**Priority:** P2
**출처:** 2026-08-30 아키텍처 감사 gap sweep — `test-architecture` 축 (CONTROL 실측 확인)

**증상 (실측):** `apps/web/e2e/` 에 spec 이 **31개**다. `ci.yml` 은 Playwright 를 **아예 안 돌린다**(fe 잡 = `biome`+`tsc`+`vitest`+`build`). Playwright 를 도는 워크플로는 `live-smoke.yml` 하나이고 `--project=chromium-live-smoke` 인데, 그 project 의 `testMatch` 는 `playwright.config.ts:134` 의 `/live-smoke\.spec\.ts$/` — **정확히 1개 파일**이다. ⇒ **30개가 CI 에서 0회 실행**된다.
★`apps/web/AGENTS.md` §10 은 이 격차를 「`e2e/design-canon-responsive.spec.ts` 는 CI 에서 안 돈다」로 **1건**만 적어 두었다. 실제로는 그 파일이 예외가 아니라 **규칙**이다.
**권장 접근:** 먼저 **어느 spec 이 다른 게이트로 대체 불가능한 것을 지키는지** 가른다(전부 CI 에 넣는 것이 목표가 아니다 — authed spec 은 secret·DB 를 요구한다). 그다음 문서의 「1건」을 실제 목록으로 바꾼다. ★수치를 고치는 것이 이 항목의 절반이다 — 지금 문서는 커버리지를 **30배 과대**로 읽게 한다.
**Risk:** 🟢 (지금 무엇을 깨지는 않는다. 「지켜지고 있다」는 오해가 비용이다)

**상태:** 🔵 ACTIVE — 2026-08-30 등재, 미수리
**트리거 판정:** 도래 (단독 착수 가능)

---

### BL-847

**Title:** `time` 빌트인이 **달력을 조작**하는데 degraded 플래그가 없다 — `timeframe.period` 는 플래그가 있다
**Category:** Backend / pine_v2 (신뢰 층)
**Priority:** P2
**출처:** 2026-08-30 아키텍처 감사 gap sweep — `pine-v2` 축 (CONTROL 코드 대조 확인)

**증상 (실측):** `interpreter.py:1301-1306` 의 `time` 은 실제 OHLCV 타임스탬프를 **안 읽고**
`50*365*86_400*1000 + bar_index*60_000` 을 돌려준다 — **2020-01-01 시작 + 전 봉이 1분봉**이라는
가정을 만들어 낸다. 주석은 「OHLCV 에 timestamp 없으면」이라는 조건을 말하지만 **코드에 그 분기가 없다** —
언제나 합성값이다. ⇒ `time` 으로 날짜 범위·세션을 거르는 전략은 **의도와 다른 봉에서 매매한다.**

★그런데 `coverage.py` 의 `_DEGRADED_ATTRIBUTES` 에는 **`timeframe.period` 하나뿐**이고 `time` 은 없다.
`timeframe.period`(기본값 `"1D"`)가 degraded 인데 **달력 전체를 지어내는 `time` 은 아니라는 것**이 모순이다.
`CONTEXT.md` 의 Degraded Pine 정의 = 「supported 지만 TradingView 와 결과가 달라질 수 있는 호출」에 정확히 해당한다.

**권장 접근:** `time`(그리고 같은 성질이면 `timestamp`)을 degraded 로 올린다 —
그러면 `allow_degraded_pine=true` 명시 동의 없이는 제출이 막힌다.
★**이것은 순수 버그 수정이 아니라 제출 게이트 변경**이므로 사용자 판단이 필요하다.
현재 실사용자 0명이라 차단 위험은 없다. 대안은 OHLCV 실제 timestamp 를 읽게 고치는 것이고 그쪽이 근본적이다 —
**둘 중 무엇을 할지가 이 항목의 결정 사항**이다.

**상태:** 🔵 ACTIVE — 2026-08-30 등재, **사용자 결정 필요**(플래그 vs 실제 timestamp 배선)
**트리거 판정:** 도래

---

### BL-740

**Title:** stress_test 의 sharpe degenerate 판정이 convention 축을 안 읽어 **파산 셀이 「그냥 0」으로 표시**된다
**Category:** Backend / stress_test (지표 계산)
**Priority:** P2
**출처:** 2026-08-15 soak-survival 관측 → **2026-08-30 아키텍처 감사가 원인 확정**

★★**이 항목이 자기 원인을 맞혔다.** 2026-08-15 등재 당시 원인 후보 셋 중 셋째로
「**NaN 만 보는 degenerate 판정 자체가 좁다**」를 적어 두었고, 트리거를
「**Sharpe 를 판단 입력으로 쓰기 전에**」로 걸어 두었다. 2026-08-30 감사가 둘 다 성립함을 확인했다 —
옵티마이저가 `objective_metric="sharpe_ratio"` 로 Sharpe 를 판단에 쓰고 있었고,
판정은 좁은 정도가 아니라 **convention 축을 통째로 안 읽고 있었다.**

**확정된 원인:** `sharpe_ratio()` 는 equity 가 0 이하로 내려간 실행에
`(Decimal("0"), "unavailable_nonpositive_equity")` 를 돌려준다 — **값 0 은 「나쁨」이 아니라 「못 잼」**이고
진실은 convention 이 진다(`backtest/engine/metrics.py` 의 `sharpe_ratio` 계약). 그런데
`stress_test/engine/grid_result.py:73` 의 `is_degenerate = num_trades == 0 or sharpe is None` 에서
둘째 절은 `sharpe_ratio: Decimal`(비-옵셔널)이라 **죽은 가지**다. ⇒ 관측된 「전부 0 인데 `is_degenerate=False`」가
정확히 이것이다. 등재 당시의 후보 ⑴(계산이 0 을 냄)도 ⑵(매핑 누락)도 아닌 **⑶ 판정이 좁다**가 답이었다.

**옵티마이저 절반은 이미 수리됐다** — `optimizer/engine/{_common,grid_search}.py` 는 2026-08-30 에
`sharpe_is_unavailable(metrics.sharpe_convention)` 축을 받았다(PR #857). 거기서 **파산 파라미터가
`maximize` 로 「최적」에 뽑히던 것**이 실제 결함이었다(골든 코퍼스 `s2_utbot` 0.0/−298% 가
`s4_hma_curvature` −7.59/−67% 를 이겼다).

**남은 범위 (이 항목):** stress_test 쪽 3곳 — `engine/grid_result.py:73`(CA·PS 셀 판정) ·
`engine/walk_forward.py:190`(`oos_sharpe`) · `serializers.py:238`(`_worst_cell_sharpe` 가 **최악 셀을
드러내려는 지표인데 유일하게 파산한 셀을 숨긴다**).
**권장 접근:** `GridSweepMetricsCell` / WFA fold DTO 가 `sharpe_convention` 을 싣게 하고 판정·표시가 그것을 읽게 한다.
★**영속 스키마(`result_jsonb`) 변경을 동반한다** — optimizer 절반과 달리 무해한 수정이 아니다.
구 실행 행에는 그 필드가 없으므로 **`None` = 소급 판정 안 함** 규약을 그대로 따른다.

**Risk:** 🟡 (표시 축 + 영속 형태 변경. 라이브 경로는 아니다)

**상태:** 🔵 ACTIVE — 2026-08-30 승격, 옵티마이저 절반 수리됨 · **stress_test 절반 미수리**
**트리거 판정:** 도래 (Sharpe 가 판단 입력이 됐다 — 2026-08-30)
