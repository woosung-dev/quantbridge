# Step 0: watch-fingerprint-and-notify

## 읽어야 할 파일

- `tools/scripts/soak-watch.sh` — **이번 테스트의 대상**. 특히 `:314-441`(게이트 호출 → 지문
  추출 → 알림 판단 → 발화 → 상태 갱신)
- `apps/api/tests/scripts/test_soak_observe.py:19-31` — `tmp_path` 가짜 레포 관용구(`_fake_repo`)
- `docs/status.md` §📌 소크 운영 상비 참조 8번 — 이 감시자의 운영 계약

## 배경

[BL-737] — 2026-08-13 재배치([ADR-029])가 이 파일을 `scripts/` → `tools/scripts/` 로 옮기자
서버의 systemd 유닛은 **41시간 동안 30분마다 `rc=127` 로 죽었고 알림은 0줄**이었다.
그 사이 소크 사망 2건을 아무도 몰랐다. **감시자는 자기 죽음을 알릴 수 없다.**

그 사고가 만든 축이 둘이고(`OnFailure` 알람 유닛 · `--status` 설치본 신선도), 그것을 재던
`soak-watch-test.sh` 는 [ADR-037] 이 철거했다. 지금 이 파일의 테스트는 0건이다.

이 step 이 재는 것은 **판단부**다:

- **지문** = `VERDICT|DISQ|WINDOWS|C5` 4필드. 변화하면 알린다
- ★**크래시 판별자는 종료 코드가 아니라 `C1` 앵커 줄의 유무**다 — 게이트는 FAIL 일 때도
  rc≠0 을 낼 수 있어 rc 로는 둘을 못 가른다. 「게이트가 죽었다」를 「소크가 죽었다」로
  보고하면 운영자가 잘못된 곳을 판다
- **heartbeat** 는 하루 1회이고, **어떤 알림이든 실제로 나간 날** 날짜를 전진시킨다
  (heartbeat 갈래에서만 전진시켰더니 변화 알림 바로 다음 주기에 heartbeat 가 또 나갔다)

## 작업

`apps/api/tests/scripts/test_soak_watch.py` 를 신설한다.

### 호출 방식 (이 lane 의 유일한 방식)

`GATE="${SCRIPT_DIR}/soak-gate.sh"` 는 **env 로 못 바꾼다.** 그래서 대상을 `tmp_path` 아래
가짜 레포에 복사하고 **그 옆에 가짜 `soak-gate.sh` 를 둔다.**

```python
def _fake_repo(tmp_path: Path) -> Path:
    scripts = tmp_path / "tools" / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    copied = scripts / "soak-watch.sh"
    shutil.copy2(REAL, copied)            # REAL = parents[4]/"tools"/"scripts"/"soak-watch.sh"
    return copied                          # 가짜 게이트는 scripts/soak-gate.sh 로 따로 쓴다
```

env 로 준다: `QB_SOAK_WATCH_STATE`(상태 파일) · `QB_SOAK_ENV_FILE`(가짜 크레덴셜) ·
`QB_SOAK_NOTIFY_CMD`(알림 캡처 seam) · `QB_NOTIFY_LIB`(**진짜 `lib/notify-telegram.sh` 절대경로** —
가짜 레포엔 lib 가 없다) · `QB_SOAK_GATE_TIMEOUT`.

★**`timeout` 을 PATH 스텁으로 놔라** — 대상은 `timeout "${GATE_TIMEOUT}" bash "${GATE}"` 로
게이트를 부르는데 **macOS 에는 `timeout` 이 없다**. 스텁 없이 재면 로컬과 CI 가 다른 갈래를 탄다.
스텁은 첫 인자(초)를 버리고 나머지를 그대로 실행한다.

### 가짜 게이트가 내야 하는 앵커 (대상의 `sed` 가 보는 것 그대로)

```
  ✓ C1 24h 창 3개            ← 크래시 판별자. `^  [✓✗] C1 ` 모양이어야 한다
판정: PASS                    ← `^판정: [A-Z]+`
  ✓ C3 실격 사건  0건
  귀속 창 2개: …
  ✓ C5 측정 무결  ⑴=✓ ⑵=✓
══ [BL-003] …                 ← 본문 꼬리에 실리는 구간
```

