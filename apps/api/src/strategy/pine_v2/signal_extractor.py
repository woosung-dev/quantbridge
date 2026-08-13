# Pine Script 신호 조건 추출기 — indicator → strategy 변환 전처리
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, cast

from src.strategy.pine_v2.coverage import analyze_coverage

# ─── 상수 ─────────────────────────────────────────────────────────────────────

_PINE_KEYWORDS = frozenset(
    {
        "true",
        "false",
        "na",
        "var",
        "varip",
        "if",
        "else",
        "for",
        "while",
        "to",
        "by",
        "and",
        "or",
        "not",
        "in",
    }
)

_DRAWING_RE = re.compile(r"\b(array|matrix|box|table)\.\w+\s*\(")
_COLOR_GRADIENT_RE = re.compile(r"\bcolor\.from_gradient\b")
_CHART_FG_RE = re.compile(r"\bchart\.fg_color\b")


# ─── 공개 타입 ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ExtractionResult:
    sliced_code: str
    signal_vars: list[str]
    removed_lines: int
    removed_functions: list[str]
    is_runnable: bool
    token_reduction_pct: float  # 0-100


class SignalExtractor:
    """Pine Script 소스에서 신호 조건만 추출해 최소 코드 반환."""

    def extract(
        self,
        source: str,
        mode: Literal["text", "ast"] = "ast",
    ) -> ExtractionResult:
        if mode == "text":
            return self._extract_text(source)
        return self._extract_ast(source)

    # ─── C-text ───────────────────────────────────────────────────────────────

    def _extract_text(self, source: str) -> ExtractionResult:
        user_vars = _find_user_defined(source)
        signal_vars = _find_signal_vars_text(source, user_vars)
        needed = _collect_deps(source, set(signal_vars), user_vars)

        kept_lines, removed_funcs = _extract_needed_lines(source, needed)
        header = _strategy_header(source)
        footer = _strategy_entry_footer(signal_vars)
        sliced = "\n".join([header, *kept_lines, footer])

        orig_lines = len(source.splitlines())
        removed_count = orig_lines - len(kept_lines)
        # 원본 라인 수 대비 kept 라인 수로 감소율 계산 (헤더/푸터 추가분 제외)
        reduction = max(0.0, (1 - len(kept_lines) / max(orig_lines, 1)) * 100)

        return ExtractionResult(
            sliced_code=sliced,
            signal_vars=signal_vars,
            removed_lines=removed_count,
            removed_functions=removed_funcs,
            is_runnable=analyze_coverage(sliced).is_runnable,
            token_reduction_pct=round(reduction, 1),
        )

    # ─── C-ast ────────────────────────────────────────────────────────────────

    def _extract_ast(self, source: str) -> ExtractionResult:
        try:
            import pynescript.ast as pyne_ast

            tree = pyne_ast.parse(source)
        except Exception:
            return self._extract_text(source)  # 파싱 실패 → C-text 폴백

        user_vars = _find_user_defined(source)
        signal_vars = _find_signal_vars_ast(tree, user_vars)

        if not signal_vars:
            return self._extract_text(source)  # 신호 변수 미탐지 → C-text 폴백

        needed = _collect_deps(source, set(signal_vars), user_vars)
        kept_lines, removed_funcs = _extract_needed_lines(source, needed)
        header = _strategy_header(source)
        footer = _strategy_entry_footer(signal_vars)
        sliced = "\n".join([header, *kept_lines, footer])

        orig_lines = len(source.splitlines())
        removed_count = orig_lines - len(kept_lines)
        reduction = max(0.0, (1 - len(kept_lines) / max(orig_lines, 1)) * 100)

        return ExtractionResult(
            sliced_code=sliced,
            signal_vars=signal_vars,
            removed_lines=removed_count,
            removed_functions=removed_funcs,
            is_runnable=analyze_coverage(sliced).is_runnable,
            token_reduction_pct=round(reduction, 1),
        )


# ─── 헬퍼 함수 ────────────────────────────────────────────────────────────────


def _find_user_defined(source: str) -> frozenset[str]:
    """소스에서 사용자 정의 변수/함수명 추출."""
    names: set[str] = set()
    # 일반 대입: name = ... 또는 name :=
    for m in re.finditer(
        r"^[ \t]*(?:var\s+|varip\s+)?([A-Za-z_]\w*)\s*:?=",
        source,
        re.MULTILINE,
    ):
        names.add(m.group(1))
    # 구조 분해: [a, b] = ...
    for m in re.finditer(r"\[([A-Za-z_][A-Za-z0-9_,\s]*)\]\s*=", source):
        names.update(re.findall(r"[A-Za-z_]\w*", m.group(1)))
    # 함수 정의: name(args) =>
    for m in re.finditer(r"^([A-Za-z_]\w*)\s*\([^)]*\)\s*=>", source, re.MULTILINE):
        names.add(m.group(1))
    return frozenset(names - _PINE_KEYWORDS)


