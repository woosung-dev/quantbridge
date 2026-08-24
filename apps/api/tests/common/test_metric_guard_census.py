"""R1 metric guard census.

대상 = ``apps/api/src/**/*.py``.

site는 다음 AST ``Call`` 이다.

(a) ``func.attr`` 이 ``inc``, ``dec``, ``observe``, ``set`` 중 하나이고,
    ``.labels(...)`` 체인의 뿌리가 ``^qb_`` 인 ``Name`` 이거나 그 ``Name`` 에 직접
    mutation 을 호출한 것.
(b) 뿌리가 ``^qb_`` 인 ``.labels(...)`` 호출 중 (a)의 수신자가 아닌 것, 즉 증가 없이
    라벨 조합을 실체화하는 호출.

guarded는 ``record_metric_safely`` / ``_count_safely`` / ``_touch_safely`` 호출이 덮는
범위다.

(i) 호출 인자 서브트리와 그 안의 ``lambda:`` 본문.
(ii) 이름으로 넘긴 중첩 ``def`` 본문. 예를 들어 ``def increment(): ...`` 뒤에
     ``record_metric_safely(increment)`` 를 호출하면 그 본문은 guarded다.

해로운 try는 수동 동결한 보호 후보 mutation 이 예외 결과를 보고하는 가장 가까운 ``try`` 안에
있는지로 판정한다. A 는 ``try`` 본문, B 는 ``except`` 본문이다. 결과 보고는 rollback,
``*_errors_total`` mutation, 또는 ``failed`` 로그다. 중첩 ``try`` 의 ``except`` 안에 있는
call은 그 handler가 직접 결과를 보고하지 않으면 바깥 ``try`` 를 계속 찾는다. 가드 밖인지는
위 frozen census가 별도로 집행하므로, 보호 자리는 가드 추가 뒤에도 남는다.

못 잡는 것: 별칭(``c = qb_x; c.inc()``), ``getattr`` 등 동적 접근, 모듈 alias 경유,
``qb_`` 아닌 이름, 그리고 후보 밖 자리가 실제 업무 경로인지다. 그 의미 판정은 AST가
아니라 수동 census 기준이 맡는다.
"""

from __future__ import annotations

import ast
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import pytest

from src.common.metrics import _LIVE_CONDITIONAL_GUARD_OUTCOMES

_MUTATION_METHODS = frozenset({"inc", "dec", "observe", "set"})
_GUARD_FUNCTIONS = frozenset({"record_metric_safely", "_count_safely", "_touch_safely"})
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_REPOSITORY_ROOT = _BACKEND_ROOT.parent.parent
_SOURCE_ROOT = _BACKEND_ROOT / "src"

_CENSUS_RULE_FAILURE_MESSAGE = """
R1 metric guard census rule:
(a) ``inc``/``dec``/``observe``/``set`` Call whose ``qb_`` Name is the metric root.
(b) a root-``qb_`` ``.labels(...)`` Call that is not the receiver of (a).
(i) Guard coverage includes every argument subtree, including lambda bodies.
(ii) Guard coverage includes the body of a nested def passed to the guard by name.
(iii) Harmful-try candidates must remain mutations inside the nearest result-reporting try.
(iv) A is a try body site; B is an except body site.
못 잡는 것: aliases, dynamic getattr access, module aliases, non-qb_ names, and whether a
site outside the frozen harmful candidates belongs to a business path.
""".strip()


# ★「업무 결과를 뒤집는가」는 AST만으로 판정할 수 없다. 이 4곳은 CONTROL 재측정으로
# 동결한 후보다. 아래 AST 규칙은 후보의 **raw** mutation 이 결과 보고 try의 A/B 자리에
# 남았는지만 검증한다. 전건 가드 뒤에는 반드시 0건이어야 하며, 공허화 방지는 결과 보고
# try 수 하한이 맡는다.
_HARMFUL_MUTATION_CANDIDATES = frozenset(
    {
        (
            "apps/api/src/tasks/live_signal.py",
            "qb_live_conditional_sweep_filled_total",
        ),
        (
            "apps/api/src/tasks/trading.py",
            "qb_exchange_exit_link_unverified_total",
        ),
        (
            "apps/api/src/trading/realtime_publisher.py",
            "qb_rt_publish_failed_total",
        ),
        (
            "apps/api/src/trading/webhook.py",
            "qb_webhook_symbol_rejected_total",
        ),
    }
)


# `_FROZEN_CENSUS`는 규칙 범위(결과 보고 `try`의 A/B)의 상위집합이며, 규칙 위반 건수가 아니다.
# Step 0 범위 판정 축 `_FROZEN_CENSUS_SCOPE`가 각 자리를 기계로 다시 검증한다.
_FROZEN_CENSUS: dict[tuple[str, str], int] = {
    ("apps/api/src/common/alert.py", "qb_pending_alerts"): 2,
    ("apps/api/src/common/rate_limit.py", "qb_rate_limit_throttled_total"): 1,
    ("apps/api/src/common/redis_client.py", "qb_redis_lock_pool_healthy"): 1,
    ("apps/api/src/tasks/live_signal.py", "qb_live_gap_ledger_seed_total"): 1,
    ("apps/api/src/tasks/live_signal.py", "qb_live_signal_divergence_total"): 3,
    ("apps/api/src/tasks/live_signal.py", "qb_live_signal_entry_skipped_total"): 1,
    ("apps/api/src/tasks/live_signal.py", "qb_live_signal_evaluated_total"): 5,
    ("apps/api/src/tasks/live_signal.py", "qb_live_signal_liquidation_total"): 1,
    ("apps/api/src/tasks/live_signal.py", "qb_live_signal_skipped_total"): 6,
    ("apps/api/src/tasks/websocket_task.py", "qb_ws_auth_circuit_total"): 1,
    ("apps/api/src/tasks/websocket_task.py", "qb_ws_duplicate_enqueue_total"): 2,
    ("apps/api/src/trading/kill_switch.py", "qb_kill_switch_triggered_total"): 1,
    ("apps/api/src/trading/webhook.py", "qb_order_rejected_total"): 1,
    ("apps/api/src/trading/websocket/position_fanout.py", "qb_ws_subscribe_rejected_total"): 1,
    ("apps/api/src/trading/websocket/reconciliation.py", "qb_ws_reconcile_unknown_total"): 1,
    ("apps/api/src/trading/websocket/state_handler.py", "qb_ws_orphan_discarded_total"): 1,
    ("apps/api/src/trading/websocket/state_handler.py", "qb_ws_orphan_event_total"): 1,
}