★**앵커를 코드에서 베끼지 말고 위 모양을 그대로 쓰되, 대상 파일의 `sed` 식을 먼저 읽고
맞춰라.** 특히 `귀속 창` 줄은 **선행 공백 2칸**이 있어야 매치된다.

### 최소한 이 일곱을 덮어라 (케이스 ≥7)

1. **첫 실행(상태 파일 없음) · `--dry-run`** — 지문이 `PASS|0|2|…` 4필드이고 출력에
   「감시 시작」 취지가 실린다. ★**dry-run 은 상태 파일을 쓰지 않는다**(파일 부재 단언)
2. ★**크래시 — `C1` 앵커가 없으면 지문이 `CRASH`** 이고 본문 머리가 **크래시**다.
   ★**`FAIL` 로 보고하지 않는다**를 함께 단언해라(「게이트가 죽었다」 ≠ 「소크가 죽었다」)
3. ★★**rc 는 판별자가 아니다** — 두 줄을 나란히 재라:
   ⑴ 게이트 스텁 **rc=0 인데 C1 앵커 없음** → `CRASH`
   ⑵ 게이트 스텁 **rc=1 인데 앵커·판정 정상** → **CRASH 아님**(지문 4필드)
   **이 대조가 이 케이스의 판별력이다**
4. **`판정: FAIL`** → 사유에 「판정 FAIL」이 실린다
5. **실격 증가** — 상태 파일에 `DISQ=1` 을 미리 넣고 게이트가 `3건` 을 내면 사유에
   `+2` 와 `1 → 3` 이 실린다. ★**감소·동일에는 발화하지 않는다**를 한 줄 더
6. **창 0** → 「활성 귀속 창 0」 · **`C5` 에 `=✗`** → 「C5 측정 무결 위반」 (두 축 각각)
7. ★**무발화** — 상태 파일의 `FINGERPRINT` 가 이번 지문과 같고 `HEARTBEAT_DATE` 가 **오늘**
   이면 아무 사유도 없다. `--dry-run` 출력이 「무발화」 갈래임을 단언해라
8. ★**발화 경로 — `QB_SOAK_NOTIFY_CMD` seam 이 본문을 stdin 으로 받는다.**
   dry-run 이 **아닌** 실행에서 캡처 파일의 첫 줄이 머리(🔴/🟠/🟢 중 하나)임을 단언해라

★**양성 대조** — 1·7 이 「출력이 비어서」 통과하지 않도록, 각 케이스에서 **게이트 스텁이
실제로 불렸음**(호출 기록 파일)을 함께 단언해라.

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/scripts/test_soak_watch.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/scripts/test_soak_watch.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 7
cd apps/api && uv run ruff check tests/scripts/
```

★두 번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 rc=4 (red) 다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. ★**진짜 `.soak/`·진짜 게이트·진짜 텔레그램에 닿지 않았는지 확인해라** — 모든 케이스가
   가짜 레포 + `QB_SOAK_NOTIFY_CMD` seam 을 탄다.
3. `summary` 에 가짜 게이트 출력의 **앵커 5줄 모양**을 남겨라 — step 1 이 그것을 재사용한다.

## 금지사항

- `tools/scripts/soak-watch.sh` **수정 금지.** 결함은 `@pytest.mark.xfail(strict=True)`
- ★**진짜 `tools/scripts/soak-gate.sh` 를 부르지 마라.** 이유: 게이트는 `.soak/` 표본과
  phantom 아카이브를 **쓰고**, 도는 데 수백 초가 걸린다. 반드시 가짜 레포 안의 스텁이다
- ★**`--install`/`--uninstall` 을 실행하지 마라** — `systemctl --user` 로 **실행자의 진짜
  타이머**를 건드린다(게이트 타이머를 끄기까지 한다). 신선도 판정은 step 1 이 **파일만** 읽어서 한다
- 실제 텔레그램 금지 · 레포의 `apps/api/.env.local` 무접촉(**CI 엔 없다**)
- 공용 헬퍼 모듈 금지 · `conftest.py`·`shards.json`·`docs/**` 무변경 · DB 픽스처 금지
- 커밋하지 마라. macOS bash 3.2 · ubuntu bash 5 양쪽 통과
