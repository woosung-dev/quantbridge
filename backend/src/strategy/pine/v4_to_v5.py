"""Pine Script v4 → v5 자동 변환 전처리기.

파서가 v5만 처리하도록, v4 코드를 v5로 정규화한다.
주요 변환:
  - //@version=4 → //@version=5
  - ta.* 네임스페이스 없는 함수 호출에 ta. 프리픽스 추가
  - input(N) 호출 → input.int/float/bool/source 변환
지원 불가 v4 기능(security, tickerid 등)은 PineUnsupportedError 발생.
"""
from __future__ import annotations

import re
from typing import Literal

from src.strategy.pine.errors import PineUnsupportedError

# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------

# ta.* 네임스페이스로 이동된 v4 함수 목록
_TA_FUNCTIONS: frozenset[str] = frozenset(
    {
        "sma",
        "ema",
        "wma",
        "dema",
        "tema",
        "vwma",
        "smma",
        "rma",
        "hma",
        "zlema",
        "rsi",
        "macd",
        "atr",
        "bb",
        "bbw",
        "cci",
        "cmo",
        "cog",
        "correlation",
        "cross",
        "crossover",
        "crossunder",
        "highest",
        "highestbars",
        "lowest",
        "lowestbars",
        "mfi",
        "mom",
        "obv",
        "percentrank",
        "pivothigh",
        "pivotlow",
        "range",
        "roc",
        "sar",
        "stoch",
        "supertrend",
        "swma",
        "tr",
        "tsi",
        "valuewhen",
        "variance",
        "vwap",
        "wpr",
        "change",
        "falling",
        "rising",
        "barssince",
        "cum",
        "dev",
        "linreg",
        "median",
        "mode",
        "percentile_linear_interpolation",
        "percentile_nearest_rank",
        "alma",
        "dmi",
        "ichimoku",
        "kc",
        "kcw",
    }
)

# v4에서 지원 불가한 기능 (함수명 또는 식별자)
_UNSUPPORTED_V4_FEATURES: frozenset[str] = frozenset(
    {
        "security",
        "tickerid",
        "request.security_lower_tf",
    }
)

# //@version=N 헤더 패턴
_VERSION_HEADER_RE = re.compile(r"^//@version\s*=\s*(\d+)", re.MULTILINE)

# 문자열 리터럴 (단/쌍 따옴표) 마스킹용 패턴
_STRING_LITERAL_RE = re.compile(r'("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')')


# input() 호출 패턴 — 첫 번째 인수 캡처
_INPUT_CALL_RE = re.compile(r"\binput\s*\(([^)]*)\)")

# ta.* 프리픽스 없는 함수 호출 패턴 — 동적으로 생성
def _build_ta_func_re() -> re.Pattern[str]:
    """_TA_FUNCTIONS에서 정규식 패턴을 빌드한다."""
    # 이미 ta. 프리픽스가 붙은 경우는 제외하는 negative lookbehind 사용
    funcs = "|".join(sorted(_TA_FUNCTIONS, key=len, reverse=True))
    return re.compile(rf"(?<!ta\.)(?<!\w)({funcs})(?=\s*\()")


_TA_FUNC_RE: re.Pattern[str] = _build_ta_func_re()


# ---------------------------------------------------------------------------
# 공개 API
# ---------------------------------------------------------------------------


def detect_version(source: str) -> Literal["v4", "v5"]:
    """소스 코드에서 Pine Script 버전을 감지한다.

    //@version=4 → 'v4', //@version=5 → 'v5', 헤더 없음 → 'v5' (기본값).
    """
    match = _VERSION_HEADER_RE.search(source)
    if match:
        version_num = match.group(1)
        if version_num == "4":
            return "v4"
    return "v5"


def normalize(source: str) -> str:
    """v4 Pine Script 소스를 v5로 정규화한다.

    v5 코드는 변경 없이 반환한다.
    지원 불가 v4 기능이 포함된 경우 PineUnsupportedError를 발생시킨다.

    Args:
        source: Pine Script 소스 코드 (v4 또는 v5).

    Returns:
        v5 호환 소스 코드.

    Raises:
        PineUnsupportedError: security(), tickerid 등 v4 전용 기능 사용 시.
    """
    # v5는 그대로 반환
    if detect_version(source) == "v5":
        return source

    # 지원 불가 기능 사전 검사
    _check_unsupported_features(source)

    # 라인별 변환
    lines = source.splitlines(keepends=True)
    result_lines = [_convert_line(line) for line in lines]
    return "".join(result_lines)


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------


