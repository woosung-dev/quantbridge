# Step 0: notify-seam-and-token-silence

## 읽어야 할 파일

- `tools/scripts/lib/notify-telegram.sh` — **이번 테스트의 대상** (76줄 전량, 절반이 계약 주석)
- `tools/scripts/soak-watch.sh:105-118` — 이 lib 를 쓰는 호출부 하나(`_notify` 래퍼)
- `apps/api/src/common/telegram_alert.py:52-65` — 같은 이유로 존재하는 `_safe_err`(파이썬 쪽 짝)
- `apps/api/tests/scripts/test_soak_observe.py` — PATH 스텁 관용구(`_write_curl_stub`)

## 배경

[BL-768] 에서 **디스크 경보와 소크 감시가 같은 알림 배선을 쓰게 되면서** `soak-watch.sh` 안에
살던 `_notify()` 를 이 lib 로 뺐다. 헤더가 이유를 적고 있다 — 복제하면 토큰 취급 규칙이
두 벌이 되고, **한쪽만 고쳐지는 순간 조용히 새는 쪽이 생긴다.**

★**계약의 핵심은 「URL 을 절대 출력하지 않는다」** 다. 텔레그램 API 는 **경로에 봇 토큰**이
들어간다(`/bot<TOKEN>/sendMessage`) — 실패 메시지에 URL 을 실으면 그 순간 토큰이 로그·
journalctl·CI 아티팩트로 샌다. 지금 이 계약을 재는 것은 **아무것도 없다.**

`QB_NOTIFY_CMD` seam 은 **하네스가 실제 텔레그램을 쏘지 않게 하는 유일한 경로**다.
그 seam 자체가 깨지면 테스트가 진짜 메시지를 보내게 된다.

## 작업

`apps/api/tests/scripts/test_notify_telegram_lib.py` 를 신설한다.

### 호출 방식 (이 lane 의 유일한 방식)

source 전용 라이브러리다. 진짜 파일을 그대로 소싱해 함수 하나를 부른다. **bash 로 부른다**
(헤더 계약이 「bash 전용」 — `local` 을 쓴다).

```python
import os, subprocess
from pathlib import Path

LIB = Path(__file__).resolve().parents[4] / "tools" / "scripts" / "lib" / "notify-telegram.sh"


def notify(body: str, env: dict[str, str], path_prepend: Path | None = None):
    e = {**os.environ, **env}
    if path_prepend is not None:
        e["PATH"] = f"{path_prepend}:{e['PATH']}"
    return subprocess.run(
        ["bash", "-c", 'set -uo pipefail; . "$1"; qb_notify_telegram "$2"', "x", str(LIB), body],
        capture_output=True, text=True, timeout=60, env=e,
    )
```

★**호출자는 `set -uo pipefail` 아래에 있다고 가정한다**(헤더 계약) — 그대로 재현해라.

### 스텁 두 개를 `tmp_path/bin` 에 놓는다

- **`curl`** — argv 전량을 파일에 기록하고 `CURL_STUB_CODE`(기본 `200`)를 stdout 에 찍는다.
  대상은 `--write-out '%{http_code}'` 의 출력을 명령 치환으로 받는다
- **`timeout`** — 첫 인자(초)를 버리고 나머지를 그대로 실행한다(`shift; exec "$@"`).
  ★**macOS 에는 `timeout` 이 없다** — 스텁 없이 재면 이 lane 이 로컬에서만 다른 갈래를 탄다

### 최소한 이 여섯을 덮어라 (케이스 ≥6)

1. **`QB_NOTIFY_ENV_FILE` 미지정 → rc=1** + stderr 에 `QB_NOTIFY_ENV_FILE` 이 실린다.
   ★이때 **curl 스텁이 한 번도 안 불렸음**을 기록 파일 부재로 함께 단언해라