# `_FROZEN_CENSUS`의 raw mutation을 업무 결과 보고 try의 A/B 자리에만 한정해 다시 센다.
# 값은 (in_scope, out_of_scope)이며, 각 합은 위 census의 같은 키 수와 같아야 한다.
_FROZEN_CENSUS_SCOPE: dict[tuple[str, str], tuple[int, int]] = {
    ("apps/api/src/common/alert.py", "qb_pending_alerts"): (0, 2),
    ("apps/api/src/common/rate_limit.py", "qb_rate_limit_throttled_total"): (0, 1),
    ("apps/api/src/common/redis_client.py", "qb_redis_lock_pool_healthy"): (0, 1),
    ("apps/api/src/tasks/live_signal.py", "qb_live_gap_ledger_seed_total"): (0, 1),
    ("apps/api/src/tasks/live_signal.py", "qb_live_signal_divergence_total"): (0, 3),
    ("apps/api/src/tasks/live_signal.py", "qb_live_signal_entry_skipped_total"): (0, 1),
    ("apps/api/src/tasks/live_signal.py", "qb_live_signal_evaluated_total"): (0, 5),
    ("apps/api/src/tasks/live_signal.py", "qb_live_signal_liquidation_total"): (0, 1),
    ("apps/api/src/tasks/live_signal.py", "qb_live_signal_skipped_total"): (0, 6),
    ("apps/api/src/tasks/websocket_task.py", "qb_ws_auth_circuit_total"): (0, 1),
    ("apps/api/src/tasks/websocket_task.py", "qb_ws_duplicate_enqueue_total"): (0, 2),
    ("apps/api/src/trading/kill_switch.py", "qb_kill_switch_triggered_total"): (0, 1),
    ("apps/api/src/trading/webhook.py", "qb_order_rejected_total"): (0, 1),
    ("apps/api/src/trading/websocket/position_fanout.py", "qb_ws_subscribe_rejected_total"): (0, 1),
    ("apps/api/src/trading/websocket/reconciliation.py", "qb_ws_reconcile_unknown_total"): (0, 1),
    ("apps/api/src/trading/websocket/state_handler.py", "qb_ws_orphan_discarded_total"): (0, 1),
    ("apps/api/src/trading/websocket/state_handler.py", "qb_ws_orphan_event_total"): (0, 1),
}


_CENSUS_ALLOWLIST: dict[tuple[str, str], int] = {
    # 자기-계상 실패 counter를 다시 record_metric_safely로 감싸면 무한 재귀한다.
    # 이 inc()는 record_metric_safely의 자체 try/except 안에서 이미 보호된다.
    ("apps/api/src/common/metrics_multiproc.py", "qb_metrics_mutation_failed_total"): 1,
}


@dataclass(frozen=True)
class _MetricSite:
    path: str
    lineno: int
    metric: str
    verb: str
    function_name: str


@dataclass(frozen=True)
class _HarmfulMetricSite:
    path: str
    lineno: int
    metric: str
    shape: str
    function_name: str


def _metric_name(expression: ast.expr) -> str | None:
    if isinstance(expression, ast.Name) and expression.id.startswith("qb_"):
        return expression.id
    if (
        isinstance(expression, ast.Call)
        and isinstance(expression.func, ast.Attribute)
        and expression.func.attr == "labels"
    ):
        return _metric_name(expression.func.value)
    return None


def _mutation_site(call: ast.Call) -> tuple[str, str] | None:
    if not isinstance(call.func, ast.Attribute) or call.func.attr not in _MUTATION_METHODS:
        return None
    metric = _metric_name(call.func.value)
    if metric is None:
        return None
    return metric, call.func.attr


def _labels_site(call: ast.Call, mutation_receivers: set[int]) -> tuple[str, str] | None:
    if (
        not isinstance(call.func, ast.Attribute)
        or call.func.attr != "labels"
        or id(call) in mutation_receivers
    ):
        return None
    metric = _metric_name(call.func.value)
    if metric is None:
        return None
    return metric, "labels"


def _is_guard_call(call: ast.Call) -> bool:
    return isinstance(call.func, ast.Name) and call.func.id in _GUARD_FUNCTIONS


def _enclosing_function(node: ast.AST, parents: dict[int, ast.AST]) -> ast.AST | None:
    current = parents.get(id(node))
    while current is not None:
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return current
        current = parents.get(id(current))
    return None


def _guarded_node_ids(tree: ast.AST) -> set[int]:
    parents = {
        id(child): parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)
    }
    nested_defs: defaultdict[tuple[int | None, str], list[ast.AST]] = defaultdict(list)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            parent_function = _enclosing_function(node, parents)
            nested_defs[
                (id(parent_function) if parent_function is not None else None, node.name)
            ].append(node)

    guarded: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _is_guard_call(node):
            continue
        arguments = [*node.args, *(keyword.value for keyword in node.keywords)]
        for argument in arguments:
            guarded.update(id(descendant) for descendant in ast.walk(argument))
            if not isinstance(argument, ast.Name):
                continue
            parent_function = _enclosing_function(node, parents)
            candidates = nested_defs[
                (id(parent_function) if parent_function is not None else None, argument.id)
            ]
            for nested_def in candidates:
                if nested_def.lineno < node.lineno:
                    guarded.update(id(descendant) for descendant in ast.walk(nested_def))
    return guarded


