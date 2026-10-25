"""실제 에디터 픽 UI 캡처와 검토한 신호 바인딩을 연결한다."""

from __future__ import annotations

import ast
import copy
import inspect
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from urllib.parse import urlsplit

from tools.research.editor_picks.common import (
    ROOT,
    checked_file,
    identity,
    immutable,
    lock,
    now,
    read,
    sha,
    write,
)


def ingest(root: Path) -> dict:
    with lock(root / "catalogue.lock"):
        return _ingest(root)


def _ingest(root: Path) -> dict:
    items = {}
    for path in sorted((root / "captures").glob("*.json")):
        payload = read(path)
        if payload.get("schema_version") != 1:
            raise ValueError("UI 수집 스키마가 다릅니다")
        listings = {row["url"]: row for row in payload["listings"]}
        for row in payload["captures"]:
            listing = listings[row["listing_url"]]
            parsed = urlsplit(listing["url"])
            if (
                parsed.scheme != "https"
                or parsed.hostname != "www.tradingview.com"
                or not re.fullmatch(
                    r"/scripts/editors-picks/(?:page-\d+/)?", parsed.path
                )
                or not any(item["url"] == row["url"] for item in listing["items"])
            ):
                raise ValueError("에디터 픽 목록 관측 근거가 없습니다")
            publication = re.fullmatch(
                r"https://www.tradingview.com/script/([A-Za-z0-9]{8})[^?#]*/",
                row["url"],
            )
            if publication is None or publication[1] != row["id"]:
                raise ValueError("게시물 ID와 URL이 다릅니다")
            item = {key: value for key, value in row.items() if key != "source"}
            item["capture"] = {
                "path": str(path.relative_to(root)),
                "sha256": sha(path.read_bytes()),
            }
            if row["status"] == "captured":
                response = urlsplit(row["source_response_url"])
                if (
                    response.hostname != "pine-facade.tradingview.com"
                    or not response.path.startswith("/pine-facade/get/")
                    or row.get("script_access") not in {"open_no_auth", "open"}
                ):
                    raise ValueError("UI가 받은 공개 원문 응답이 아닙니다")
                source = row["source"].encode()
                source_hash = sha(source)
                target = root / "sources" / f"{row['id']}-{source_hash[:12]}.pine"
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists() and target.read_bytes() != source:
                    raise ValueError("원문 파일이 변경됐습니다")
                target.write_bytes(source)
                item.update(
                    source_file=str(target.relative_to(root)),
                    source_sha256=source_hash,
                    license_notices=[
                        line
                        for line in row["source"].splitlines()
                        if re.search(
                            r"license|copyright|©|all rights reserved", line, re.I
                        )
                    ],
                )
            previous = items.get(row["id"])
            if (
                previous
                and previous.get("source_sha256")
                and item.get("source_sha256")
                and previous["source_sha256"] != item["source_sha256"]
            ):
                raise ValueError("같은 게시물의 원문 버전 변경: 새 실험이 필요합니다")
            if not previous or not previous.get("source_sha256"):
                items[row["id"]] = item
    seen = {}
    for item in items.values():
        digest = item.get("source_sha256")
        if digest in seen:
            item["duplicate_of"] = seen[digest]
        elif digest:
            seen[digest] = item["id"]

    def order(item):
        match = re.search(r"/page-(\d+)/", item["listing_url"])
        return int(match[1]) if match else 1, item["listing_position"]

    catalogue = {
        "schema_version": 1,
        "observed_at": now(),
        "items": sorted(items.values(), key=order),
    }
    write(root / "catalogue.json", catalogue)
    return catalogue