2. **env 파일 부재 → rc=1** + stderr 에 **그 경로**가 실린다
3. **토큰/챗 ID 공백 → rc=1** — 파일은 있는데 `TELEGRAM_BOT_TOKEN=` 이 비었을 때.
   ★`TELEGRAM_CHAT_ID` 만 빈 경우도 같은 축으로 한 줄(둘 다 `-z` 검사 대상이다)
4. **`QB_NOTIFY_CMD` seam** — 본문이 **stdin 으로** 그 명령에 들어가고(파일로 캡처해 대조),
   ★**그 명령의 종료 코드가 그대로 반환**된다(rc=0 과 rc≠0 둘 다 재라).
   ★그리고 **seam 이 설정되면 env 검사 갈래를 아예 안 탄다** — `QB_NOTIFY_ENV_FILE` 이
   비어 있어도 rc=0 이어야 한다(코드 순서상 seam 이 먼저다)
5. **HTTP 판정** — 스텁 코드 `200` → rc=0 · `404` → rc=1 이고 stderr 에 `404` 가 실린다 ·
   스텁이 아무것도 안 찍으면(빈 코드) rc=1. ★`--fail` 이 아니라 **상태 코드 직접 판정**이라
   400/404 가 같은 축으로 잡힌다는 것이 이 함수의 설계다
6. ★★**음성 대조 — 토큰이 새지 않는다.** env 파일에 눈에 띄는 토큰
   (예: `TELEGRAM_BOT_TOKEN=SEKRET-DO-NOT-LEAK-0000`)을 넣고 **실패 갈래**(스텁 404)를
   태운 뒤, **stdout·stderr 어디에도** 그 문자열과 `api.telegram.org` 가 **없음**을 단언해라.
   ★성공 갈래에서도 같은 단언을 한 줄 더 해라 — 새는 자리는 실패 메시지만이 아니다

★**양성 대조를 함께 넣어라** — 6번이 「출력이 비어서」 통과하면 판별력이 0 이다.
같은 케이스에서 **stderr 가 비어 있지 않고 `HTTP 404` 를 포함**함을 먼저 단언한 뒤
토큰 부재를 단언해라.

★**curl argv 계약도 한 줄 재라** — 기록된 argv 에 `--output`·`/dev/null`·
`--data-urlencode`(chat_id·text)·`--max-time` 이 있는지. `--output /dev/null` 이 빠지면
응답 본문이 로그로 나온다.

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/scripts/test_notify_telegram_lib.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/scripts/test_notify_telegram_lib.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 6
cd apps/api && uv run ruff check tests/scripts/
```

★두 번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 rc=4 (red) 다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. ★**진짜 네트워크가 나가지 않았는지 확인해라** — 모든 케이스가 `QB_NOTIFY_CMD` seam 이거나
   PATH 스텁 `curl` 을 탄다. 스텁 없이 도는 케이스가 하나라도 있으면 그것은 사고다.
3. 사람 개입이 필요하면 `status:"blocked"` + `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- `tools/scripts/lib/notify-telegram.sh` **수정 금지.** 결함은 `@pytest.mark.xfail(strict=True)`
- ★**진짜 텔레그램 API 를 부르지 마라.** 이유: 이 레포의 봇 토큰이 `.env.local` 에 실재하고,
  테스트가 알림을 쏘면 운영 채널이 오염된다. `api.telegram.org` 를 **테스트 코드에 URL 로
  적지도 마라** — 6번 음성 대조가 그 문자열을 찾는다(자기 테스트가 자기 단언을 깬다)
- 레포의 `apps/api/.env.local` 을 **읽지도 쓰지도 마라** — 모든 크레덴셜은 `tmp_path` 의
  가짜 파일이다. ★**CI 엔 그 파일이 없다**
- 공용 헬퍼 모듈 금지 · `conftest.py`·`shards.json`·`docs/**` 무변경 · DB 픽스처 금지
- 커밋하지 마라. macOS bash 3.2 · ubuntu bash 5 양쪽 통과