def _find_signal_vars_text(source: str, user_vars: frozenset[str]) -> list[str]:
    """plotshape / strategy.entry / label.new 패턴에서 신호 변수 탐지."""
    candidates: set[str] = set()

    # strategy.entry(..., when=var)
    for m in re.finditer(
        r"strategy\.entry\s*\([^)]*\bwhen\s*=\s*([A-Za-z_]\w*)",
        source,
        re.DOTALL,
    ):
        candidates.add(m.group(1))

    # plotshape(expr, ...) — 첫 번째 인자에서 식별자 수집
    for m in re.finditer(r"\bplotshape\s*\((.+?)(?:,\s*[\"'\w])", source, re.DOTALL):
        for ident in re.findall(r"\b([A-Za-z_]\w*)\b", m.group(1)):
            candidates.add(ident)

    # label.new(var ? ...) — 삼항 신호 패턴
    for m in re.finditer(r"\blabel\.new\s*\(\s*([A-Za-z_]\w*)\s*\?", source):
        candidates.add(m.group(1))

    # alertcondition(var, ...) — 첫 번째 인자가 신호 조건
    for m in re.finditer(r"\balertcondition\s*\(\s*([A-Za-z_]\w*)\b", source):
        candidates.add(m.group(1))

    # 사용자 정의 변수만 유지
    return sorted(candidates & user_vars)


def _collect_deps(
    source: str,
    seeds: set[str],
    user_vars: frozenset[str],
    depth: int = 0,
) -> set[str]:
    """seed 변수로부터 사용자 정의 의존성 재귀 수집 (최대 depth=5)."""
    if depth >= 5:
        return seeds

    new_vars: set[str] = set()
    lines = source.splitlines()

    for line in lines:
        # 일반 대입: var = expr 또는 var := expr
        m = re.match(
            r"^[ \t]*(?:var\s+|varip\s+)?([A-Za-z_]\w*)\s*:?=\s*(.+)",
            line,
        )
        if m and m.group(1) in seeds:
            for ident in re.findall(r"\b([A-Za-z_]\w*)\b", m.group(2)):
                if ident in user_vars and ident not in seeds:
                    new_vars.add(ident)
            continue

        # 구조 분해 대입: [a, b] = func(...) — RHS 에서 사용자 정의 함수 탐지
        m = re.match(
            r"^[ \t]*\[([A-Za-z_][A-Za-z0-9_,\s]*)\]\s*=\s*(.+)",
            line,
        )
        if m:
            lhs_vars = re.findall(r"[A-Za-z_]\w*", m.group(1))
            if any(v in seeds for v in lhs_vars):
                for ident in re.findall(r"\b([A-Za-z_]\w*)\b", m.group(2)):
                    if ident in user_vars and ident not in seeds:
                        new_vars.add(ident)
            continue

        # 함수 정의 헤더: name(args) => — 함수 바디에서 사용하는 사용자 정의 항목 탐지
        m = re.match(r"^([A-Za-z_]\w*)\s*\([^)]*\)\s*=>", line)
        if m and m.group(1) in seeds:
            # 이 함수의 바디 라인 수집 (들여쓰기 기반)
            func_start = lines.index(line)
            for body_line in lines[func_start + 1 :]:
                if not body_line or body_line[0] not in " \t":
                    break
                for ident in re.findall(r"\b([A-Za-z_]\w*)\b", body_line):
                    if ident in user_vars and ident not in seeds:
                        new_vars.add(ident)

    if new_vars:
        return _collect_deps(source, seeds | new_vars, user_vars, depth + 1)
    return seeds


def _is_drawing_line(line: str) -> bool:
    return bool(
        _DRAWING_RE.search(line) or _COLOR_GRADIENT_RE.search(line) or _CHART_FG_RE.search(line)
    )


