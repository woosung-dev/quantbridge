# Step 1: watch-freshness-and-state

## 읽어야 할 파일

- `tools/scripts/soak-watch.sh:241-306` — `_installed_execstart` · `_check_freshness` · `_status`
- `tools/scripts/soak-watch.sh:126-200` — `_install` 이 **굽는 유닛 파일 형식**(테스트가 그 모양을
  손으로 만들어야 한다). ★`--install` 을 실행해서 만들지 마라 — 실행자의 진짜 systemd 를 건드린다
- `apps/api/tests/scripts/test_soak_watch.py` — step 0 이 만든 파일. **여기에 덧붙인다**

## 배경

「타이머가 waiting」은 건강 신호가 아니다. [BL-737] 사고 41시간 동안 **타이머는 정상 waiting
이었고 서비스만 30분마다 rc=127 로 죽었다.** 그래서 `--status` 가 재는 것은 타이머가 아니라
**설치된 유닛의 `ExecStart` 가 지금 이 파일을 가리키는가**다. 그리고 알람 유닛(`OnFailure=`)이
없으면 그 죽음이 다시 안 보이므로 그것도 같은 축으로 잰다.

상태 파일 쪽 계약 하나가 실제 사고로 고쳐졌다 — **heartbeat 날짜는 「어떤 알림이든 실제로
나간 날」 전진**한다. heartbeat 갈래에서만 전진시켰더니 변화 알림 바로 다음 주기에 heartbeat 가
또 나갔다. **전송에 실패한 날은 전진시키지 않는다**(그날 소식이 실제로 0이므로).

## 작업

step 0 의 파일에 덧붙인다. **누적 케이스 ≥12.**

### 신선도 — `XDG_CONFIG_HOME` 을 `tmp_path` 로 주고 유닛 파일을 손으로 쓴다

`_installed_execstart` 는 `${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/dev.quantbridge.soak-watch.service`
에서 `^ExecStart=/bin/bash (.*)$` 를 뽑는다. 알람 유닛은
`dev.quantbridge.soak-watch-alarm.service` 이고 그 `ExecStart` 안의 `. "<env 파일>"` 경로를 뽑는다.
**두 줄의 정확한 모양은 `_install` 본문을 읽고 맞춰라.**

★`--status` 는 앞부분에서 `systemctl` 을 부를 수 있다(있으면 타이머 줄을 찍는다).
**타이머 절은 단언 대상이 아니다** — OS 마다 다르다. 재는 것은 `── 설치본 신선도 ──`
아래의 줄들과 **종료 코드**다.

### 최소한 이 축들을 덮어라

1. **유닛 부재 → rc=1** + 「설치된 유닛이 없다」
2. **`ExecStart` 가 없는 파일을 가리킴 → rc=1** + 「rc=127 로 죽는다」 ★[BL-737] 그 자체
3. **`ExecStart` 가 다른(실재하는) 파일 → rc=1** + 「이 파일이 아니다」 +
   **설치본·현재본 두 경로가 모두 출력**된다(사람이 이것만 보고 재설치한다)
4. ★**정상 — `ExecStart` 가 가짜 레포의 그 파일 + 알람 유닛 + env 파일 실재 → rc=0**
   그리고 `✓` 줄 둘이 나온다. **이 양성 대조가 없으면 「항상 rc=1」인 판정기도 1~3을 통과한다**
5. **알람 유닛 부재 → rc=1** + 「watch 가 죽어도 조용하다」 취지
   (★`ExecStart` 는 정상인 상태에서 재라 — 실패원을 하나만 남긴다)
6. **알람 유닛의 env 파일이 없다 → rc=1** (파싱은 되는데 그 경로가 부재)

### 상태 파일 왕복 — ★`date` 를 스텁하지 말고 **왕복**으로 재라

자정 근처에 파이썬이 계산한 오늘과 셸이 계산한 오늘이 갈리면 간헐 red 가 된다.
**두 번 실행해 앞 실행이 쓴 파일을 뒤 실행이 읽게** 해라.

7. ★**heartbeat 는 하루 1회** — 같은 지문으로 **연속 2회** 실행한다(둘 다 dry-run 아님,
   `QB_SOAK_NOTIFY_CMD` 는 성공 명령). ⑴ 1회차는 발화하고 `HEARTBEAT_DATE` 가 상태 파일에
   기록된다 ⑵ **2회차는 캡처 파일이 늘지 않는다**(무발화)
8. ★**전송 실패 시 날짜가 전진하지 않는다** — `QB_SOAK_NOTIFY_CMD` 를 실패하는 명령으로 주면
   ⑴ 스크립트 rc=1 ⑵ 상태 파일의 `HEARTBEAT_DATE` 가 **이전 값 그대로**다.
   ★그 뒤 같은 지문으로 성공 명령으로 한 번 더 돌리면 **이번엔 발화**한다(그날 소식이 0이었으므로)
9. **과거 날짜** — 상태 파일에 `HEARTBEAT_DATE=1970-01-01` 을 넣고 지문은 동일하게 두면
   heartbeat 가 발화한다(머리 🟢). 리터럴 과거 날짜라 시계와 무관하다
10. **상태 파일 형식** — 갱신 후 파일이 `FINGERPRINT=` · `DISQ=` · `HEARTBEAT_DATE=` **3줄**이고
    ★**`.` 로 소싱 가능한 형태에 기대지 않는다**(대상은 `sed` 로 파싱한다. 값에 공백·`|` 가 있어도 읽힌다)

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/scripts/test_soak_watch.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/scripts/test_soak_watch.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 12
cd apps/api && uv run ruff check tests/scripts/
```

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. ★**step 0 의 케이스를 지우지 마라** — 누적 ≥12 는 step 0 의 ≥7 을 포함한 수다.
3. ★**`~/.config/systemd/user/` 에 파일이 생기지 않았는지 확인해라** — 전부 `XDG_CONFIG_HOME`
   을 `tmp_path` 로 준 상태여야 한다.

## 금지사항

- `tools/scripts/soak-watch.sh` **수정 금지**(결함은 `xfail(strict=True)`)
- ★**`--install`/`--uninstall` 실행 금지.** 이유: `systemctl --user daemon-reload`·
  `enable --now` 를 부르고 **게이트 타이머까지 끈다**. 유닛 파일은 손으로 쓴다
- ★**`systemctl` 을 스텁하지 마라** — `--status` 는 그것이 없어도 신선도 판정을 끝까지 한다.
  스텁을 놓으면 OS 별 갈래가 하나 더 생겨 단언이 흔들린다
- 실제 텔레그램 금지 · 진짜 게이트 호출 금지 · 레포 `.soak/` 무접촉
- 공용 헬퍼 모듈 금지 · `conftest.py`·`shards.json`·`docs/**` 무변경 · DB 픽스처 금지
- 커밋하지 마라. macOS bash 3.2 · ubuntu bash 5 양쪽 통과