def raw_signal_strategy(adapted):
    """연구용 생성 진입문의 포지션 guard만 제거하고 원문 계산은 보존한다."""
    code = adapted.strategy_source
    for binding in adapted.bindings:
        direction = binding["direction"]
        if direction not in {"long", "short"}:
            raise ValueError("원시 신호 연구는 진입 방향만 지원합니다")
        temporary = re.escape(binding["condition_variable"])
        operator = "<=" if direction == "long" else ">="
        # unique()가 원문 이름과 분리한 조건 변수와 생성 flag의 최상위 if만 수정한다.
        pattern = rf"^(if {temporary}) and strategy\.position_size {operator} 0 (and not qb_adapt_{direction}_submitted_*)(\r?)$"
        code, count = re.subn(pattern, r"\1 \2\3", code, flags=re.MULTILINE)
        if count != 1:
            raise ValueError("생성 진입문의 고유 position guard를 확인할 수 없습니다")
    if code.count("\n") != adapted.strategy_source.count("\n"):
        raise ValueError("연구 신호 어댑터가 원문 줄 지도를 변경했습니다")
    return replace(
        adapted,
        strategy_source=code,
        converted_sha256=sha(code.encode()),
        warnings=[
            *adapted.warnings,
            "raw_signal_v1: 같은 방향 신호도 제출하며 중복 진입은 공통 원장이 처리합니다",
        ],
    )