def _check_unsupported_features(source: str) -> None:
    """지원 불가 v4 기능이 있으면 PineUnsupportedError를 발생시킨다."""
    for feature in _UNSUPPORTED_V4_FEATURES:
        # 문자열/주석 내부 제외하고 검사
        for lineno, line in enumerate(source.splitlines(), start=1):
            code_part, _ = _split_code_and_comment(line)
            masked = _mask_string_literals(code_part)
            # feature 식별자 패턴 검사
            pattern = re.compile(rf"(?<!\w){re.escape(feature)}(?!\w)")
            if pattern.search(masked):
                raise PineUnsupportedError(
                    f"'{feature}'은(는) v4 전용 기능으로 자동 변환이 지원되지 않습니다.",
                    feature=feature,
                    category="v4_migration",
                    line=lineno,
                )


def _convert_line(line: str) -> str:
    """한 줄을 v4 → v5로 변환한다.

    주석과 문자열 리터럴 내부는 변환하지 않는다.
    """
    # 버전 헤더 변환
    if _VERSION_HEADER_RE.match(line.rstrip()):
        return _VERSION_HEADER_RE.sub("//@version=5", line)

    # 코드 부분과 주석 부분 분리
    code_part, comment_part = _split_code_and_comment(line)

    # 코드 부분 변환 (문자열 리터럴은 보호)
    converted_code = _convert_code_part(code_part)

    return converted_code + comment_part


def _split_code_and_comment(line: str) -> tuple[str, str]:
    """한 줄을 코드 부분과 주석 부분으로 분리한다.

    문자열 리터럴 내부의 '//'는 주석으로 처리하지 않는다.

    Returns:
        (code_part, comment_part) 튜플. comment_part는 '//'를 포함한다.
    """
    # 문자열 리터럴을 플레이스홀더로 치환해 '//' 위치를 안전하게 탐색
    placeholders: list[str] = []

    def _replace(m: re.Match[str]) -> str:
        placeholders.append(m.group(0))
        return f"\x00STR{len(placeholders) - 1}\x00"

    masked = _STRING_LITERAL_RE.sub(_replace, line)

    # 주석 시작 위치 탐색
    comment_match = re.search(r"//", masked)
    if comment_match:
        code_masked = masked[: comment_match.start()]
        comment_start_in_original = _restore_placeholders(code_masked, placeholders)
        code_part = line[: len(comment_start_in_original)]
        comment_part = line[len(comment_start_in_original) :]
    else:
        code_part = line
        comment_part = ""

    return code_part, comment_part


def _restore_placeholders(masked: str, placeholders: list[str]) -> str:
    """마스킹된 문자열을 원본으로 복원한다."""
    for i, original in enumerate(placeholders):
        masked = masked.replace(f"\x00STR{i}\x00", original)
    return masked


def _mask_string_literals(code: str) -> str:
    """코드에서 문자열 리터럴을 플레이스홀더로 마스킹한다."""
    return _STRING_LITERAL_RE.sub("\x00MASKED\x00", code)


def _convert_code_part(code: str) -> str:
    """코드 부분에서 v4 → v5 변환을 수행한다.

    문자열 리터럴 내부는 변환하지 않는다.
    """
    # 문자열 리터럴을 임시 플레이스홀더로 치환
    placeholders: list[str] = []

    def _replace_str(m: re.Match[str]) -> str:
        placeholders.append(m.group(0))
        return f"\x00STR{len(placeholders) - 1}\x00"

    masked = _STRING_LITERAL_RE.sub(_replace_str, code)

    # ta.* 프리픽스 추가
    masked = _TA_FUNC_RE.sub(r"ta.\1", masked)

    # input() 변환
    masked = _INPUT_CALL_RE.sub(_convert_input_calls, masked)

    # 플레이스홀더 복원
    for i, original in enumerate(placeholders):
        masked = masked.replace(f"\x00STR{i}\x00", original)

    return masked


def _convert_input_calls(m: re.Match[str]) -> str:
    """input(arg) 호출을 input.TYPE(arg)로 변환한다."""
    args_str = m.group(1).strip()
    inferred_type = _infer_input_type(args_str)
    return f"input.{inferred_type}({m.group(1)})"


def _infer_input_type(first_arg: str) -> str:
    """첫 번째 인수 리터럴로 input 타입을 추론한다.

    - 정수 리터럴 → "int"
    - 실수 리터럴 → "float"
    - true/false → "bool"
    - 문자열 리터럴 → "source"
    - 그 외 → "int" (기본값)
    """
    stripped = first_arg.strip().split(",")[0].strip()

    # bool
    if stripped in ("true", "false"):
        return "bool"

    # float (소수점 포함)
    try:
        if "." in stripped:
            float(stripped)
            return "float"
    except ValueError:
        pass

    # int
    try:
        int(stripped)
        return "int"
    except ValueError:
        pass

    # 문자열 리터럴 (따옴표로 감싸진 경우) 또는 마스킹된 플레이스홀더
    if (stripped.startswith('"') and stripped.endswith('"')) or (
        stripped.startswith("'") and stripped.endswith("'")
    ) or stripped.startswith("\x00STR"):
        return "source"

    # 기본값
    return "int"
