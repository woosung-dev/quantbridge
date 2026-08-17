"""[BL-788] `SQLModel.metadata` 등록 **범위** 자체에 검사면을 세운다.

## 왜 이 파일이 필요한가

`tests/conftest.py` 의 `bootstrap_test_schema` 는 `SQLModel.metadata.create_all` 로 테스트
스키마를 만든 뒤 `alembic_version` 을 **head 로 stamp** 한다. `create_all` 이 만드는 것은
「그 순간 metadata 에 등록된」 테이블뿐이므로, 등록이 빠진 테이블은 **만들어지지 않은 채
head 라고 적힌 DB** 가 된다. 2026-08-17 에 `auth_*` 5테이블이 정확히 그 모양이었다
(`conftest.py:356` 주석 참조 — fresh DB 에서만 터지고 재사용 DB 에서는 조용했다).

## ★기존 검사면이 이 결함군을 못 보는 이유

`tests/test_migrations.py::test_alembic_schema_matches_sqlmodel_metadata` 는
`SQLModel.metadata.tables` 를 **순회**해서 DB 와 대조한다. metadata 에서 빠진 테이블은
순회 대상 자체가 아니므로 **정의상 보이지 않는다** — 이 결함군에 대해 항진명제다.

## ★in-process 단언이 안 되는 이유

이 테스트가 도는 시점에는 pytest 수집이 이미 `tests/**` 전 모듈을 import 해서 metadata 가
꽉 차 있다. 「지금 metadata 에 24개 있다」를 여기서 재면 무엇을 지워도 초록이다.
그래서 ⑶은 **자식 프로세스**에서 `tests.conftest` **만** import 한 결과를 잰다
(선례: `tests/test_destructive_db_guard.py:70 _collect()`).

## 무엇을 SSOT 로 삼는가

★기대치를 이 파일에 **적지 않는다**. `src/**/*.py` 를 AST 로 훑어 `__tablename__ = "..."`
와 `sa.Table("...", SQLModel.metadata, ...)` 를 **세는 것**이 SSOT 다. 즉 모델을 새로 추가하면
그 사실 자체가 기대치를 늘린다. `alembic/env.py` 를 SSOT 로 쓰지 않는 이유는 그 파일도
같은 종류의 손 목록이라서다 — 대신 ⑵가 **env.py 를 이 census 로 검사한다**.

## 세 다리

- ⑴ `tests/conftest.py` 가 표를 선언하는 모든 모듈을 **명시 import** 하는가 (선언 축)
- ⑵ `alembic/env.py` 가 같은 것을 하는가 (SSOT 를 자칭하는 쪽도 검사한다)
- ⑶ `tests.conftest` **만** import 한 자식에서 실제 등록 테이블 = census 인가 (실행 축)

★⑴이 ⑶과 별개로 필요하다. 2026-08-17 실측 — conftest 의 `from src.main import create_app`
는 `src/main.py:447` 의 `app = create_app()` 을 태우고, 그것이 stress_test router →
dependencies → service 를 지나 `src.optimizer.models` 를 **우연히** 끌어온다. 그래서
`optimization_runs` 는 conftest 목록에 없는데도 등록돼 있었다. 그 배선 중 한 칸이라도
지연 import 로 바뀌면 조용히 사라진다 — ⑴은 그 우연에 기대지 않겠다는 단언이다.
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_SRC_ROOT = _BACKEND_ROOT / "src"
_CONFTEST = _BACKEND_ROOT / "tests" / "conftest.py"
_ALEMBIC_ENV = _BACKEND_ROOT / "alembic" / "env.py"

# 자식 stdout 은 로깅 설정(`configure_logging`)이 섞일 수 있다. 표식 줄만 골라 읽는다.
_DUMP_MARKER = "QB-METADATA-TABLES "

_DUMP_SCRIPT = (
    "import json, sys\n"
    "import tests.conftest  # noqa: F401 — 이 한 줄이 create_all 범위를 정한다\n"
    "from sqlmodel import SQLModel\n"
    f"sys.stdout.write({_DUMP_MARKER!r} + json.dumps(sorted(SQLModel.metadata.tables)) + chr(10))\n"
)


# ---------------------------------------------------------------------------
# census — `src/**` 가 선언하는 테이블. 이 파일의 유일한 기대치 원천이다.
# ---------------------------------------------------------------------------


def _module_name(path: Path) -> str:
    """`apps/api/src/auth/models.py` → `src.auth.models`."""
    rel = path.relative_to(_BACKEND_ROOT).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _tables_declared_in(path: Path) -> frozenset[str]:
    """한 파일이 선언하는 테이블 이름 — `__tablename__` 대입 + `Table("name", ...)` 호출."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            if isinstance(node.value.value, str) and any(
                isinstance(t, ast.Name) and t.id == "__tablename__" for t in node.targets
            ):
                found.add(node.value.value)
        elif isinstance(node, ast.Call):
            func = node.func
            is_table_ctor = (isinstance(func, ast.Attribute) and func.attr == "Table") or (
                isinstance(func, ast.Name) and func.id == "Table"
            )
            if (
                is_table_ctor
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                found.add(node.args[0].value)
    return frozenset(found)


def _table_declaring_modules() -> dict[str, frozenset[str]]:
    """표를 하나라도 선언하는 `src.*` 모듈 → 그 표 이름 집합."""
    out: dict[str, frozenset[str]] = {}
    for path in sorted(_SRC_ROOT.rglob("*.py")):
        tables = _tables_declared_in(path)
        if tables:
            out[_module_name(path)] = tables
    return out


# ---------------------------------------------------------------------------
# 손 목록 파서 — 어떤 파일이 어떤 `src.*` 모듈을 **명시 import** 하는가
# ---------------------------------------------------------------------------


def _resolve(module: str, name: str | None) -> str:
    """`from src.auth import better_auth_tables` 의 대상이 모듈인지 심볼인지 **디스크로** 가른다.

    import 를 시도하지 않는다 — 부작용 없이 결정적이어야 하기 때문이다.
    """
    if name is None:
        return module
    base = _BACKEND_ROOT.joinpath(*module.split("."))
    if (base / f"{name}.py").exists() or (base / name / "__init__.py").exists():
        return f"{module}.{name}"
    return module


def _imported_src_modules(path: Path) -> frozenset[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "src" or alias.name.startswith("src."):
                    out.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # 상대 import 는 `src.*` 가 아니다
                continue
            module = node.module or ""
            if module != "src" and not module.startswith("src."):
                continue
            for alias in node.names:
                out.add(_resolve(module, alias.name))
    return frozenset(out)


def _assert_census_is_not_empty(census: dict[str, frozenset[str]]) -> None:
    """★빈 census 는 모든 차집합 단언을 항진명제로 만든다 — 그 전에 죽인다."""
    assert census, (
        f"census 가 비었다. `{_SRC_ROOT}` 에서 `__tablename__`/`Table(...)` 를 하나도 못 찾았다 — "
        "경로가 틀렸거나 파서가 죽은 것이다. 이 상태로는 아래 비교가 무엇이든 통과한다."
    )


# ---------------------------------------------------------------------------
# ⑴ 선언 축 — conftest 의 손 목록
# ---------------------------------------------------------------------------


def test_conftest_imports_every_table_declaring_module() -> None:
    """red 면 고장난 것: 어떤 모델의 테이블이 `create_all` 범위 밖인데 DB 는 head 로 stamp 된다.

    ★고치는 법 = `tests/conftest.py` 머리에 `# noqa: F401 — metadata 등록` 주석과 함께
      그 모듈 import 를 추가한다. 전이 import 로 우연히 등록되고 있더라도 추가해라 —
      그 우연은 다른 파일의 배선이 바뀌면 사라진다.
    """
    census = _table_declaring_modules()
    _assert_census_is_not_empty(census)

    declared = _imported_src_modules(_CONFTEST)
    missing = {m: sorted(census[m]) for m in sorted(set(census) - declared)}

    assert not missing, (
        f"`tests/conftest.py` 가 명시 import 하지 않는 표 선언 모듈: {missing}. "
        "그 테이블은 `bootstrap_test_schema` 의 create_all 범위에 들어간다는 보장이 없다."
    )


# ---------------------------------------------------------------------------
# ⑵ 같은 축 — alembic/env.py. autogenerate·`alembic check` 가 보는 범위다.
# ---------------------------------------------------------------------------


def test_alembic_env_imports_every_table_declaring_module() -> None:
    """red 면 고장난 것: `alembic check` 가 그 테이블을 **removed table** 로 오인한다([BL-770]).

    ⑴과 같은 결함군이지만 피해가 다르다 — 이쪽은 운영 DB 를 향하는 migration 을 잘못 만든다.
    """
    census = _table_declaring_modules()
    _assert_census_is_not_empty(census)

    declared = _imported_src_modules(_ALEMBIC_ENV)
    missing = {m: sorted(census[m]) for m in sorted(set(census) - declared)}

    assert not missing, (
        f"`alembic/env.py` 가 명시 import 하지 않는 표 선언 모듈: {missing}. "
        "그 테이블은 autogenerate/`alembic check` 의 metadata 쪽에 없다."
    )


# ---------------------------------------------------------------------------
# ⑶ 실행 축 — 자식 프로세스에서 `tests.conftest` 만 import 했을 때 실제 등록 결과
# ---------------------------------------------------------------------------


def _tables_registered_by_conftest_import() -> frozenset[str]:
    proc = subprocess.run(
        [sys.executable, "-c", _DUMP_SCRIPT],
        cwd=_BACKEND_ROOT,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert proc.returncode == 0, (
        f"자식 프로세스가 `import tests.conftest` 에서 죽었다 (rc={proc.returncode}).\n"
        f"--- stderr ---\n{proc.stderr}\n--- stdout ---\n{proc.stdout}"
    )
    payloads = [
        line[len(_DUMP_MARKER) :]
        for line in proc.stdout.splitlines()
        if line.startswith(_DUMP_MARKER)
    ]
    assert len(payloads) == 1, (
        f"자식이 표식 줄을 정확히 한 번 내지 않았다 (found={len(payloads)}). "
        f"stdout 오염 또는 스크립트 파손.\n--- stdout ---\n{proc.stdout}"
    )
    return frozenset(json.loads(payloads[0]))


def test_conftest_import_alone_registers_every_declared_table() -> None:
    """red 면 고장난 것: `pytest tests/<한 파일>` 처럼 **부분 실행**할 때 스키마가 모자란다.

    ★전량 실행에서는 수집이 `tests/**` 를 다 import 하므로 이 결함이 가려진다.
      `_test_engine` 은 session fixture라 create_all 이 **수집 이후**에 돌기 때문이다.
      자식에서 `tests.conftest` 만 import 하는 것이 그 가림막을 걷는 유일한 방법이다.
    """
    census = _table_declaring_modules()
    _assert_census_is_not_empty(census)

    expected: set[str] = set()
    for tables in census.values():
        expected |= set(tables)

    registered_keys = _tables_registered_by_conftest_import()
    assert registered_keys, "자식이 빈 metadata 를 냈다 — 비교가 항진명제가 된다."

    # metadata key 는 schema 가 붙는다(`trading.orders`, `ts.ohlcv`). census 는 맨이름이므로
    # 맨이름으로 내린다. ★내리면서 뭉치면 비교가 느슨해지므로 충돌부터 막는다.
    registered = {key.rsplit(".", 1)[-1] for key in registered_keys}
    assert len(registered) == len(registered_keys), (
        f"schema 를 떼자 이름이 충돌했다: {sorted(registered_keys)}. "
        "이 비교는 맨이름 유일성을 전제한다 — 전제가 깨졌으니 검사기를 고쳐라."
    )

    assert registered == expected, (
        f"등록 누락(census 에 있는데 자식에 없음): {sorted(expected - registered)} / "
        f"정체불명(자식에 있는데 census 에 없음): {sorted(registered - expected)}"
    )
