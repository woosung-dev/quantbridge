# 레인 β 원장 초안 — [BL-785] · [BL-782]

수치의 정본은 `B-REPORT.md` 다. 여기서는 상태줄과 그 근거 한 줄만 낸다.

---

### BL-785 — 게이트가 버전 SSOT 를 우회한다

**상태:** ✅ **Resolved (2026-08-17 gate-pins)** — 로컬 스크립트 5종이 `lib/mise-shim-path.sh` 로
shim 을 PATH 앞에 세우고, `tools/scripts/tool-pin-audit.sh` 가 재유입을 막는다(`final-gates` 의
「도구 핀 감사」 + 「도구 핀 감사 하네스」, `mise run gate-harnesses` 13→14종).

- 음성 대조로 종결했다 — 낡은 `pnpm`/`uv`/`node`(`exit 1`)를 PATH 앞에 세운 채
  **수리 전 코드는 `CI frozen-lockfile` FAIL(rc=1)**, **수리 후 코드는 같은 조작에서 PASS(rc=0)**.
  판정 근거는 `B-REPORT.md` §AC-2.
- **서버(`truewords-oracle`)에서 도는 `soak-*.sh` 6종은 안 고쳤다** — 그 환경의 mise 존재를
  확인할 수 없고 서버 접속이 금지다. 감사기가 이유와 함께 면제로 인쇄한다(목록 = REPORT §AC-4).
- 이 회차가 만든 **회귀 1건을 이 회차가 잡았다** — `docs-audit-test.sh` 가 fixture 트리에 lib 를
  안 옮겨 19케이스가 전부 rc=1 이 됐다. 표적 테스트는 초록이었고 게이트 전량이 잡았다.

---

### BL-782 — `alembic check` 가 재는 DB 가 정의돼 있지 않다

**상태:** ✅ **Resolved (2026-08-17 gate-pins)** — 판정 기준을 **migration-only DB** 로 확정해
`gates-and-traps.md` §환경에 적었고, 그 기준으로 남아 있던 유일한 drift
(`trading.funding_rates.exchange` VARCHAR(32) → `exchangename`)를 migration `20260817_0002` 로 닫았다.
게이트 `CI fresh DB alembic` 과 **CI `backend` 잡** 둘 다 `upgrade head` 뒤에 `alembic check` 까지 돈다
(CI 스텝은 CI 가 돌기 전까지 미검증 — 근거는 REPORT §AC-5).

- **[BL-770] 의 「rc=0 이 처음」은 개발 DB 에 대한 것이었다.** 2026-08-17 실측 — 개발 DB 는 head
  `20260816_0001` 인데 그 컬럼이 이미 `exchangename` 이다(`create_all` 이력이 섞여 있다).
  migration 계보로만 만들면 `varchar(32)` 다. **같은 명령이 DB 마다 다른 답을 냈다.**
- 다른 drift 는 **없었다** — migration-only DB 의 `alembic check` 가 낸 항목은 이 한 컬럼뿐이다.
  따라서 「축을 하나씩」이 저절로 지켜졌고 다음 회차로 넘길 drift 후보도 없다.
- ★**서버 소크 DB 에는 적용하지 않았다.** 그 DB 의 `funding_rates.exchange` 값 집합은 확인하지
  못했다(서버 접속 금지). 라벨 밖 값이 있으면 `USING` 캐스트가 소리 내며 실패한다 — 조용히
  틀린 결과를 내지는 않는다.
- 후속 후보(이번에 안 건드림): `funding_rate_repository.py` 의 `cast(exchange, String)` 은 이제
  구조적으로 불필요하지만, migration 이 아직 안 닿은 DB 를 위해 남겼다. 전 배포처가 head 에
  도달한 뒤 걷어내면 `ix_funding_rates_exchange_symbol` 를 다시 쓸 수 있다.
