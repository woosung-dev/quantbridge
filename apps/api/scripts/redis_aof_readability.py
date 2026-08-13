#!/usr/bin/env python3
"""redis AOF 판독성 분류 — [BL-003] 게이트 C5⑸ `aof_ok` 의 판정 규칙 ([BL-594], [ADR-024]).

`scripts/soak-gate.sh` 가 컨테이너에서 받아온 `redis-check-aof` 원문을 읽고 **재기동
가능성**을 1/0 으로 낸다. 원문 형식은 수집기가 붙인 두 마커를 포함한다:

    __last_incr=<매니페스트의 마지막 INCR 파일명>     (매니페스트가 있을 때만)
    __missing=<경로>                                  (매니페스트가 없을 때)
    …redis-check-aof 출력…
    __rc=<redis-check-aof 종료 코드>                   (실행됐을 때만)

★★**종료 코드는 판별식이 될 수 없다** (스크래치 컨테이너 실측 2026-08-05):

| AOF 상태             | exit | 특징적인 줄                              | 서버 기동                                    | 판정 |
| -------------------- | ---- | ---------------------------------------- | -------------------------------------------- | ---- |
| 정상                 | 0    | `All AOF files and manifest are valid`   | ✅                                           | ✔    |
| 마지막 INCR 꼬리절단 | 1    | `0x…: Expected to read N bytes, got M …` | ✅ `aof-load-truncated yes` 가 자름           | ✔    |
| **비마지막** 파일    | 1    | 위와 **같은 모양**                        | ❌ `the truncated file is not the last file` | ✘    |
| 구분자 손상          | 1    | `0x…: Expected \r\n, got: …`             | ✅ **뜬다**(로더가 CRLF 를 미검증 폐기)       | ✘★   |
| 중간 손상            | 1    | `AOF … format error`                     | ❌ `Bad file format …` (프로덕션 서명)       | ✘    |

도는 redis 의 AOF 꼬리는 **언제든 미완결일 수 있다**. exit code 로 재면 멀쩡한 스택이
거짓 `측정불가` 로 떨어진다. 반대로 「exit≠0 이어도 short read 면 통과」로 넓히면
**비마지막 파일 절단**(위 3행)이 통과해 fail-open 이 된다 — 그 둘은 출력이 같은 모양이고
**유일한 판별자가 「지목된 파일이 마지막 INCR 인가」**다.

★**구분자 손상은 알려진 거짓 양성이다**(위 4행) — check-aof 는 벌크 페이로드 뒤의 `\r\n` 을
검증하는데 **서버 로더는 그 2바이트를 검증 없이 버린다**. 방향이 **엄격 쪽**이라 래칫에는
안전하므로(거짓 `측정불가`는 만들어도 거짓 PASS 는 못 만든다) 통과시키지 않는다.

그래서 규칙은 **양성 서명만 통과**(default deny)한다. 아래 `classify()` 가 정본이고
`apps/api/tests/scripts/test_redis_aof_readability.py` 가 실측 캡처 7형으로 동결한다.

★**알려진 한계** — `redis-check-aof` 는 **프레이밍만** 본다. 벌크 페이로드 안이 깨져 명령
이름이 망가지면 `valid` 라고 하는데 서버는 `Unknown command` 로 죽는다(실측). 즉 이 함수의
`True` 는 「프레이밍이 성하다」이지 「반드시 뜬다」가 아니다 — [BL-594] 후속.

★backend 의존성을 쓰지 않는다. 게이트가 **시스템 python3** 로 부른다
(`soak_gate_predicate.py` 와 같은 선례).
"""

from __future__ import annotations

import pathlib
import re
import sys

VALID_TAIL = "All AOF files and manifest are valid"

_RC = re.compile(r"^__rc=(\d+)$", re.M)
_LAST_INCR = re.compile(r"^__last_incr=(.*)$", re.M)
_INVALID_FILE = re.compile(r"^AOF (\S+) is not valid\.", re.M)
_DEFECT = re.compile(r"^0x\s+[0-9a-fA-F]+:\s*(.*)$", re.M)
_SHORT_READ = re.compile(r"Expected to read \d+ bytes, got \d+ bytes")


def classify(text: str) -> bool:
    """AOF 가 판독 가능한가 — 즉 지금 재기동하면 redis 가 뜨는가.

    판정 불가(수집 실패·마커 부재·빈 출력)는 전부 `False` 다. 「못 쟀다」와 「깨졌다」를
    구분하지 않지만 **둘 다 「재기동 내성을 증명하지 못했다」**이고 방향은 fail-closed 다.
    """
    rc = _RC.search(text)
    if rc is None:
        # docker exec 실패 · 매니페스트 부재 · 빈 출력 — 잴 수 없었다.
        return False

    if int(rc.group(1)) == 0:
        # ★exit 0 만으로 통과시키지 않는다. 종결 문장을 함께 요구한다 —
        #   빈 출력이 우연히 0 을 내는 갈래를 막는다.
        return VALID_TAIL in text

    # 결함이 **마지막 INCR 파일의 꼬리 절단 하나뿐**일 때만 통과. 그 외 전부 거절.
    #   ⑴ 「유효하지 않다」고 지목된 파일이 정확히 하나이고, 그게 매니페스트의 마지막 INCR
    #   ⑵ 결함 줄(`0x…:`)이 전부 short read (= EOF 도달) 이고, 하나 이상 있다
    #   ⑶ 어디에도 format error 가 없다
    # redis 의 기동 규칙(`aof-load-truncated yes` 는 **마지막** 파일의 EOF 절단만 봐준다)을
    # 그대로 옮긴 것이다. 그보다 넓히면 fail-open 이 된다.
    last_incr = _LAST_INCR.search(text)
    tail_name = last_incr.group(1).strip() if last_incr else ""
    invalid = _INVALID_FILE.findall(text)
    defects = _DEFECT.findall(text)
    short_reads = [d for d in defects if _SHORT_READ.match(d)]
    return (
        tail_name != ""
        and invalid == [tail_name]
        and len(defects) > 0
        and len(short_reads) == len(defects)
        and "format error" not in text
    )


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: redis_aof_readability.py <captured-output-file>", file=sys.stderr)
        return 2
    path = pathlib.Path(argv[1])
    text = path.read_text() if path.exists() else ""
    print("1" if classify(text) else "0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