def augment_expression_signals(
    source: str, bindings: list[dict]
) -> tuple[str, list[dict], dict]:
    """검토한 읽기 전용 전역 조건만 원문 끝의 별도 진단 호출로 연결한다."""
    from pynescript import ast as A

    from src.strategy.pine_v2.interpreter import pine_version_from_ast
    from src.strategy.pine_v2.parser_adapter import parse_to_ast

    if len(bindings) != 2 or {b.get("direction") for b in bindings} != {
        "long",
        "short",
    }:
        raise ValueError("조건식은 long/short 한 개씩 필요합니다")
    tree = parse_to_ast(source)
    version = pine_version_from_ast(tree)
    globals_ = {
        "open",
        "high",
        "low",
        "close",
        "volume",
        "hl2",
        "hlc3",
        "ohlc4",
        "hlcc4",
        "time",
        "bar_index",
        "na",
    }
    for statement in tree.body:
        if isinstance(statement, A.Assign):
            target = statement.target
            targets = target.elts if isinstance(target, A.Tuple) else [target]
            globals_.update(t.id for t in targets if isinstance(t, A.Name))
    udf_names = {node.name for node in A.walk(tree) if isinstance(node, A.FunctionDef)}
    allowed_calls = {"ta.crossover", "ta.crossunder", "crossover", "crossunder", "na"}
    allowed_calls.update(
        f"math.{name}"
        for name in (
            "abs",
            "min",
            "max",
            "round",
            "floor",
            "ceil",
            "sqrt",
            "pow",
            "log",
            "exp",
            "sign",
            "sin",
            "cos",
            "tan",
            "asin",
            "acos",
            "atan",
        )
    )

    def call_name(node):
        if isinstance(node, A.Name):
            return node.id
        if isinstance(node, A.Attribute) and isinstance(node.value, A.Name):
            return f"{node.value.id}.{node.attr}"
        return ""

    def validate(node):
        if isinstance(node, A.Name):
            if node.id not in globals_:
                raise ValueError(f"조건식의 미지원 전역 이름: {node.id}")
        elif isinstance(node, A.Constant):
            if type(node.value) not in (bool, int, float, str):
                raise ValueError("조건식 상수 형식이 다릅니다")
        elif isinstance(node, A.Call):
            name = call_name(node.func)
            if name not in allowed_calls or name in udf_names:
                raise ValueError(f"조건식의 미지원 호출: {name}")
            for argument in node.args:
                if argument.name is not None:
                    raise ValueError("진단 조건 호출은 positional 인자만 허용합니다")
                validate(argument.value)
        elif isinstance(node, A.Subscript):
            if not isinstance(node.value, A.Name) or not isinstance(
                node.slice, A.Constant
            ):
                raise ValueError("조건식 이력은 전역 변수의 상수 인덱스만 허용합니다")
            if type(node.slice.value) is not int or not 0 <= node.slice.value <= 10000:
                raise ValueError("조건식 이력 인덱스가 범위 밖입니다")
            validate(node.value)
        elif isinstance(node, A.BoolOp):
            if not isinstance(node.op, (A.And, A.Or)):
                raise ValueError("조건식 논리 연산이 다릅니다")
            for value in node.values:
                validate(value)
        elif isinstance(node, A.Compare):
            if not all(
                isinstance(op, (A.Eq, A.NotEq, A.Lt, A.LtE, A.Gt, A.GtE))
                for op in node.ops
            ):
                raise ValueError("조건식 비교 연산이 다릅니다")
            for value in [node.left, *node.comparators]:
                validate(value)
        elif isinstance(node, A.BinOp) and isinstance(
            node.op, (A.Add, A.Sub, A.Mult, A.Div, A.Mod)
        ):
            validate(node.left)
            validate(node.right)
        elif isinstance(node, A.UnaryOp) and isinstance(
            node.op, (A.Not, A.UAdd, A.USub)
        ):
            validate(node.operand)
        else:
            raise ValueError("조건식은 읽기 전용 스칼라 연산만 허용합니다")

    newline = "\r\n" if "\r\n" in source else "\n"
    augmented = source + ("" if source.endswith("\n") else newline)
    generated = []
    diagnostics = []
    for binding in sorted(bindings, key=lambda b: b["direction"]):
        expression = binding.get("expression")
        if (
            not isinstance(expression, str)
            or not expression.strip()
            or len(expression) > 2048
        ):
            raise ValueError("검토한 조건식 문자열이 필요합니다")
        if "\n" in expression or "\r" in expression:
            raise ValueError("조건식은 한 줄이어야 합니다")
        parsed = parse_to_ast(f"alertcondition(({expression}))\n")
        if len(parsed.body) != 1 or not isinstance(parsed.body[0], A.Expr):
            raise ValueError("조건식 외 문장이 있습니다")
        call = parsed.body[0].value
        if (
            not isinstance(call, A.Call)
            or call_name(call.func) != "alertcondition"
            or len(call.args) != 1
        ):
            raise ValueError("조건식 외 호출이 있습니다")
        validate(call.args[0].value)
        compiled_expression = expression
        if version < 5:
            compiled_node = copy.deepcopy(call.args[0].value)
            changed = False
            for node in A.walk(compiled_node):
                if not isinstance(node, A.Call):
                    continue
                name = call_name(node.func)
                if name.startswith(("ta.", "math.")):
                    legacy = name.split(".", 1)[1]
                    if legacy in udf_names:
                        raise ValueError(
                            "이전 Pine 버전의 진단 함수 이름이 UDF와 충돌합니다"
                        )
                    node.func = A.Name(id=legacy, ctx=A.Load())
                    changed = True
            if changed:
                compiled_expression = A.unparse(compiled_node)
        title = f"qb_expression_{sha(source.encode())[:12]}_{binding['direction']}"
        while title in source:
            title += "_"
        line = augmented.count("\n") + 1
        augmented += f'alertcondition(({compiled_expression}), title="{title}", message="{title}"){newline}'
        generated.append(
            {
                "direction": binding["direction"],
                "function": "alertcondition",
                "line": line,
                "expression": expression,
            }
        )
        diagnostic = {**binding, "line": line, "title": title, "message": title}
        if compiled_expression != expression:
            diagnostic["compiled_expression"] = compiled_expression
        diagnostics.append(diagnostic)
    return (
        augmented,
        generated,
        {
            "policy": "reviewed_expression_v1",
            "original_source_sha256": sha(source.encode()),
            "augmented_source_sha256": sha(augmented.encode()),
            "original_line_count": len(source.splitlines()),
            "diagnostics": diagnostics,
            "native_verified": False,
        },
    )