def _extract_needed_lines(
    source: str,
    needed: set[str],
) -> tuple[list[str], list[str]]:
    """needed 변수/함수 정의 라인 추출. 드로잉 API 라인 제거."""
    lines = source.splitlines()
    kept: list[str] = []
    removed_funcs: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # input() 선언은 항상 포함 (드로잉 아닐 때)
        if re.search(r"\binput(?:\.\w+)?\s*\(", line) and not _is_drawing_line(line):
            kept.append(line)
            i += 1
            continue

        # 함수 정의 블록: name(args) =>
        m = re.match(r"^([A-Za-z_]\w*)\s*\([^)]*\)\s*=>", line)
        if m and m.group(1) in needed:
            block = [line]
            i += 1
            while i < len(lines) and lines[i] and lines[i][0] in " \t":
                block.append(lines[i])
                i += 1
            full_block = "\n".join(block)
            if _is_drawing_line(full_block):
                removed_funcs.append(m.group(1))
            else:
                kept.extend(block)
            continue

        # 일반 변수 대입
        m = re.match(r"^[ \t]*(?:var\s+|varip\s+)?([A-Za-z_]\w*)\s*:?=", line)
        if m and m.group(1) in needed:
            if _is_drawing_line(line):
                removed_funcs.append(m.group(1))
            else:
                kept.append(line)
            i += 1
            continue

        # 구조 분해 대입: [a, b] = func(...)
        m = re.match(r"^[ \t]*\[([A-Za-z_][A-Za-z0-9_,\s]*)\]\s*=\s*(.+)", line)
        if m:
            vars_in = re.findall(r"[A-Za-z_]\w*", m.group(1))
            if any(v in needed for v in vars_in) and not _is_drawing_line(line):
                kept.append(line)
            i += 1
            continue

        i += 1

    return kept, removed_funcs


def _strategy_header(source: str) -> str:
    """원본 indicator 제목 추출 후 strategy 헤더 생성."""
    m = re.search(r"(?:indicator|strategy)\s*\(\s*[\"']([^\"']+)[\"']", source)
    title = m.group(1) if m else "Converted Strategy"
    return (
        "//@version=5\n"
        f'strategy("{title}", overlay=true, '
        "default_qty_type=strategy.percent_of_equity, default_qty_value=10)"
    )


def _find_signal_vars_ast(tree: object, user_vars: frozenset[str]) -> list[str]:
    """AST walk 기반 신호 변수 탐지 (plotshape / strategy.entry / label.new)."""
    import pynescript.ast as pyne_ast

    candidates: set[str] = set()

    def _get_func_name(call_node: object) -> str | None:
        func = getattr(call_node, "func", None)
        if func is None:
            return None
        if hasattr(func, "id"):
            return str(func.id)  # 단순 함수 이름 (예: plotshape)
        # Attribute 노드 (예: strategy.entry, label.new)
        if hasattr(func, "attr") and hasattr(func, "value") and hasattr(func.value, "id"):
            return f"{func.value.id}.{func.attr}"
        return None

    def _collect_names_from_node(node: pyne_ast.AST) -> None:
        """노드 서브트리에서 user_vars 에 속하는 Name.id 수집."""
        for sub in pyne_ast.walk(node):
            sub_type = type(sub).__name__
            if sub_type == "Name" and hasattr(sub, "id") and sub.id in user_vars:
                candidates.add(sub.id)

    ast_tree = cast("pyne_ast.AST", tree)
    for node in pyne_ast.walk(ast_tree):
        if type(node).__name__ != "Call":
            continue

        func_name = _get_func_name(node)
        if func_name is None:
            continue

        args: list[pyne_ast.AST] = getattr(node, "args", []) or []

        if func_name == "plotshape":
            # 첫 번째 인자에서 사용자 변수 수집
            if args:
                _collect_names_from_node(args[0])

        elif func_name == "strategy.entry":
            # when= 키워드 인자 탐색 (Arg.name == "when")
            for arg in args:
                if getattr(arg, "name", None) == "when":
                    val = getattr(arg, "value", None)
                    if val is not None and hasattr(val, "id") and val.id in user_vars:
                        candidates.add(val.id)

        elif func_name == "label.new":
            # 첫 번째 인자의 삼항 test 에서 사용자 변수 수집
            arg0_val = getattr(args[0], "value", None) if args else None
            if arg0_val is not None and type(arg0_val).__name__ == "Conditional":
                test_node = getattr(arg0_val, "test", None)
                if test_node is not None:
                    _collect_names_from_node(test_node)

        elif func_name == "alertcondition" and args:
            # alertcondition(var, title=...) — 첫 번째 인자가 신호 조건
            _collect_names_from_node(args[0])

    return sorted(candidates & user_vars)


def _strategy_entry_footer(signal_vars: list[str]) -> str:
    """신호 변수를 strategy.entry / strategy.close 로 변환."""
    if not signal_vars:
        return "// [변환 실패: 신호 변수를 찾지 못했습니다]"

    buy_keywords = ("bull", "buy", "long", "up")
    sell_keywords = ("bear", "sell", "short", "down")

    buy_var = next(
        (v for v in signal_vars if any(k in v.lower() for k in buy_keywords)),
        signal_vars[0],
    )
    sell_var = next(
        (v for v in signal_vars if any(k in v.lower() for k in sell_keywords)),
        signal_vars[-1],
    )

    return (
        f'strategy.entry("Long",  strategy.long,  when={buy_var})\n'
        f'strategy.entry("Short", strategy.short, when={sell_var})\n'
        f'strategy.close("Long",  when={sell_var})\n'
        f'strategy.close("Short", when={buy_var})'
    )