class _SiteCollector(ast.NodeVisitor):
    def __init__(self, path: str, guarded_node_ids: set[int]) -> None:
        self._path = path
        self._guarded_node_ids = guarded_node_ids
        self._function_names: list[str] = []
        self._calls: list[ast.Call] = []
        self._call_function_names: dict[int, str] = {}
        self.sites: list[_MetricSite] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self._function_names.append(node.name)
        self.generic_visit(node)
        self._function_names.pop()

    def visit_Call(self, node: ast.Call) -> None:
        self._calls.append(node)
        self._call_function_names[id(node)] = (
            self._function_names[-1] if self._function_names else "<module>"
        )
        self.generic_visit(node)

    def collect(self) -> list[_MetricSite]:
        mutation_receivers = {
            id(call.func.value)
            for call in self._calls
            if _mutation_site(call) is not None and isinstance(call.func, ast.Attribute)
        }
        for call in self._calls:
            site = _mutation_site(call) or _labels_site(call, mutation_receivers)
            if site is None or id(call) in self._guarded_node_ids:
                continue
            metric, verb = site
            self.sites.append(
                _MetricSite(
                    path=self._path,
                    lineno=call.lineno,
                    metric=metric,
                    verb=verb,
                    function_name=self._call_function_names[id(call)],
                )
            )
        return self.sites


def _collect_unguarded_sites(tree: ast.AST, path: str) -> list[_MetricSite]:
    collector = _SiteCollector(path, _guarded_node_ids(tree))
    collector.visit(tree)
    return collector.collect()


def _parent_nodes(tree: ast.AST) -> dict[int, ast.AST]:
    return {
        id(child): parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)
    }


def _try_position(
    node: ast.AST, try_node: ast.Try, parents: dict[int, ast.AST]
) -> tuple[str, ast.ExceptHandler | None] | None:
    """node가 이 try의 본문(A) 또는 handler(B) 어느 쪽에 있는지 돌려준다."""
    current = node
    while parents.get(id(current)) is not try_node:
        parent = parents.get(id(current))
        if parent is None:
            return None
        current = parent
    if current in try_node.body:
        return "A", None
    if isinstance(current, ast.ExceptHandler):
        return "B", current
    return None


def _handler_result_nodes(handler: ast.ExceptHandler) -> list[ast.AST]:
    """handler의 무조건 실행 경로만 편다 — 중첩 try/if의 분기는 이 handler의 보고가 아니다."""
    result_nodes: list[ast.AST] = []
    pending = list(handler.body)
    while pending:
        node = pending.pop()
        if isinstance(node, (ast.With, ast.AsyncWith)):
            pending.extend(node.body)
            continue
        if isinstance(node, (ast.For, ast.AsyncFor, ast.If, ast.Match, ast.Try, ast.While)):
            continue
        result_nodes.append(node)
    return result_nodes


def _handler_reports_business_result(handler: ast.ExceptHandler) -> bool:
    """rollback·errors_total·failed 로그 중 하나가 handler의 무조건 경로에 있는지 확인한다."""
    for root in _handler_result_nodes(handler):
        for node in ast.walk(root):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Attribute) and node.func.attr == "rollback":
                return True
            if (
                isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "logger"
                and any(
                    isinstance(argument, ast.Constant)
                    and isinstance(argument.value, str)
                    and "failed" in argument.value
                    for argument in node.args
                )
            ):
                return True
            mutation = _mutation_site(node)
            if mutation is not None and mutation[0].endswith("_errors_total"):
                return True
    return False


def _nearest_result_reporting_try_shape(node: ast.AST, parents: dict[int, ast.AST]) -> str | None:
    """예외를 업무 결과로 보고하는 가장 가까운 try에서 node의 A/B 모양을 찾는다."""
    current = parents.get(id(node))
    while current is not None:
        if isinstance(current, ast.Try):
            position = _try_position(node, current, parents)
            if position is None:
                current = parents.get(id(current))
                continue
            shape, handler = position
            handlers = current.handlers if handler is None else [handler]
            if any(_handler_reports_business_result(candidate) for candidate in handlers):
                return shape
        current = parents.get(id(current))
    return None


def _in_scope_census_entries() -> frozenset[tuple[str, str]]:
    """step 0 범위 판정에서 결과 보고 try의 A/B에 든 census 키를 도출한다."""
    return frozenset(key for key, (in_scope, _) in _census_scope_counts().items() if in_scope > 0)


def _harmful_scan_candidates() -> frozenset[tuple[str, str]]:
    """전량 범위 대상과 수동 하한선 제어군을 함께 훑을 후보 집합."""
    return _in_scope_census_entries() | _HARMFUL_MUTATION_CANDIDATES


def _harmful_mutation_sites() -> list[_HarmfulMetricSite]:
    """범위 도출 후보의 raw mutation이 A/B 해로운 try 자리에 남았는지 수집한다."""
    harmful_sites: list[_HarmfulMetricSite] = []
    candidates = _harmful_scan_candidates()
    for path, tree in _source_trees():
        relative_path = path.relative_to(_REPOSITORY_ROOT).as_posix()
        parents = _parent_nodes(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            mutation = _mutation_site(node)
            if mutation is None:
                continue
            metric, _ = mutation
            if (relative_path, metric) not in candidates:
                continue
            shape = _nearest_result_reporting_try_shape(node, parents)
            if shape is None:
                continue
            function = _enclosing_function(node, parents)
            harmful_sites.append(
                _HarmfulMetricSite(
                    path=relative_path,
                    lineno=node.lineno,
                    metric=metric,
                    shape=shape,
                    function_name=(
                        function.name
                        if isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef))
                        else "<module>"
                    ),
                )
            )
    return harmful_sites