def screen_one(root: Path, identifier: str) -> dict:
    from scripts.pine_validation.strategy_adapter import adapt_strategy
    from src.strategy.pine_v2.coverage import analyze_coverage

    item = next(
        x for x in read(root / "catalogue.json")["items"] if x["id"] == identifier
    )
    if item.get("duplicate_of") or item["status"] != "captured":
        return {
            "id": identifier,
            "status": "excluded",
            "reason": item.get("duplicate_of", item["status"]),
        }
    source = (
        checked_file(root, item["source_file"], item["source_sha256"])
        .read_bytes()
        .decode()
    )
    # 원문 바이트는 보존한다. 줄 단위 정적 검사는 CRLF의 CR을 문법으로 오인하지 않는다.
    coverage = analyze_coverage(source.replace("\r\n", "\n"))
    base = {"id": identifier, "source_sha256": item["source_sha256"]}
    # 연구의 세 주기는 실제 봉 격자를 검사한 metadata로 JSONL worker에 전달한다.
    # request.security 등 다른 근사는 이 문맥으로 해제하지 않는다.
    if not coverage.is_runnable or set(coverage.degraded_calls) - {"timeframe.period"}:
        return {**base, "status": "unsupported", "detail": str(coverage)}
    review_path = root / "reviews" / f"{identifier}.json"
    if not review_path.exists():
        return {**base, "status": "needs_binding_review"}
    review = read(review_path)
    if (
        review.get("decision") == "exclude"
        and review.get("source_sha256") == item["source_sha256"]
    ):
        return {**base, "status": "excluded", "reason": review["basis"]}
    if (
        review.get("source_sha256") != item["source_sha256"]
        or not review.get("reviewed_by")
        or not review.get("basis")
        or not review.get("family")
        or {
            b.get("direction")
            for b in review.get(
                "expression_bindings"
                if review.get("binding_type") == "expression"
                else "signal_bindings",
                [],
            )
        }
        != {"long", "short"}
        or not 200 <= review.get("warmup_bars", 0) <= 10000
    ):
        raise ValueError("원문 해시·양방향 신호·준비봉·검토 근거가 필요합니다")
    expression_provenance = None
    signal_bindings = review.get("signal_bindings", [])
    if review.get("binding_type", "call") not in {"call", "expression"}:
        raise ValueError("신호 바인딩 형식이 다릅니다")
    if review.get("binding_type") == "expression":
        source, signal_bindings, expression_provenance = augment_expression_signals(
            source, review["expression_bindings"]
        )
        augmented_path = root / "augmented" / f"{identifier}.pine"
        augmented_path.parent.mkdir(parents=True, exist_ok=True)
        if augmented_path.exists():
            if augmented_path.read_bytes() != source.encode():
                raise ValueError("이미 생성한 진단 원문 변경을 거부합니다")
        else:
            augmented_path.write_bytes(source.encode())
        expression_provenance["augmented_file"] = str(augmented_path.relative_to(root))
    adapted = adapt_strategy(source, signal_bindings, fixed_quantity=None)
    base_adapted_sha256 = adapted.converted_sha256
    adapted = raw_signal_strategy(adapted)
    code = adapted.strategy_source
    if not analyze_coverage(code).is_runnable:
        return {**base, "status": "adaptation_unsupported"}
    path = root / "adapted" / f"{identifier}.pine"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(code.encode())
    return {
        **item,
        **review,
        "status": "static_eligible",
        "adapted_file": str(path.relative_to(root)),
        "adapted_sha256": sha(code.encode()),
        "adaptation": adapted.to_dict(),
        **(
            {
                "signal_bindings": signal_bindings,
                "expression_provenance": expression_provenance,
            }
            if expression_provenance is not None
            else {}
        ),
        "research_adapter": {
            "policy": "raw_signal_v1",
            "base_adapted_sha256": base_adapted_sha256,
        },
        "execution_verified": False,
        "runtime_context": {
            "timeframes": ["1h", "4h", "1d"],
            "transport": "validated_frame_metadata",
        },
    }


def _screen_implementation_hash() -> str:
    paths = sorted((ROOT / "apps/api/src/strategy/pine_v2").rglob("*.py"))
    paths += [ROOT / "apps/api/scripts/pine_validation/strategy_adapter.py"]
    return identity(
        {
            "dependencies": {
                str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in paths
            },
            # 스케줄러 수정은 기존 판정을 무효화하지 않는다.
            "binding": ast.dump(ast.parse(inspect.getsource(screen_one))),
            "research_adapter": ast.dump(
                ast.parse(inspect.getsource(raw_signal_strategy))
            ),
            "expression_adapter": ast.dump(
                ast.parse(inspect.getsource(augment_expression_signals))
            ),
            "file_validation": ast.dump(ast.parse(inspect.getsource(checked_file))),
        }
    )


