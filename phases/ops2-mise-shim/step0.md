# Step 0: shim-path-pin

## 읽어야 할 파일

- `tools/scripts/lib/mise-shim-path.sh` — **이번 테스트의 대상** (46줄 전량, 대부분이 근거 주석)
- `docs/adr/036-tool-version-ssot-mise.md` — 이 파일이 집행하는 결정
- `apps/api/tests/scripts/test_assert_main_checkout.py` — PATH 를 좁혀서 재는 선례(케이스 5)

## 배경

[ADR-036] 이 도구 버전의 SSOT 를 루트 `mise.toml` 하나로 모았지만 **게이트가 안 따라왔다**
([BL-785]). `tools/scripts/` 의 스크립트는 사용자 셸에서 상속한 PATH 로 돌고, 거기 mise 가
걸려 있는지는 셸 초기화에 달려 있어 **실제로 갈렸다** — 2026-08-16 실측에서 레포 루트가
corepack 폴백 `pnpm 8.15.9` 를 썼고, `pnpm-lock.yaml` 이 `lockfileVersion 9.0` 이라
그 셸에서는 `frozen-lockfile` 이 red 였다. ★**그 증상은 「내 PR 이 lockfile 을 깼다」로 오인된다.**

이 함수의 설계 결정 셋이 전부 주석으로만 지켜지고 있다:

- **조용히 넘어가지 않는다** — shim 디렉터리가 없으면 경고 2줄 + rc=1(호출부가 무시할 수는
  있지만, 「어느 버전으로 돌았는지 모르는 채 초록/빨강을 낸다」를 최소한 말은 한다)
- **조건 없이 앞에 붙인다** — 「이미 PATH 에 있으면 건너뛴다」로 짜면 **낡은 도구가 shim 보다
  앞에 선 바로 그 상황**에서 아무것도 안 하게 된다. 고치려는 병이 정확히 그것이다
- **mise 를 실행하지 않는다** — shim 은 자기완결 바이너리라 PATH 에 `mise` 가 없어도 돈다

## 작업

`apps/api/tests/scripts/test_mise_shim_path.py` 를 신설한다.

### 호출 방식 (이 lane 의 유일한 방식)

source 전용이고 **부작용이 `PATH` 하나뿐**이라, 함수의 stdout/stderr 를 파일로 갈라 받고
**호출 후의 `PATH` 를 프로세스 stdout 으로** 돌려받는다.

```python
SCRIPT = 'set -uo pipefail; . "$1"; qb_pin_tool_path > "$2" 2> "$3"; rc=$?; printf "%s\\n%s\\n" "$rc" "$PATH"'
# subprocess.run(["bash", "-c", SCRIPT, "x", str(LIB), str(out), str(err)], env=..., ...)
# stdout 첫 줄 = rc · 둘째 줄 = 호출 후 PATH · out/err 파일 = 함수 자신의 출력
```

`LIB = Path(__file__).resolve().parents[4] / "tools" / "scripts" / "lib" / "mise-shim-path.sh"`.

env 는 **`HOME` 과 `MISE_DATA_DIR` 과 `PATH` 를 전부 `tmp_path` 로 고정**해라 —
실행자의 진짜 mise 설치가 결과를 가르면 CI 와 로컬이 다른 것을 잰다.

### 최소한 이 다섯을 덮어라 (케이스 ≥5)

1. **shim 디렉터리 부재 → rc=1** · stderr **2줄**(첫 줄에 그 경로, 둘째 줄에
   「CI 와 비교하지 마라」 취지) · ★**stdout 0바이트** · ★**PATH 무변경**(호출 전후 동일 문자열)
2. **shim 디렉터리 존재 → rc=0** · ★**PATH 의 첫 항목이 정확히 그 디렉터리** ·
   stdout·stderr 둘 다 0바이트
3. ★**조건 없이 앞에 붙인다** — 호출 전 PATH 를 `"<낡은 도구 디렉터리>:<shims>:<나머지>"` 로
   주고도 호출 후 **첫 항목이 shims** 임을 단언해라. 「이미 있으면 건너뛴다」 구현이면
   여기서 낡은 디렉터리가 첫 항목으로 남는다 — **이 케이스가 이 lane 의 판별력이다**
4. **`MISE_DATA_DIR` 우선** — `HOME` 은 shim 이 **없는** 곳을 가리키고 `MISE_DATA_DIR` 은
   **있는** 곳을 가리킬 때 rc=0 이고 PATH 첫 항목이 `MISE_DATA_DIR/shims` 다.
   그 반대(`MISE_DATA_DIR` 미설정 + `HOME/.local/share/mise/shims` 존재)도 한 줄
5. ★**mise 를 실행하지 않는다** — PATH 에 실행 가능한 `mise` 스텁을 놓고(호출되면 파일을
   남기게), 성공 갈래를 태운 뒤 **그 파일이 생기지 않았음**을 단언해라.
   「PATH 를 좁혀도 돈다」보다 강한 단언이다(전자는 부재로만 참이다)

### ★[BL-791] gap 고정 — `xfail(strict=True)` 한 건

[BL-791](DEFERRED, P3)이 적어 둔 결함: 이 함수는 shim 디렉터리의 **존재만** 보므로
**빈/부분 설치된 `shims/`** 는 성공으로 처리되고, 그 안에 `pnpm` shim 이 없으면 셸이 다음
PATH 항목의 구버전으로 조용히 폴백한다.

```python
@pytest.mark.xfail(strict=True, reason="[BL-791] 내용물 미검증 — fail 정책 결정 전이라 현재는 rc=0")
def test_empty_shims_dir_is_rejected(...):
    # 빈 디렉터리를 shims 로 주고 rc == 1 을 기대한다 (지금은 rc=0 이라 xfail)
```

★**이 lane 은 [BL-791] 을 고치지 않는다.** 처방(fail-closed 전환)은 「CI 로그에 그 경고가
있었는지」 확인이 선행이라고 원장이 적어 뒀고 그 판단은 이 회차 범위 밖이다. 여기서 하는
일은 **누가 고치는 순간 XPASS 로 red 가 나게 못박는 것**이다.

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/scripts/test_mise_shim_path.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/scripts/test_mise_shim_path.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 5
cd apps/api && uv run ruff check tests/scripts/
```

★두 번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 rc=4 (red) 다.
★`xfail` 은 pytest 에서 **실패로 세지 않는다** — 첫 AC 는 `N passed, 1 xfailed` 로 rc=0 이다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. ★**`xfail` 이 `strict=True` 인지 확인해라** — 아니면 고쳐도 조용히 지나간다.
3. `summary` 에 [BL-791] gap 을 어떤 이름의 테스트로 고정했는지 한 줄 남겨라.

## 금지사항

- `tools/scripts/lib/mise-shim-path.sh` **수정 금지.** [BL-791] 처방을 여기서 집행하지 마라 —
  이유: fail 정책을 조이면 mise 없는 러너에서 게이트가 **전부** 죽는다. 그 판단은 CI 로그 확인이 선행이다
- ★**실행자의 진짜 mise 설치(`$HOME/.local/share/mise`)를 읽지 마라** — env 3종을
  `tmp_path` 로 고정한다. 안 그러면 로컬은 초록, CI 는 빨강(또는 그 반대)이 된다
- `mise` 를 **진짜로 실행하지 마라** — 5번은 스텁이고 호출 0건이 단언 대상이다
- 공용 헬퍼 모듈 금지 · `conftest.py`·`shards.json`·`docs/**` 무변경 · DB 픽스처 금지
- 커밋하지 마라. macOS bash 3.2 · ubuntu bash 5 양쪽 통과