def _result_reporting_try_count() -> int:
    """해로운 자리 스캐너가 의존하는 결과 보고 try를 전 소스에서 센다."""
    return sum(
        1
        for _, tree in _source_trees()
        for node in ast.walk(tree)
        if isinstance(node, ast.Try)
        and any(_handler_reports_business_result(handler) for handler in node.handlers)
    )


def _source_trees() -> list[tuple[Path, ast.Module]]:
    return [
        (path, ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
        for path in sorted(_SOURCE_ROOT.rglob("*.py"))
    ]


def _census_sites() -> list[_MetricSite]:
    sites: list[_MetricSite] = []
    for path, tree in _source_trees():
        relative_path = path.relative_to(_REPOSITORY_ROOT).as_posix()
        sites.extend(_collect_unguarded_sites(tree, relative_path))
    return sites


def _census_counts(
    sites: list[_MetricSite], allowlist: dict[tuple[str, str], int]
) -> Counter[tuple[str, str]]:
    return Counter((site.path, site.metric) for site in sites) - Counter(allowlist)


def _census_scope_counts() -> dict[tuple[str, str], tuple[int, int]]:
    """동결 census의 개별 raw mutation을 결과 보고 try 범위로 분류한다."""
    scope_counts = {key: [0, 0] for key in _FROZEN_CENSUS}
    for path, tree in _source_trees():
        relative_path = path.relative_to(_REPOSITORY_ROOT).as_posix()
        parents = _parent_nodes(tree)
        guarded_node_ids = _guarded_node_ids(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or id(node) in guarded_node_ids:
                continue
            mutation = _mutation_site(node)
            if mutation is None:
                continue
            metric, _ = mutation
            key = relative_path, metric
            if key not in scope_counts:
                continue
            is_in_scope = _nearest_result_reporting_try_shape(node, parents) is not None
            scope_counts[key][0 if is_in_scope else 1] += 1
    return {key: (counts[0], counts[1]) for key, counts in scope_counts.items()}


def _census_failure_message(actual: Counter[tuple[str, str]], sites: list[_MetricSite]) -> str:
    added_sites: list[_MetricSite] = []
    for key, actual_count in actual.items():
        frozen_count = _FROZEN_CENSUS.get(key, 0)
        if actual_count > frozen_count:
            key_sites = sorted(
                (site for site in sites if (site.path, site.metric) == key),
                key=lambda site: site.lineno,
            )
            added_sites.extend(key_sites[frozen_count:])

    reduced_entries = [
        (key, actual.get(key, 0))
        for key, frozen_count in _FROZEN_CENSUS.items()
        if actual.get(key, 0) < frozen_count
    ]
    lines = [
        "Metric guard census diverged from the frozen R1 baseline after allowlist exclusion.",
        "159 − 2026-08-02 수리 18 = 141 − 2026-08-03 수리 12 = 129 "
        "− 2026-08-03 수리 25 = 104 − 2026-08-03 수리 8 = 96 − 2026-08-04 수리 12 = 84",
        "★2026-08-24 n9-metric-safety — 동결 합 79 → 63 (`live_signal.py` 16건 수리, 신규 0). "
        "위 체인의 84 는 이 합과 다른 계열이니 이어 붙이지 마라.",
        "새 site (file, lineno, metric, verb, 함수명):",
    ]
    lines.extend(
        f"  ({site.path}, {site.lineno}, {site.metric}, {site.verb}, {site.function_name})"
        for site in sorted(added_sites, key=lambda site: (site.path, site.lineno))
    )
    lines.append("줄어든 항목 (_FROZEN_CENSUS에서 이 항목을 삭제해라):")
    lines.extend(
        f"  {key}: 이 항목을 _FROZEN_CENSUS에서 삭제해라 (실측 {count})"
        for key, count in reduced_entries
    )
    return "\n".join(lines)


def _outcome_leaves(expression: ast.expr) -> list[ast.expr]:
    if isinstance(expression, ast.IfExp):
        return [*_outcome_leaves(expression.body), *_outcome_leaves(expression.orelse)]
    return [expression]


def _guard_outcome_expression(call: ast.Call) -> ast.expr | None:
    for keyword in call.keywords:
        if keyword.arg == "outcome":
            return keyword.value
    return None


def _guard_outcome_calls(tree: ast.AST) -> list[ast.Call]:
    calls: list[ast.Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "labels"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "qb_live_conditional_guard_total"
        ):
            calls.append(node)
        if (
            isinstance(node.func, ast.Name)
            and node.func.id == "_count_safely"
            and node.args
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id == "qb_live_conditional_guard_total"
        ):
            calls.append(node)
    return calls


def test_census_rule_is_stated_in_the_failure_message() -> None:
    for required_text in ("(a)", "(b)", "(i)", "(ii)", "(iii)", "(iv)", "못 잡는 것"):
        assert required_text in _CENSUS_RULE_FAILURE_MESSAGE


def test_census_rule_classifies_the_synthetic_fixture() -> None:
    fixture = ast.parse(
        """
qb_a.inc()
record_metric_safely(lambda: qb_b.labels(x="y").inc())
record_metric_safely(qb_c.dec)

def bump():
    qb_d.inc()

record_metric_safely(bump)
qb_fixture.labels(x="y")
qb_multiline.labels(
    x="y",
).inc()
c = qb_e
c.inc()
"""
    )

    sites = _collect_unguarded_sites(fixture, "synthetic.py")
    actual = {(site.metric, site.verb) for site in sites}
    expected = {
        ("qb_a", "inc"),
        ("qb_fixture", "labels"),
        ("qb_multiline", "inc"),
    }

    assert actual == expected
    assert sum(site.metric == "qb_multiline" for site in sites) == 1
    assert all(site.metric != "qb_e" for site in sites), "별칭 c = qb_e; c.inc()는 잡지 못한다"
    assert all(site.metric not in {"qb_b", "qb_c", "qb_d"} for site in sites)


def test_unguarded_mutation_counts_match_the_frozen_census() -> None:
    assert len(_FROZEN_CENSUS) == 17
    assert sum(_FROZEN_CENSUS.values()) == 30

    sites = _census_sites()
    actual = _census_counts(sites, _CENSUS_ALLOWLIST)

    assert actual == _FROZEN_CENSUS, _census_failure_message(actual, sites)


def test_census_allowlist_entries_exist_and_are_required() -> None:
    sites = _census_sites()
    without_allowlist = _census_counts(sites, {})

    assert {key: without_allowlist[key] for key in _CENSUS_ALLOWLIST} == _CENSUS_ALLOWLIST
    assert without_allowlist != _FROZEN_CENSUS


def test_census_scope_classification_matches_the_frozen_map() -> None:
    assert _census_scope_counts() == _FROZEN_CENSUS_SCOPE


def test_census_scope_totals_reconcile_with_the_census() -> None:
    actual = _census_scope_counts()

    assert actual.keys() == _FROZEN_CENSUS.keys()
    assert all(
        in_scope + out_of_scope == _FROZEN_CENSUS[key]
        for key, (in_scope, out_of_scope) in actual.items()
    )


def test_census_scope_scanner_is_not_vacuous() -> None:
    fixture = ast.parse(
        """
try:
    qb_census_scope.inc()
except Exception:
    logger.error("business operation failed")
"""
    )
    mutation = next(
        node
        for node in ast.walk(fixture)
        if isinstance(node, ast.Call) and _mutation_site(node) == ("qb_census_scope", "inc")
    )

    assert _result_reporting_try_count() >= 1
    assert _nearest_result_reporting_try_shape(mutation, _parent_nodes(fixture)) == "A"


def test_known_harmful_mutation_sites_are_gone_with_try_scan_control() -> None:
    """0건 단언은 결과 보고 try 양성 대조와 함께만 허용한다 (2026-08-24 실측 138건)."""
    actual = _harmful_mutation_sites()
    reporting_try_count = _result_reporting_try_count()

    assert not actual, actual
    assert reporting_try_count >= 100, (
        "결과 보고 try 스캐너가 100곳 미만만 훑었다 — 해로운 자리 0건은 대상 미도달로도 참이다: "
        f"{reporting_try_count}"
    )


def test_harmful_scan_covers_every_in_scope_census_entry() -> None:
    assert _harmful_scan_candidates() >= _in_scope_census_entries()


def test_harmful_candidate_lower_bound_is_still_covered() -> None:
    assert _harmful_scan_candidates() >= _HARMFUL_MUTATION_CANDIDATES


def test_harmful_sites_are_empty_with_a_positive_control() -> None:
    actual = _harmful_mutation_sites()

    assert not actual, actual
    assert _result_reporting_try_count() >= 1


def test_guard_outcome_literals_are_all_allowed() -> None:
    violations: list[str] = []
    for path, tree in _source_trees():
        relative_path = path.relative_to(_REPOSITORY_ROOT).as_posix()
        for call in _guard_outcome_calls(tree):
            expression = _guard_outcome_expression(call)
            if expression is None:
                violations.append(f"{relative_path}:{call.lineno}: outcome= is required")
                continue
            for leaf in _outcome_leaves(expression):
                if not isinstance(leaf, ast.Constant) or not isinstance(leaf.value, str):
                    violations.append(
                        f"{relative_path}:{leaf.lineno}: outcome leaf is not a static string literal: "
                        f"{ast.unparse(leaf)}"
                    )
                    continue
                if leaf.value not in _LIVE_CONDITIONAL_GUARD_OUTCOMES:
                    violations.append(
                        f"{relative_path}:{leaf.lineno}: unsupported outcome literal {leaf.value!r}"
                    )

    assert not violations, "\n".join(violations)


# ---------------------------------------------------------------------------
# 보호 목록 (L2) — CONTROL 이 손으로 동결한다. ★추론하지 않는다.
#
# 왜 추론을 안 쓰나: 「머니-패스」 zone 을 AST 로 추론하려 세 번 시도했고 정의를 조금씩
# 바꿀 때마다 6 / 13 / 14 곳으로 흔들렸다(2026-08-02). 그중 「6곳」은 프로토타입에 박아둔
# 임의의 40줄 창이 만든 값이었다. ⇒ 머니-패스 여부는 구문에서 추론할 수 없다.
# 신규 유입 차단은 위 census 천장이 담당하고, 이 목록은 **무엇을 왜 지키는지**를 고정한다.
#
# ★★2026-08-04 `live_signal.py` 해체의 **순이득 — 두 자리가 처음으로 각각 집행된다.**
#   해체 전에는 `qb_live_conditional_reconcile_errors_total` 두 항목이 삼중항
#   `(tasks/live_signal.py, _reconcile_conditional_entries, …)` 로 **완전히 동일**했다.
#   오라클(`test_every_protected_site_is_actually_guarded`)은 「그 함수에 가드된 mention 이
#   1개 이상」만 보므로 **둘 중 하나만 남겨도 통과**했다 — 즉 한 자리는 집행되지 않았다.
#   해체 후 두 항목은 서로 다른 함수를 가리킨다:
#     · 「지연 return」  → `_place_planned_entry`
#     · 「stand-down 직전」→ `_resolve_current_position`
#
# ★★그래서 **앵커를 이 오라클로 검증하지 마라.** 오라클은 같은 함수에 그 metric 의 다른
#   가드가 하나라도 있으면 통과하므로 **틀린 함수를 적어도 green 이다.** 실제로 해체 1단계에서
#   두 항목이 옛 함수를 가리킨 채 통과했다(다른 두 항목은 red 였다 — 그래서 더 헷갈린다).
#   갱신할 때는 **이유 문자열이 가리키는 앵커 행이 새 함수의 행 범위 안인지 숫자로 확인해라.**
#
# ★`(파일, 함수, metric)` 이 겹치는 항목이 `tasks/trading.py` 2건 ·
#   `conditional_entry_janitor.py` 1건 남아 있다(이번 회차 범위 밖). 같은 이유로 각각
#   집행되지 않고 있으니, 그 파일을 손볼 때 함께 갈라라.
# ---------------------------------------------------------------------------

_PROTECTED_SITES: tuple[tuple[str, str, str, str], ...] = (
    # (파일, 함수, metric, 이유)
    # Tier 1 — 주문 접수·실행 enqueue 성공 직후. 던지면 성공이 실패로 기록된다.
    (
        "apps/api/src/tasks/live_signal.py",
        "_place_planned_entry",
        "qb_live_conditional_placed_total",
        "성공 접수를 stage=conditional_place 실패로 계상",
    ),
    (
        "apps/api/src/tasks/live_signal.py",
        "_place_planned_entry",
        "qb_live_conditional_guard_total",
        "위와 같음 + _GuardOutcomeCounter 는 ValueError 도 던진다",
    ),
    (
        "apps/api/src/tasks/live_signal.py",
        "_place_planned_entry",
        "qb_live_conditional_reconcile_errors_total",
        "지연 return 을 건너뛰어 낡은 스냅샷 위 과잉 등재 (실측: execute await 2회)",
    ),
    (
        "apps/api/src/tasks/trading.py",
        "_do_place_trailing_stop",
        "qb_trailing_placement_total",
        "중복 set_trading_stop + 거짓 trailing_unprotected critical alert",
    ),
    # Tier 2 — 내구 쓰기와 체결 후처리 훅 사이의 gauge. 던지면 후처리가 통째로 유실된다.
    (
        "apps/api/src/trading/websocket/state_handler.py",
        "handle_order_event",
        "qb_active_orders",
        "WS fill 주 경로. 23줄 아래 가드와 그 전용 회귀 테스트를 도달 불가로 만든다",
    ),
    (
        "apps/api/src/tasks/trading.py",
        "_execute_with_session",
        "qb_active_orders",
        "REST 동기 fill. max_retries=0 이라 회수 경로가 없다",
    ),
    (
        "apps/api/src/tasks/trading.py",
        "_fetch_order_status_with_session",
        "qb_active_orders",
        "watchdog fill",
    ),
    (
        "apps/api/src/trading/websocket/reconciliation.py",
        "run",
        "qb_active_orders",
        "reconciler fill",
    ),
    (
        "apps/api/src/tasks/conditional_entry_janitor.py",
        "_async_conditional_entry_janitor",
        "qb_active_orders",
        "janitor fill",
    ),
    (
        "apps/api/src/tasks/live_signal.py",
        "_write_back_confirmed_terminal",
        "qb_active_orders",
        "BL-567 이 '트레일링 영구 유실' 로 등재한 격리 블록의 한 줄 위",
    ),
    # ★2026-08-02 codex G6 Spec MAJOR 로 추가된 7곳 — 같은 결함 형태가 **내가 이미 고친
    #   파일 안에** 남아 있었다. 4곳은 `commit()` **앞**이라 더 나쁘다(계측 예외가 terminal
    #   DB 전이를 rollback 시킨다).
    (
        "apps/api/src/tasks/live_signal.py",
        "_cancel_planned_entry",
        "qb_live_conditional_cancelled_total",
        "거래소 취소 성공 뒤. except 가 stage=cancel 실패로 계상하고 이후 reconcile 중단",
    ),
    (
        "apps/api/src/tasks/live_signal.py",
        "_async_sweep_conditional_entries",
        "qb_active_orders",
        "★commit 앞 + except 가 rollback — 계측 예외가 terminal DB 전이를 되돌린다",
    ),
    (
        "apps/api/src/tasks/live_signal.py",
        "_async_sweep_conditional_entries",
        "qb_live_conditional_sweep_filled_total",
        "체결 발견 뒤 — 예외가 rollback + sweep_cancel_failed로 실제 체결을 취소 실패로 오기록",
    ),
    (
        "apps/api/src/tasks/conditional_entry_janitor.py",
        "_async_conditional_entry_janitor",
        "qb_active_orders",
        "★commit 앞 + rollback (2곳)",
    ),
    (
        "apps/api/src/tasks/trading.py",
        "_execute_with_session",
        "qb_active_orders",
        "reject 경로 commit 뒤 (2곳). 같은 문자열이 3곳이라 하나만 남기면 잘못된 패턴이 복제된다",
    ),
    (
        "apps/api/src/tasks/trading.py",
        "_fetch_order_status_with_session",
        "qb_active_orders",
        "같은 형태 — 일관성 유지",
    ),
    # ★2026-08-03 metric-guard-residual — 고장 주입으로 귀결을 **실측**하고 감싼 12곳.
    #   근거는 산문이 아니라 테스트다: `tests/trading/test_router_cancel_metric_failure.py` ·
    #   `tests/trading/test_trading_task_metric_failure.py` ·
    #   `tests/tasks/test_live_signal_metric_failure.py`.
    #   ★`_FROZEN_CENSUS` 는 `(파일, metric)` **합계**뿐이라 위치를 잃는다 — 같은 파일·metric 에
    #   새 raw 가 생기고 여기 자리가 raw 로 되돌아가면 **상쇄돼 통과**한다(2026-08-02 codex G1
    #   MAJOR#7). 그래서 자리마다 여기에 남긴다.
    (
        "apps/api/src/trading/router.py",
        "cancel_order",
        "qb_active_orders",
        "commit 뒤 — 던지면 확정된 취소가 HTTP 500 으로 보고된다 (H1, 주입 확인)",
    ),
    (
        "apps/api/src/tasks/trading.py",
        "_cancel_order_with_session",
        "qb_active_orders",
        "commit 뒤 + 바로 아래 로그가 거래소 취소를 남기는 유일한 라인 (H1)",
    ),
    (
        "apps/api/src/tasks/live_signal.py",
        "_resolve_current_position",
        "qb_live_conditional_reconcile_errors_total",
        "★stand-down 직전 — 던지면 잘못된 전제 위 조건부 진입이 거래소에 남는다 (H4)",
    ),
    (
        "apps/api/src/tasks/live_signal.py",
        "_block_on_direction_divergence",
        "qb_live_signal_divergence_total",
        "★세션 자동 비활성화 commit 뒤 · 무신호 차단 고지 앞 — 세션이 조용히 죽는다 (H2)",
    ),
    (
        "apps/api/src/tasks/live_signal.py",
        "_block_on_direction_divergence",
        "qb_live_signal_evaluated_total",
        "위와 같은 블록 — 둘 다 감싸야 고지에 도달한다",
    ),
    # ★2026-08-03 metric-guard-residual-close — 고장 주입 25곳(전건 「수리함」).
    #   BL-580 이 산문으로 뺐던 두 근거가 **둘 다 반증**됐다:
    #   ① 「order_service.py 10곳은 blast radius 0」 → 10/10 이 도메인 예외 대신 OSError 를
    #      탈출시킨다(4xx → 500, 그중 6종은 호출자 타입 분기까지 건너뛴다).
    #   ② 「closed_pnl 은 already_synced 로 수렴」 → 수렴 논거가 닿는 자리는 7곳 중 1곳뿐.
    #   정본: `tests/trading/test_order_rejected_metric.py` ·
    #   `tests/tasks/test_closed_pnl_refresh_metric_failure.py` ·
    #   `tests/tasks/test_closed_pnl_sweep_metric_failure.py` ·
    #   `tests/tasks/test_refresh_closed_pnl.py`.
    (
        "apps/api/src/trading/services/order_service.py",
        "_execute_inner",
        "qb_order_rejected_total",
        "★거절 8곳 — 도메인 예외가 삼켜지면 4xx 가 500 이 되고 호출자 기록 분기가 빠진다 (H5·H4)",
    ),
    (
        "apps/api/src/trading/services/order_service.py",
        "_validate_position_size",
        "qb_order_rejected_total",
        "risk 사이징 거절 — 구체 타입 catch 는 없지만 4xx 가 500 이 된다 (H5)",
    ),
    (
        "apps/api/src/tasks/trading.py",
        "_refresh_closed_pnl_with_session",
        "qb_closed_pnl_backfill_total",
        "★종결 skip 5곳 + applied/already_synced — 정상 종결이 재시도로 오분류된다 (H6·H1)",
    ),
    (
        "apps/api/src/tasks/trading.py",
        "refresh_closed_pnl_task",
        "qb_closed_pnl_backfill_total",
        "★포기 알림 바로 앞 — 던지면 알림이 1건 더가 아니라 0건이 된다 (H2)",
    ),
    (
        "apps/api/src/tasks/trading.py",
        "_sweep_closed_pnl_with_session",
        "qb_closed_pnl_backfill_total",
        "★계정 격리 handler 의 첫 줄 + 신규 청산 알림 앞 + 원장 적재 앞 (H4·H2·H7)",
    ),
    (
        "apps/api/src/tasks/trading.py",
        "_sweep_closed_pnl_with_session",
        "qb_exchange_exit_link_unverified_total",
        "청산 원장 행 관측 뒤 — 예외가 계정 격리 handler로 가서 이 계정 스윕 후속 처리를 중단",
    ),
    # ★2026-08-24 n7-metric-guard-sweep 모양 B — except 본문의 계측 실패는 잡은 예외까지
    #   다시 누출시킨다. 두 자리는 각각 Redis 발행 실패와 심볼 거절의 응답 경로다.
    (
        "apps/api/src/trading/realtime_publisher.py",
        "_publish_envelope",
        "qb_rt_publish_failed_total",
        "발행 실패 handler 안 — 계측 예외가 원래 Redis 발행 예외를 상위 경로로 누출",
    ),
    (
        "apps/api/src/trading/webhook.py",
        "_normalized_symbol_or_reject",
        "qb_webhook_symbol_rejected_total",
        "심볼 거절 handler 안 — 계측 예외가 원래 ValueError와 웹훅 응답 경로를 함께 누출",
    ),
    # ★2026-08-03 metric-guard-residual-sweep — 라이브 발주 outbox 경로 8곳(전건 「수리함」).
    #   전부 `mark_failed`/`mark_dispatched` + `commit()` **뒤**이고, 호출자
    #   `dispatch_live_signal_event_task:2793` 이 **예외 타입으로** 재시도를 가른다 ⇒ 계측이
    #   던지면 종결이 재시도로 오분류된다(H6). 정본 = `tests/tasks/test_live_signal_metric_failure.py`.
    #   ★★★**사전등록이 한 자리에서 반증됐다** — `:3133`(close_position_flat)만 fail-open
    #      `try` 안이라, 계측 예외를 `except` 가 「포지션 조회 실패」로 오인해 삼키고 **그대로
    #      발주한다**. 오기록이 아니라 **거절이 집행으로 뒤집히는** 자리다(신규 라벨 H8).
    #   ★이 함수는 metric 이 하나뿐이라 아래 `(파일, 함수, metric)` 삼중항은 **과선택**한다 —
    #    「이 함수에 가드된 dispatch_total 이 1개 이상」만 집행한다. **자리별 집행은 census
    #    천장**(`test_unguarded_mutation_count...`)이 한다. 잔여 4곳이 raw 로 남아 있으므로
    #    수리한 자리가 raw 로 되돌아가면 그 `(파일, metric)` 개수가 4를 넘어 red 가 된다.
    (
        "apps/api/src/tasks/live_signal.py",
        "_async_dispatch_event",
        "qb_live_signal_dispatch_total",
        "★발주 outbox 종결 7곳 — flat 청산 거부가 집행으로 뒤집히고(H8), "
        "kill-switch·도메인 거절의 타입이 소실돼 무재시도 분기를 건너뛴다 (H6·H5)",
    ),
    (
        "apps/api/src/tasks/live_signal.py",
        "dispatch_live_signal_event_task",
        "qb_live_signal_dispatch_total",
        "★재시도 소진 포기 기록 — 던지면 포기 반환이 사라지고 사유가 어디에도 안 남는다 (H6·H2)",
    ),
)

# ★공허화 방지 (codex G6 Standards MAJOR) — 목록이 비면 아래 두 테스트가 **반복할 항목이
#   없어 통과**한다. 그건 검증이 아니라 침묵이다.
assert _PROTECTED_SITES, "보호 목록이 비었다 — 이 테스트 파일은 아무것도 집행하지 않는다"


def _references_metric(node: ast.AST, metric: str) -> bool:
    """가드 인자 서브트리의 한 노드가 그 metric 을 가리키는가.

    세 형태를 덮는다:
    (a) ``record_metric_safely(qb_x.dec)`` — bound method 를 인자로 넘김
    (b) ``_count_safely(qb_x, ...)`` — counter 자체를 인자로 넘김
    (c) ``record_metric_safely(lambda: qb_x.labels(...).inc())`` — lambda 안 체인
    """
    if (
        isinstance(node, ast.Attribute)
        and node.attr in _MUTATION_METHODS
        and isinstance(node.value, ast.Name)
        and node.value.id == metric
    ):
        return True
    if isinstance(node, ast.Name) and node.id == metric:
        return True
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and _metric_name(node.func.value) == metric
    )


def _guarded_metric_mentions(tree: ast.Module, function_name: str, metric: str) -> int:
    """해당 함수 안에서 그 metric 이 **가드의 인자로 구조적으로** 들어간 횟수.

    ★1차 구현은 `metric in ast.unparse(call)` 이라는 **문자열 포함**이었다 (2026-08-02 codex G6
    Standards MAJOR). 그러면 같은 이름이 주석·다른 인자에 스치기만 해도 통과하고, 같은 함수의
    **다른** mutation 을 감싸 놓고 목표 자리를 raw 로 되돌려도 통과한다. ⇒ AST 로 본다:
    가드 호출의 인자 서브트리 안에서 그 metric 을 뿌리로 하는 mutation/labels 노드를 찾는다.
    """
    found = 0
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name != function_name:
            continue
        for inner in ast.walk(node):
            if not isinstance(inner, ast.Call):
                continue
            name = (
                inner.func.id
                if isinstance(inner.func, ast.Name)
                else getattr(inner.func, "attr", None)
            )
            if name not in _GUARD_FUNCTIONS:
                continue
            for argument in list(inner.args) + [kw.value for kw in inner.keywords]:
                found += sum(1 for sub in ast.walk(argument) if _references_metric(sub, metric))
    return found


def test_every_protected_site_is_actually_guarded() -> None:
    """동결한 보호 자리 각각에 **가드된** mutation 이 실재하는지 확인한다.

    ★★이 테스트가 집행하는 것과 하지 않는 것을 정확히 적는다 (2026-08-02, 내가 한 번 틀렸다).

    **하지 않는 것:** 「이 함수 안에 그 metric 의 가드 밖 mutation 이 0개」를 요구하지 **않는다.**
    처음엔 그렇게 썼다가 red 가 났다 — `_reconcile_conditional_entries` 안의
    `qb_live_conditional_guard_total` 은 **9곳**이고 이번 회차가 감싼 것은 그중 발주 직후 1곳뿐이다.
    `(파일, 함수, metric)` 삼중항은 **과선택한다.** zone 추론이 6/13/14 로 흔들린 것과 같은 병이다.

    **집행은 위 census 천장이 한다.** 보호 site 를 raw 로 되돌리면 그 `(파일, metric)` 개수가
    올라가 `test_unguarded_mutation_count_per_file_matches_record` 가 red 가 된다. 실측 확인됨.

    **이 테스트의 몫:** 가드가 통째로 사라지는 것(리팩터링·되돌림)을 잡고, **무엇을 왜 지키는지**를
    코드 안에 남긴다.
    """
    missing = [
        f"{path}::{function} 에 {metric} 의 가드된 mutation 이 없다 — {reason}"
        for path, function, metric, reason in _PROTECTED_SITES
        if _guarded_metric_mentions(
            {p.relative_to(_REPOSITORY_ROOT).as_posix(): t for p, t in _source_trees()}[path],
            function,
            metric,
        )
        == 0
    ]
    assert not missing, "\n".join(missing)


def test_protected_site_list_is_not_vacuous() -> None:
    """공허화 방지 — 함수가 사라지거나 가드가 통째로 빠지면 '0건이라 통과' 가 아니라 red."""
    trees = {path.relative_to(_REPOSITORY_ROOT).as_posix(): tree for path, tree in _source_trees()}
    problems: list[str] = []
    for path, function, metric, _reason in _PROTECTED_SITES:
        tree = trees.get(path)
        if tree is None:
            problems.append(f"{path} 가 없다 — 보호 목록을 갱신해라")
            continue
        names = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        if function not in names:
            problems.append(f"{path}::{function} 가 없다 (rename?) — 보호 목록을 갱신해라")
            continue
        if _guarded_metric_mentions(tree, function, metric) == 0:
            problems.append(
                f"{path}::{function} 에 {metric} 의 **가드된** mutation 이 0개다 — "
                "자리가 비었으면 통과가 아니라 갱신 대상이다"
            )
    assert not problems, "\n".join(problems)


@pytest.mark.parametrize(("path", "metric"), sorted(_HARMFUL_MUTATION_CANDIDATES))
def test_each_harmful_candidate_has_a_runtime_protection_contract(path: str, metric: str) -> None:
    """수동 동결한 해로운 후보가 보호 목록에서 빠져 static census만 남는 것을 막는다."""
    protected = {
        (site_path, site_metric) for site_path, _function, site_metric, _reason in _PROTECTED_SITES
    }

    assert (path, metric) in protected