def _screen_request(root: Path, item: dict, timeout: int, implementation: str) -> str:
    review = root / "reviews" / f"{item['id']}.json"
    return identity(
        {
            "item": item,
            "review": sha(review.read_bytes()) if review.exists() else None,
            "implementation": implementation,
            "timeout": timeout,
        }
    )


def screen(root: Path, timeout: int = 15, workers: int = 4) -> list[dict]:
    if not 1 <= workers <= 4:
        raise ValueError("정적 검사 병렬 수는 1~4입니다")
    with lock(root / "screening.lock"):
        implementation = _screen_implementation_hash()
        items = read(root / "catalogue.json")["items"]
        if len({item["id"] for item in items}) != len(items):
            raise ValueError("같은 게시물 ID를 동시에 검사할 수 없습니다")

        def scan(item: dict) -> dict:
            destination = root / "screening" / f"{item['id']}.json"
            if item.get("source_sha256"):
                checked_file(root, item["source_file"], item["source_sha256"])
            request_hash = _screen_request(root, item, timeout, implementation)
            if destination.exists():
                previous = read(destination)
                if previous.get("screen_request_sha256") == request_hash:
                    if previous.get("status") == "static_eligible":
                        checked_file(
                            root, previous["adapted_file"], previous["adapted_sha256"]
                        )
                    return previous
            review = root / "reviews" / f"{item['id']}.json"
            try:
                completed = subprocess.run(  # noqa: S603 — 현재 Python의 고정 정적 검사 모듈만 실행
                    [
                        sys.executable,
                        "-m",
                        "tools.research.editor_picks",
                        "--run-dir",
                        str(root),
                        "screen-one",
                        "--id",
                        item["id"],
                    ],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    timeout=timeout * 3 if review.exists() else timeout,
                )
                if completed.returncode:
                    row = {
                        "id": item["id"],
                        "status": "screen_failed",
                        "error": completed.stderr[-1500:],
                    }
                else:
                    row = read(destination)
            except subprocess.TimeoutExpired:
                row = {"id": item["id"], "status": "parser_timeout"}
            if request_hash != _screen_request(root, item, timeout, implementation):
                row = {"id": item["id"], "status": "screen_input_changed"}
            else:
                row["screen_request_sha256"] = request_hash
            write(destination, row)
            return row

        with ThreadPoolExecutor(max_workers=workers) as pool:
            rows = {
                item["id"]: row
                for item, row in zip(items, pool.map(scan, items), strict=True)
            }
        # 수집이 계속되는 동안 추가된 원문을 이전 스냅샷으로 숨기지 않는다.
        with lock(root / "catalogue.lock"):
            current = read(root / "catalogue.json")["items"]
            result = []
            for item in current:
                row = rows.get(item["id"])
                if row is None or row.get("screen_request_sha256") != _screen_request(
                    root, item, timeout, implementation
                ):
                    row = {"id": item["id"], "status": "screen_pending"}
                result.append(row)
            write(root / "screening.json", result)
            return result


def seal(
    root: Path, count: int = 200, pilot: bool = False, allow_partial: bool = False
) -> dict:
    if count < 1 or (pilot and allow_partial):
        raise ValueError("양수 목표가 필요하며 파일럿 부분 동결은 허용하지 않습니다")
    selected = [
        row
        for row in read(root / "screening.json")
        if row["status"] == "static_eligible"
    ][:count]
    if (
        not selected
        or (len(selected) != count and not allow_partial)
        or len({item["source_sha256"] for item in selected}) != len(selected)
    ):
        raise ValueError("중복 없는 검토 원문이 필요합니다")
    cohort = {
        "schema_version": 1,
        "target": count,
        "items": selected,
        "source_count": len(selected),
        "execution_verified": False,
        "selection_policy": "editor_pick_order_then_pine_eligibility_not_returns",
        "complete": False,
    }
    immutable(root / ("pilot-cohort.json" if pilot else "cohort.json"), cohort)
    return cohort
