# Step 0: restart-stack-probe-fail-closed

## 읽어야 할 파일

- `tools/scripts/soak-restart.sh` — **이번 테스트의 대상**. 특히 `:100-140`(인자 파싱 ·
  `--confirm` 게이트 · ⓿ 스택 생존 3값 판정)과 `:220-300`(⓿-b 선행 · 파라미터 조회 · dry-run 출력)
- `apps/api/tests/scripts/test_soak_observe.py:19-31` — `tmp_path` 가짜 레포 관용구
- `apps/api/tests/scripts/test_db_backup_target.py` — PATH `docker` 스텁 관용구

## 배경

[BL-656] 이 만든 축이고, **그 축을 재던 `soak-restart-test.sh`(14 단언)를 [ADR-037] 이
철거했다.** 그 BL 자신이 남긴 문장이 이 lane 의 이유다:

> ★★★**결함 ①은 회귀해 있었다** — 「정적 카운트 0건으로 동결」이라 적었지만
> **그 카운트를 도는 게이트가 없었다.**

지금 상태가 정확히 그것이다 — 하네스가 사라졌고 테스트는 0건이다.

★★★**재는 것의 핵심은 종료 코드 3값이다.** `soak-stack.sh ps` 는 **0=하나라도 running /
1=완전 down / 2=못 쟀다**(docker 데몬 도달 불가)를 낸다. 초판은 `|| STACK_UP=0` 으로
**1과 2를 한데 접었고**, 그래서 `DOCKER_HOST`·context 가 어긋나 살아 있는 스택이 안 보이는
순간 「완전 down」으로 읽어 `down` 을 건너뛰고 곧장 `pin` 을 불렀다. `_pin` 의 보호는 같은
docker 로 판정하므로 **함께 눈이 멀고**, 결과는 살아 있는 컨테이너의 mount 원본(`.soak/src`)을
제자리에서 덮어쓰는 것이다. **이 레포는 원격 `DOCKER_HOST` 로 이미 그것을 밟았다.**

⇒ **못 쟀으면 멈춘다. 측정 실패를 상태로 바꾸지 마라.**

## 작업

`apps/api/tests/scripts/test_soak_restart.py` 를 신설한다.

### 호출 방식 (이 lane 의 유일한 방식)

`SCRIPT_DIR`/`ROOT` 파생 경로로 형제 스크립트를 부르므로 **`tmp_path` 가짜 레포**에 복사하고
형제 둘을 **스텁으로 갈아 끼운다.**

```
tmp/tools/scripts/soak-restart.sh          ← 진짜 파일 복사 (shutil.copy2)
tmp/tools/scripts/soak-stack.sh            ← 스텁: argv 를 기록 파일에 append 하고 지정 rc 로 종료
tmp/tools/scripts/assert-main-checkout.sh  ← 스텁: 지정 rc 로 종료(기본 0)
tmp/bin/docker                             ← 스텁: 항상 rc=1 (원장 조회를 결정론적으로 실패시킨다)
```

★**`docker` 스텁은 선택이 아니다** — 스텁이 없으면 개발 머신의 진짜 docker 가
`docker exec quantbridge-db psql …` 을 **진짜 소크 DB** 에 쏜다.

★**오라클은 「호출 순서」다** — 철거된 하네스가 쓰던 것과 같다. `soak-stack.sh` 스텁이
자기 argv 를 한 줄씩 기록하게 하고, 테스트는 **그 줄의 목록**을 단언한다.

### 최소한 이 일곱을 덮어라 (케이스 ≥7)

1. ★★**`ps` rc=2 → 스크립트 rc=2** + stderr 에 「측정하지 못했다」 취지.
   ★그리고 **기록 파일에 `ps` 한 줄만 있다** — `pin`·`up`·`down` 이 **하나도 안 불렸다**.
   **이 케이스가 이 lane 의 이유다**(2를 1로 접으면 여기서 `pin` 이 불린다)
2. **`ps` rc=0(살아 있음) → dry-run 출력이 「살아 있다」 갈래**이고 ⑷ 가 `down → pin → up` 이다
3. **`ps` rc=1(완전 down) → 「완전 down」 갈래**이고 ⑷ 를 건너뛴다고 출력한다
4. ★**dry-run 은 아무것도 집행하지 않는다** — 2·3 둘 다에서 기록 파일에 `pin`·`up`·`down` 이
   **0건**이다(⓿-b 선행은 `CONFIRM=1` 일 때만이다)
