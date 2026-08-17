"""[BL-788] `SQLModel.metadata` 등록 **범위** 자체에 검사면을 세운다.

## 왜 이 파일이 필요한가

`tests/conftest.py` 의 `bootstrap_test_schema` 는 `SQLModel.metadata.create_all` 로 테스트
스키마를 만든 뒤 `alembic_version` 을 **head 로 stamp** 한다. `create_all` 이 만드는 것은
「그 순간 metadata 에 등록된」 테이블뿐이므로, 등록이 빠진 테이블은 **만들어지지 않은 채
head 라고 적힌 DB** 가 된다. 2026-08-17 에 `auth_*` 5테이블이 정확히 그 모양이었다
(`conftest.py` 의 「★`create_all` 이 만드는 것은 **이 순간 metadata 에 등록된** 테이블뿐이다」
주석 참조 — fresh DB 에서만 터지고 재사용 DB 에서는 조용했다). ★줄 번호로 가리키지 않는다:
초판은 `conftest.py:356` 이라 적었는데 같은 커밋이 그 파일 머리에 7줄을 넣어 곧바로 낡았다.

## ★기존 검사면이 이 결함군을 못 보는 이유

`tests/test_migrations.py::test_alembic_schema_matches_sqlmodel_metadata` 는
`SQLModel.metadata.tables` 를 **순회**해서 DB 와 대조한다. metadata 에서 빠진 테이블은
순회 대상 자체가 아니므로 **정의상 보이지 않는다** — 이 결함군에 대해 항진명제다.

## ★in-process 단언이 안 되는 이유

이 테스트가 도는 시점에는 pytest 수집이 이미 `tests/**` 전 모듈을 import 해서 metadata 가
꽉 차 있다. 「지금 metadata 에 24개 있다」를 여기서 재면 무엇을 지워도 초록이다.
그래서 실행 축 둘은 **자식 프로세스**에서 잰다
(선례: `tests/test_destructive_db_guard.py:70 _collect()`).

## 무엇을 SSOT 로 삼는가

★기대치를 이 파일에 **적지 않는다**. `src/**/*.py` 를 AST 로 훑어 `table=True` 클래스와
`Table("...", SQLModel.metadata, ...)` 호출을 **세는 것**이 SSOT 다. 즉 모델을 새로 추가하면
그 사실 자체가 기대치를 늘린다. `alembic/env.py` 를 SSOT 로 쓰지 않는 이유는 그 파일도
같은 종류의 손 목록이라서다 — 대신 ⑵⑷가 **env.py 를 이 census 로 검사한다**.

## 네 다리

- ⑴ `tests/conftest.py` 가 표를 선언하는 모든 모듈을 **모듈 최상위에서 import** 하는가 (선언 축)
- ⑵ `alembic/env.py` 가 같은 것을 하는가 (SSOT 를 자칭하는 쪽도 검사한다)
- ⑶ `tests.conftest` **만** import 한 자식에서 실제 등록 테이블 = census 인가 (실행 축)
- ⑷ `alembic/env.py` 를 **실제로 태운** 자식에서 `target_metadata` = census 인가 (실행 축)

★⑴이 ⑶과 별개로 필요하다. 2026-08-17 실측 — conftest 의 `from src.main import create_app`
는 `src/main.py:447` 의 `app = create_app()` 을 태우고, 그것이 stress_test router →
dependencies → service 를 지나 `src.optimizer.models` 를 **우연히** 끌어온다. 그래서
`optimization_runs` 는 conftest 목록에 없는데도 등록돼 있었다. 그 배선 중 한 칸이라도
지연 import 로 바뀌면 조용히 사라진다 — ⑴은 그 우연에 기대지 않겠다는 단언이다.

★반대로 ⑶⑷가 ⑴⑵와 별개로 필요하다. 선언 축은 **소스 텍스트**만 보므로, 소스에 import 구문이
있는 것과 그 배선이 실제로 metadata 를 넓히는 것은 다르다. ⑶⑷가 그 차이를 잰다.

## ★★실행 축은 census 의 사각을 덮지 못한다 (2026-08-17 적대 리뷰가 반증)

초판 주석은 「파서가 못 보는 선언 형태는 실행 축이 『정체불명』으로 잡는다」고 적었다. **거짓이다.**
실행 축이 보는 것은 conftest·env.py 가 **import 한** 모듈이 등록한 표뿐이다. 그러므로 아무도
import 하지 않는 모듈이 파서에게도 안 보이면 — 선언 축은 「import 할 것이 없다」고 통과하고
실행 축은 「등록된 것이 census 와 같다」고 통과한다. **네 다리가 전부 초록**이다. 실증된 두 형태:

- `from sqlalchemy import Table as SATable` → `SATable("escaped_table", SQLModel.metadata, ...)`
- `class EscapedModel(SQLModel, table=TABLE_FLAG)` — `table=` 이 변수

⇒ census 는 이 검사면의 **유일한** 기대치 원천이고, 그래서 파서는 「못 보면 조용히 넘어간다」가
아니라 **「결정할 수 없으면 멈춘다」**여야 한다. import 별칭은 해석하고(`_local_aliases`),
그래도 결정 못 하는 것은 AssertionError 로 사람에게 넘긴다.
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

# 자식 stdout 은 로깅 설정(`configure_logging`)·alembic 의 오프라인 SQL 이 섞인다.
# 표식 줄만 골라 읽는다.
_DUMP_MARKER = "QB-METADATA-TABLES "

_CONFTEST_DUMP_SCRIPT = (
    "import json, sys\n"
    "import tests.conftest  # noqa: F401 — 이 한 줄이 create_all 범위를 정한다\n"
    "from sqlmodel import SQLModel\n"
    f"sys.stdout.write({_DUMP_MARKER!r} + json.dumps(sorted(SQLModel.metadata.tables)) + chr(10))\n"
)

# ★`alembic/env.py` 를 **실제로 태우는** 스크립트. `as_sql=True`(오프라인)라 DB 에 붙지 않고
#   `fn` 이 빈 목록을 내므로 migration 도 하나도 안 돈다 — 생성된 SQL 은 stdout 으로 버려진다.
#   그런데도 env.py 의 모듈 최상위(= 모델 import 블록)와 `target_metadata` 배선은 다 지난다.
#   ★`_guard_destructive_migrations()` 는 `config.cmd_opts` 가 없으면 통과한다(파이썬 직접 호출).
#
# ★★**`SQLModel.metadata` 를 덤프하면 안 된다.** 초판이 그랬고, 그래서 이 다리는 「env.py 를
#   태운 뒤 프로세스 어딘가에 뭐가 등록됐나」만 봤다 — env.py 가 그것을 alembic 에 **넘겼는지**는
#   보지 않았다. 지금은 `target_metadata = SQLModel.metadata` 라 **우연히** 같은 객체라서 통과했을
#   뿐이다. 2026-08-17 적대 리뷰가 `env.py` 의 그 줄을 `MetaData()`(빈 것)로 바꿔 실증했다:
#   실제 `alembic check` 는 rc≠0 로 죽는데(DB 테이블 전부가 removed table) 네 다리는 전부 초록이었다.
#
#   그래서 **alembic 이 실제로 읽는 자리**에서 캡처한다 — `EnvironmentContext.configure()` 가
#   `opts['target_metadata'] = target_metadata` 로 심고(alembic 1.18.4
#   `runtime/environment.py:912`), autogenerate 가 `migration_context.opts.get('target_metadata')`
#   로 꺼내 쓴다(`autogenerate/api.py:371`). `alembic check` 가 보는 것과 **같은 객체**다.
#   ★한 번도 configure 되지 않았으면 `get_context()` 가 던진다 → 자식 rc≠0 → red.
#   빈 입력을 「일치」로 읽는 길을 남기지 않는다.
_ALEMBIC_DUMP_SCRIPT = (
    "import json, sys\n"
    "from sqlalchemy import MetaData\n"
    "from alembic.config import Config\n"
    "from alembic.script import ScriptDirectory\n"
    "from alembic.runtime.environment import EnvironmentContext\n"
    "cfg = Config('alembic.ini')\n"
    "script = ScriptDirectory.from_config(cfg)\n"
    "with EnvironmentContext(\n"
    "    cfg, script, fn=lambda rev, ctx: [], as_sql=True,\n"
    "    starting_rev='base', destination_rev='base',\n"
    ") as env_ctx:\n"
    "    script.run_env()\n"
    "    try:\n"
    "        migration_context = env_ctx.get_context()\n"
    "    except Exception as exc:\n"
    "        raise SystemExit(\n"
    "            'QB-ABORT: env.py 가 context.configure() 를 한 번도 부르지 않았다 — '\n"
    "            'target_metadata 를 캡처할 자리가 없다: %r' % (exc,)\n"
    "        )\n"
    "    captured = migration_context.opts.get('target_metadata')\n"
    "if not isinstance(captured, MetaData):\n"
    "    raise SystemExit(\n"
    "        'QB-ABORT: env.py 가 넘긴 target_metadata 가 MetaData 가 아니다: %r. '\n"
    "        'alembic 은 시퀀스도 받지만 이 레포는 단일 MetaData 를 전제한다 — '\n"
    "        '바꿨다면 이 검사기를 같이 넓혀라.' % (type(captured),)\n"
    "    )\n"
    f"sys.stdout.write({_DUMP_MARKER!r} + json.dumps(sorted(captured.tables)) + chr(10))\n"
)

# ★`_SRC_ROOT.rglob` 는 **작업 트리**를 읽는다 — git 추적 여부를 안 본다. 병렬 워크트리·
#   다중 에이전트 운영에서 `src/` 에 잠깐 놓인 프로브 파일이 실제로 이 검사면을 red 로 만든
#   사고가 있었다(2026-08-17). fail-closed 자체는 옳으므로 거르지 않고, 대신 실패 메시지가
#   그 가능성을 먼저 말하게 한다 — 다음 사람이 유령을 쫓지 않도록.
_STRAY_FILE_HINT = (
    "\n★모르는 이름이 보이면 `git status --short apps/api/src` 를 먼저 봐라 — "
    "추적되지 않는 임시 `.py` 파일도 census 에 들어간다."
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


def _local_aliases(tree: ast.Module, symbol: str) -> frozenset[str]:
    """이 모듈에서 `symbol` 이 묶인 **지역 이름** 전부.

    `from sqlalchemy import Table as SATable` → `{"Table", "SATable"}`.

    ★왜 필요한가: 2026-08-17 적대 리뷰가 `SATable("escaped_table", SQLModel.metadata, ...)` 로
      census 를 통째로 우회했다. 파서가 그 모듈을 못 보면 선언 축 ⑴⑵는 「import 할 것이 없다」고
      통과하고, 아무도 그 모듈을 import 하지 않으니 실행 축 ⑶⑷도 통과한다 — **네 다리 전부
      초록**. census 는 이 검사면의 유일한 기대치 원천이라 여기가 새면 나머지가 다 샌다.
    ★`ast.walk` 로 훑는다. 함수 본문에 숨긴 import 도 그 함수가 돌면 표를 등록하므로,
      「최상위만」이라는 좁힘은 여기서는 사각을 만든다(⑴⑵의 `tree.body` 직계 규칙과 반대인
      이유 = 저쪽은 「실행이 보장되는가」를 묻고 이쪽은 「이 이름이 그것인가」를 묻는다).
    ★**아직 못 보는 것 하나** — import 가 아니라 **대입**으로 만든 별칭(`T = Table` 뒤의
      `T(...)`)은 여기 안 잡힌다. 알면서 남긴다: 실사용례가 없고, 대입 추적은 순서 의존이라
      값보다 새 결함의 위험이 크다. ★그래도 「초록 = 그런 표가 없다」로 읽지 마라 —
      초록은 「내가 본 형태 중에는 없었다」만 말한다(`apps/api/AGENTS.md` §10).
    """
    names = {symbol}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == symbol:
                    names.add(alias.asname or alias.name)
    return frozenset(names)


def _is_table_class(node: ast.ClassDef, path: Path) -> bool:
    """`class X(SQLModel, table=True)` 인가.

    ★**리터럴 bool 이 아니면 추측하지 않고 red.** `class X(SQLModel, table=FLAG)` 는 파서가
      `False` 로 읽었지만 런타임에는 진짜 표로 등록됐다(2026-08-17 적대 리뷰 실증 —
      그 모듈을 아무도 import 하지 않으면 네 다리가 전부 초록이었다). `__tablename__` 비리터럴에
      이미 쓰고 있는 fail-closed 규약과 같은 결이다.
    """
    for kw in node.keywords:
        if kw.arg is None:
            # `class X(SQLModel, **opts)` — `table` 이 그 안에 있는지 소스로 알 수 없다.
            raise AssertionError(
                f"{path}:{node.lineno} `{node.name}` 이 클래스 인자를 `**` 로 편다 — "
                "`table=` 여부를 소스에서 결정할 수 없다. 명시 kwarg 로 바꿔라."
            )
        if kw.arg != "table":
            continue
        if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, bool):
            return kw.value.value
        raise AssertionError(
            f"{path}:{node.lineno} `{node.name}` 의 `table=` 이 리터럴 bool 이 아니다 — "
            "census 파서가 이것이 표인지 결정할 수 없다. 리터럴로 바꾸거나 파서를 넓혀라."
        )
    return False


def _explicit_tablename(node: ast.ClassDef, path: Path) -> str | None:
    """클래스 본문의 `__tablename__` 리터럴. 없으면 None.

    ★`ast.Assign`(`__tablename__ = "x"`)과 `ast.AnnAssign`(`__tablename__: str = "x"`)을
      **둘 다** 본다. 초판은 Assign 만 봤고, 그래서 어노테이션 대입으로 선언한 실동작 테이블이
      census 에서 통째로 사라졌다(2026-08-17 적대 리뷰가 프로브로 재현 — 그 모듈을 아무도
      import 하지 않으면 네 다리가 전부 초록이었다).
    """
    for stmt in node.body:
        targets: list[ast.expr]
        if isinstance(stmt, ast.Assign):
            targets = list(stmt.targets)
        elif isinstance(stmt, ast.AnnAssign):
            targets = [stmt.target]
        else:
            continue
        if not any(isinstance(t, ast.Name) and t.id == "__tablename__" for t in targets):
            continue
        value = stmt.value
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            return value.value
        # ★리터럴이 아니면 **추측하지 않는다.** 여기서 클래스명 소문자로 넘겨짚으면
        #   census 에 틀린 이름이 들어가 영영 못 고치는 red 가 된다.
        raise AssertionError(
            f"{path}:{node.lineno} `{node.name}.__tablename__` 이 리터럴 문자열이 아니다 — "
            "census 파서가 테이블 이름을 결정할 수 없다. 리터럴로 바꾸거나 파서를 넓혀라."
        )
    return None


def _metadata_table_call_name(
    node: ast.Call, table_names: frozenset[str], sqlmodel_names: frozenset[str], path: Path
) -> str | None:
    """`Table("name", SQLModel.metadata, ...)` 이면 그 이름, Table 호출이 아니면 None.

    ★**두 번째 인자까지 본다.** 이름만 보면 `Table("x", other_metadata, ...)` 처럼
      `SQLModel.metadata` 에 안 묶이는 표까지 census 에 들어가고, 그러면 ⑶⑷가
      「등록 누락」이라며 **원리적으로 충족 불가능한 red** 를 영구히 낸다.

    ★생성자 이름도 metadata 이름도 **모듈의 import 별칭으로 해석**한다(`_local_aliases`).
      종전 판정은 이름이 글자 그대로 `Table`/`SQLModel` 인 것만 봤다.

    ★**Table 호출인데 census 이름을 결정하지 못하면 None 이 아니라 red 다.** 종전 주석은
      「못 보는 쪽이 fail-closed — 실행 축이 「정체불명」으로 잡는다」고 적었는데 그게 거짓이었다:
      실행 축이 보는 것은 conftest·env.py 가 **import 한** 모듈뿐이라, 아무도 import 하지 않는
      모듈의 표는 어느 다리에도 안 걸린다. census 가 못 보면 그 모듈은 통째로 투명해진다.
      ⇒ 조용히 넘기지 말고 멈춰서 사람에게 묻는다.
    """
    func = node.func
    if isinstance(func, ast.Attribute):
        is_table_ctor = func.attr in table_names
    elif isinstance(func, ast.Name):
        is_table_ctor = func.id in table_names
    else:
        is_table_ctor = False
    if not is_table_ctor:
        return None

    where = f"{path}:{node.lineno}"
    if len(node.args) < 2:
        raise AssertionError(
            f"{where} `Table(...)` 호출의 위치 인자가 2개 미만이다 — census 파서가 "
            "테이블 이름과 metadata 귀속을 결정할 수 없다. 파서를 넓히거나 호출을 풀어 써라."
        )
    name_arg, metadata_arg = node.args[0], node.args[1]
    if not (isinstance(name_arg, ast.Constant) and isinstance(name_arg.value, str)):
        raise AssertionError(
            f"{where} `Table(...)` 의 첫 인자가 리터럴 문자열이 아니다 — census 파서가 "
            "테이블 이름을 결정할 수 없다. 리터럴로 바꾸거나 파서를 넓혀라."
        )
    bound_to_sqlmodel = (
        isinstance(metadata_arg, ast.Attribute)
        and metadata_arg.attr == "metadata"
        and isinstance(metadata_arg.value, ast.Name)
        and metadata_arg.value.id in sqlmodel_names
    )
    if not bound_to_sqlmodel:
        raise AssertionError(
            f"{where} `Table({name_arg.value!r}, ...)` 의 두 번째 인자가 "
            "`SQLModel.metadata`(또는 그 import 별칭)로 보이지 않는다 — census 파서가 이 표가 "
            "`create_all`/autogenerate 범위에 드는지 결정할 수 없다. 정말 별개의 MetaData 라면 "
            "이 파서에 그 예외를 **명시**해라. 조용히 빠지면 네 다리가 전부 이 표를 못 본다."
        )
    return name_arg.value


def _tables_declared_in(path: Path) -> frozenset[str]:
    """한 파일이 `SQLModel.metadata` 에 선언하는 테이블 이름.

    두 형태를 센다:
    - `class X(SQLModel, table=True)` — `__tablename__` 리터럴이 있으면 그것, 없으면
      SQLModel 기본값인 **클래스명 소문자**(`sqlmodel.main` 의 `__tablename__` declared_attr).
    - `Table("name", SQLModel.metadata, ...)` — Better Auth 처럼 모델 클래스가 없는 표.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    table_names = _local_aliases(tree, "Table")
    sqlmodel_names = _local_aliases(tree, "SQLModel")
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if not _is_table_class(node, path):
                continue
            explicit = _explicit_tablename(node, path)
            found.add(explicit if explicit is not None else node.name.lower())
        elif isinstance(node, ast.Call):
            name = _metadata_table_call_name(node, table_names, sqlmodel_names, path)
            if name is not None:
                found.add(name)
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
# 손 목록 파서 — 어떤 파일이 어떤 `src.*` 모듈을 **모듈 최상위에서** import 하는가
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
    """★**모듈 최상위의 무조건 import 만** 센다.

    초판은 `ast.walk` 로 파일 전체를 훑었다. 그래서 `if TYPE_CHECKING:` 블록이나 함수 본문의
    import 도 「명시 import 했다」로 셌는데, 그 둘은 **런타임에 `SQLModel.metadata` 를 전혀
    안 넓힌다** — 즉 이 파일이 막으려던 결함을 리팩터 한 번으로 되살릴 수 있었다
    (2026-08-17 적대 리뷰가 conftest 의 optimizer import 를 `TYPE_CHECKING` 으로 옮겨 실증:
    런타임 등록이 사라졌는데 세 다리 전부 초록이었다). `tree.body` 직계만 보면 조건부·지연
    import 는 자동으로 빠진다 — 판정 기준은 「실행이 보장된 자리에 있는가」다.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    out: set[str] = set()
    for node in tree.body:
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
        f"census 가 비었다. `{_SRC_ROOT}` 에서 `table=True`/`Table(...)` 를 하나도 못 찾았다 — "
        "경로가 틀렸거나 파서가 죽은 것이다. 이 상태로는 아래 비교가 무엇이든 통과한다."
    )


def _missing_modules(census: dict[str, frozenset[str]], path: Path) -> dict[str, list[str]]:
    declared = _imported_src_modules(path)
    return {m: sorted(census[m]) for m in sorted(set(census) - declared)}


# ---------------------------------------------------------------------------
# ⑴ 선언 축 — conftest 의 손 목록
# ---------------------------------------------------------------------------


def test_conftest_imports_every_table_declaring_module() -> None:
    """red 면 고장난 것: 어떤 모델의 테이블이 `create_all` 범위 밖인데 DB 는 head 로 stamp 된다.

    ★고치는 법 = `tests/conftest.py` **머리**(모듈 최상위)에 `# noqa: F401 — metadata 등록`
      주석과 함께 그 모듈 import 를 추가한다. 전이 import 로 우연히 등록되고 있더라도
      추가해라 — 그 우연은 다른 파일의 배선이 바뀌면 사라진다. ★`if TYPE_CHECKING:` 안이나
      fixture 본문에 넣으면 안 센다. 런타임에 안 도는 import 는 범위를 안 넓히기 때문이다.
    """
    census = _table_declaring_modules()
    _assert_census_is_not_empty(census)

    missing = _missing_modules(census, _CONFTEST)
    assert not missing, (
        f"`tests/conftest.py` 가 모듈 최상위에서 import 하지 않는 표 선언 모듈: {missing}. "
        "그 테이블은 `bootstrap_test_schema` 의 create_all 범위에 들어간다는 보장이 없다."
        + _STRAY_FILE_HINT
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

    missing = _missing_modules(census, _ALEMBIC_ENV)
    assert not missing, (
        f"`alembic/env.py` 가 모듈 최상위에서 import 하지 않는 표 선언 모듈: {missing}. "
        "그 테이블은 autogenerate/`alembic check` 의 metadata 쪽에 없다." + _STRAY_FILE_HINT
    )


# ---------------------------------------------------------------------------
# ⑶⑷ 실행 축 — 자식 프로세스에서 실제로 등록된 결과를 잰다
# ---------------------------------------------------------------------------


def _dump_tables_in_child(script: str, what: str) -> frozenset[str]:
    proc = subprocess.run(
        [sys.executable, "-c", script],
        cwd=_BACKEND_ROOT,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert proc.returncode == 0, (
        f"자식 프로세스가 {what} 에서 죽었다 (rc={proc.returncode}).\n"
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


def _assert_registered_matches_census(
    registered_keys: frozenset[str], census: dict[str, frozenset[str]], what: str
) -> None:
    assert registered_keys, f"[{what}] 자식이 빈 metadata 를 냈다 — 비교가 항진명제가 된다."

    expected: set[str] = set()
    for tables in census.values():
        expected |= set(tables)

    # metadata key 는 schema 가 붙는다(`trading.orders`, `ts.ohlcv`). census 는 맨이름이므로
    # 맨이름으로 내린다. ★내리면서 뭉치면 비교가 느슨해지므로 충돌부터 막는다.
    registered = {key.rsplit(".", 1)[-1] for key in registered_keys}
    assert len(registered) == len(registered_keys), (
        f"schema 를 떼자 이름이 충돌했다: {sorted(registered_keys)}. "
        "이 비교는 맨이름 유일성을 전제한다 — 전제가 깨졌으니 검사기를 고쳐라."
    )

    assert registered == expected, (
        f"[{what}] 등록 누락(census 에 있는데 없음): {sorted(expected - registered)} / "
        f"정체불명(등록됐는데 census 에 없음): {sorted(registered - expected)}. "
        "★정체불명 쪽이 차 있으면 census 파서가 못 보는 선언 형태라는 뜻이다 — "
        "import 를 추가할 게 아니라 이 파일의 파서를 넓혀라." + _STRAY_FILE_HINT
    )


def test_conftest_import_alone_registers_every_declared_table() -> None:
    """red 면 고장난 것: `pytest tests/<한 파일>` 처럼 **부분 실행**할 때 스키마가 모자란다.

    ★전량 실행에서는 수집이 `tests/**` 를 다 import 하므로 이 결함이 가려진다.
      `_test_engine` 은 session fixture라 create_all 이 **수집 이후**에 돌기 때문이다.
      자식에서 `tests.conftest` 만 import 하는 것이 그 가림막을 걷는 유일한 방법이다.
    """
    census = _table_declaring_modules()
    _assert_census_is_not_empty(census)
    registered = _dump_tables_in_child(_CONFTEST_DUMP_SCRIPT, "`import tests.conftest`")
    _assert_registered_matches_census(registered, census, "tests.conftest 단독 import")


def test_alembic_env_run_registers_every_declared_table() -> None:
    """red 면 고장난 것: `alembic check`·autogenerate 의 `target_metadata` 가 실제로 모자란다.

    ★⑵(선언 축)만으로는 부족하다. 선언 축은 **소스에 import 구문이 있는가**를 보고, 이 다리는
      **env.py 가 `context.configure()` 에 실제로 넘긴 `target_metadata`** 를 본다.
      `alembic check` 는 DB 를 요구하지만 이 다리는 오프라인이라 DB 없이 같은 축을 잰다
      ([BL-770] 재발 방지).

    ★2026-08-17 실측 — `env.py` 의 `target_metadata = SQLModel.metadata` 는 그대로 두고
      `run_migrations_offline()` 의 `target_metadata=` 인자만 빈 `MetaData()` 로 바꾸면,
      종전 판(= `SQLModel.metadata` 를 덤프)은 **4개 전부 초록**이었다. 지금은 이 다리가 red 다.
      캡처 지점의 근거는 `_ALEMBIC_DUMP_SCRIPT` 머리 주석 참조.
    """
    census = _table_declaring_modules()
    _assert_census_is_not_empty(census)
    registered = _dump_tables_in_child(_ALEMBIC_DUMP_SCRIPT, "`alembic/env.py` 오프라인 실행")
    _assert_registered_matches_census(registered, census, "alembic/env.py 실행")
