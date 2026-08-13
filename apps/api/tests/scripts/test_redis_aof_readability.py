"""[BL-594] AOF 판독성 분류 규칙을 **실측 출력**으로 못박는다 ([ADR-024] C5⑸).

## 왜 fixture 가 손으로 쓴 문자열이 아닌가

이 분류기의 위험은 로직이 아니라 **redis 가 실제로 무엇을 출력하는가**에 있다. 그래서
`apps/api/tests/fixtures/bl594_aof/*.txt` 는 전부 **스크래치 컨테이너(`redis:7-alpine`,
7.4.9)에서 받아온 원문**이다. 각 파일의 출처(2026-08-05):

| 파일                       | 만든 방법                                              | 서버 실제 기동                               | 판정 |
| -------------------------- | ------------------------------------------------------ | -------------------------------------------- | ---- |
| `valid.txt`                | 키 300개 쓰고 그대로                                   | ✅                                           | ✔    |
| `last_incr_short_read.txt` | 마지막 INCR 꼬리 25바이트 절단                         | ✅ `aof-load-truncated is enabled`           | ✔    |
| `non_last_file_error.txt`  | INCR 2개 매니페스트에서 **앞** 파일 꼬리 절단          | ❌ `the truncated file is not the last file` | ✘    |
| `format_error.txt`         | 명령 헤더(`*3\r\n$3\r\nset`)를 `0xff` 16바이트로 덮음  | ❌ `Bad file format …` (프로덕션 서명)       | ✘    |
| `separator_corruption.txt` | 페이로드 뒤 `\r\n` 2바이트만 `0x0000` 으로             | ✅ **뜬다** (dbsize 300 전부 적재)           | ✘★   |
| `no_manifest.txt`          | `appendonlydir` 를 감춰 수집기가 `__missing=` 만 남김  | (측정 불가)                                  | ✘    |
| `docker_failed.txt`        | 없는 컨테이너에 `docker exec` — **빈 출력**(0바이트)   | (측정 불가)                                  | ✘    |

★**`last_incr_short_read` 와 `non_last_file_error` 는 check-aof 출력이 같은 모양이다** —
둘 다 exit 1 · `Expected to read N bytes, got M bytes` · `AOF … is not valid`. 유일한
판별자는 **지목된 파일이 매니페스트의 마지막 INCR 인가**이고, 그 하나로 기동 여부가
갈린다(✅ vs ❌). 이 두 fixture 가 규칙의 존재 이유다.

★★**`separator_corruption` 은 알려진 거짓 양성이다** — `redis-check-aof` 는 벌크 페이로드
뒤의 `\r\n` 을 검증하는데 **서버의 로더는 그 2바이트를 검증 없이 버린다**. 그래서 검사는
`is not valid` 인데 서버는 멀쩡히 뜬다(실측). 방향이 **엄격 쪽**이라 래칫에는 안전하다
(거짓 `측정불가`는 만들어도 거짓 PASS 는 못 만든다) — 그래서 통과시키지 **않는다**.
★이 표는 2026-08-05 codex 리뷰 처분 중 **정정됐다**. 그전에는 `Expected \r\n, got:` 이면
서버가 죽는다고 적혀 있었는데, 그때 죽은 건 0바이트 64개가 구분자 **말고 더** 부순
경우였다. 순수 구분자 손상만으로는 죽지 않는다.

★**이 테스트는 DB 픽스처도 컨테이너도 쓰지 않는다** — 순수 문자열 분류다.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

FIXTURES = Path(__file__).parents[1] / "fixtures" / "bl594_aof"


def _load_module() -> Any:
    """분류기 동적 import (`sys.path` 오염 회피 — tests/scripts 선례)."""
    script_path = Path(__file__).parents[2] / "scripts" / "redis_aof_readability.py"
    spec = importlib.util.spec_from_file_location("redis_aof_readability", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def aof() -> Any:
    return _load_module()


def _read(name: str) -> str:
    path = FIXTURES / f"{name}.txt"
    assert path.exists(), f"실측 캡처가 없다: {path}"
    return path.read_text()


# ── 실측 캡처 7형 동결 ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("valid", True),
        ("last_incr_short_read", True),
        ("non_last_file_error", False),
        ("format_error", False),
        ("separator_corruption", False),
        ("no_manifest", False),
        ("docker_failed", False),
    ],
)
def test_captured_outputs_classify_as_measured(aof: Any, name: str, expected: bool) -> None:
    """실제 `redis-check-aof` 출력 → 위 표의 판정과 일치해야 한다.

    ★`separator_corruption` 만 「기동 여부」와 갈린다 — 알려진 거짓 양성(모듈 docstring).
    """
    assert aof.classify(_read(name)) is expected


# ── 규칙의 각 절 ─────────────────────────────────────────────────────────────


def test_exit_code_alone_is_not_the_predicate(aof: Any) -> None:
    """★★두 캡처 모두 `__rc=1` 인데 판정은 갈린다 — 종료 코드로 재면 안 된다.

    `last_incr_short_read` 는 도는 redis 의 정상적인 미완결 꼬리다(서버가 뜬다).
    exit code 를 그대로 쓰면 멀쩡한 스택이 거짓 `측정불가` 로 떨어진다.
    """
    tail, non_last = _read("last_incr_short_read"), _read("non_last_file_error")
    assert "__rc=1" in tail and "__rc=1" in non_last
    assert aof.classify(tail) is True
    assert aof.classify(non_last) is False


def test_short_read_outside_the_last_incr_is_rejected(aof: Any) -> None:
    """★비마지막 파일 절단은 서버를 죽인다 — 「short read 면 통과」로 넓히면 fail-open.

    두 캡처의 차이는 `__last_incr` 마커뿐이다. 그 마커를 지목된 파일로 바꾸면 통과해야
    하고(규칙이 파일명을 실제로 본다는 증거), 그대로면 거절해야 한다.
    """
    non_last = _read("non_last_file_error")
    assert "__last_incr=appendonly.aof.4.incr.aof" in non_last
    assert aof.classify(non_last) is False

    as_if_last = non_last.replace(
        "__last_incr=appendonly.aof.4.incr.aof",
        "__last_incr=appendonly.aof.3.incr.aof",
    )
    assert aof.classify(as_if_last) is True


def test_format_error_is_rejected_even_without_a_defect_line(aof: Any) -> None:
    """`format error` 는 그 자체로 거절 사유다 — `0x…` 결함 줄이 없어도."""
    text = _read("format_error")
    assert "format error" in text
    assert aof.classify(text) is False


def test_a_non_short_read_defect_line_is_rejected_on_its_own(aof: Any) -> None:
    """★`format error` 문구가 **없어도** 거절된다 — 다른 절이 걸린다.

    구분자 손상 캡처에는 `format error` 줄이 없다. 거절 사유는 결함 줄(`0x…:`)이 short read
    가 아니라는 것뿐이다. 이 절이 없으면 「`format error` 만 막으면 된다」로 좁혀져
    fail-open 이 된다.
    """
    text = _read("separator_corruption")
    assert "format error" not in text
    assert "Expected \\r\\n, got:" in text
    assert aof.classify(text) is False


def test_exit_zero_still_requires_the_closing_sentence(aof: Any) -> None:
    """★빈 출력이 우연히 `__rc=0` 을 내는 갈래를 막는다."""
    assert aof.classify("__last_incr=x.aof\n__rc=0\n") is False
    assert aof.classify(_read("valid")) is True


def test_missing_rc_marker_is_never_a_pass(aof: Any) -> None:
    """★수집이 죽으면 「이상 없음」이 아니라 **못 쟀다**이다 (fail-closed).

    타임아웃·docker 실패·매니페스트 부재가 전부 여기로 온다.
    """
    assert aof.classify("") is False
    assert aof.classify(_read("no_manifest")) is False
    assert aof.classify(_read("valid").replace("__rc=0", "")) is False


# ── CLI 계약 (soak-gate.sh 가 stdout 의 1/0 만 읽는다) ───────────────────────


def test_cli_prints_one_or_zero(aof: Any, tmp_path: Path, capsys: Any) -> None:
    ok = tmp_path / "ok.txt"
    ok.write_text(_read("valid"))
    assert aof.main(["prog", str(ok)]) == 0
    assert capsys.readouterr().out.strip() == "1"

    bad = tmp_path / "bad.txt"
    bad.write_text(_read("format_error"))
    assert aof.main(["prog", str(bad)]) == 0
    assert capsys.readouterr().out.strip() == "0"


def test_cli_treats_a_missing_file_as_unmeasured(aof: Any, tmp_path: Path, capsys: Any) -> None:
    """수집기가 임시 파일을 못 남긴 갈래 — 예외가 아니라 `0` 이어야 한다."""
    assert aof.main(["prog", str(tmp_path / "nope.txt")]) == 0
    assert capsys.readouterr().out.strip() == "0"