5. ★**`--confirm` 은 `assert-main-checkout.sh` 를 **먼저** 부른다** — 그 스텁을 rc=1 로 두면
   스크립트 rc=2 이고 **`soak-stack.sh` 가 한 번도 안 불린다**(기록 파일 부재).
   워크트리에서 ⑴~⑶ 만 돌고 중간에 죽는 것을 막는 순서다
6. **인자 계약** — `--strategy-id` 를 값 없이 주면 rc=2 + 「값이 없다」 ·
   알 수 없는 인자는 rc=2 + 「알 수 없는 인자」. ★`--dry-run` 과 `--confirm` 을 함께 주면
   **뒤에 오는 것이 이긴다**(파싱이 순차라 그렇다 — 실측해서 그대로 고정해라)
7. ★**`--help` 범위 대조** — `--help` 는 `sed -n '2,40p' "$0"` 로 헤더를 찍는다.
   ★**2026-08-20 실측: 이 파일의 헤더 주석은 34행에서 끝나고 35행부터는 코드다**
   (`set -uo pipefail` · `SCRIPT_DIR=` · `ROOT=` · `DB_CONTAINER=`). 즉 도움말에 **코드가 실린다.**
   ⑴ 먼저 **직접 재라**(파일을 읽어 `^#` 가 아닌 첫 줄이 몇 행인지) — 이 문장을 믿지 마라.
   ⑵ 그 사실을 테스트로 고정해라: 「도움말 출력에 `set -uo pipefail` 이 없어야 한다」를
   `@pytest.mark.xfail(strict=True, reason="…")` 로 둔다. 수리하면 XPASS 로 red 가 난다.
   ★4회차가 `db-backup.sh --help` 에서 잡은 것과 **같은 계열**(범위와 헤더가 어긋난다)이고
   방향만 반대다(그쪽은 잘렸고 이쪽은 넘친다)

★**양성 대조** — 각 케이스에서 **`soak-stack.sh` 스텁이 실제로 불렸는지**(1·5 는 반대로
안 불렸는지)를 기록 파일로 함께 단언해라. 「출력에 문자열이 있다」만으로는 대상에 닿았다는
증거가 안 된다.

★**실패원을 하나만 남겨라** — 1번을 잴 때 `assert-main-checkout` 스텁·`docker` 스텁은
**정상 경로**로 두고 `ps` rc 만 2로 만들어라. 여러 개가 동시에 실패하면 rc=2 가 어디서
왔는지 못 가른다(4회차에 변이 하나가 정확히 그래서 초록으로 샜다).

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/scripts/test_soak_restart.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/scripts/test_soak_restart.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 7
cd apps/api && uv run ruff check tests/scripts/
```

★두 번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 rc=4 (red) 다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. ★**진짜 스택·진짜 DB 에 닿지 않았는지 확인해라** — 모든 케이스가 가짜 레포 + PATH `docker`
   스텁을 탄다. `docker ps` 로 컨테이너 상태가 그대로인지 눈으로 한 번 봐라.
3. `summary` 에 ⑴ `ps` 3값 매핑 ⑵ `--help` 범위 실측치(헤더 끝 행 vs `sed` 범위)를 남겨라.

## 금지사항

- `tools/scripts/soak-restart.sh` **수정 금지.** 결함은 `@pytest.mark.xfail(strict=True)`
- ★**`--confirm` 을 진짜 형제 스크립트와 함께 실행하지 마라.** 이유: `soak-stack.sh down` 은
  **소크 스택을 내린다.** 형제는 반드시 가짜 레포 안의 스텁이다
- ★**`docker` 스텁 없이 돌리지 마라** — 개발 머신에서 진짜 소크 DB 에 psql 이 나간다
- ★**`.soak/evidence/` 를 만들지 마라** — 덤프 경로는 `--confirm` 갈래이고 이 lane 은
  거기까지 가지 않는다. 가짜 레포 안이라도 dry-run 범위를 넘지 마라
- 공용 헬퍼 모듈 금지 · `conftest.py`·`shards.json`·`docs/**` 무변경 · DB 픽스처 금지
- 커밋하지 마라. macOS bash 3.2 · ubuntu bash 5 양쪽 통과
