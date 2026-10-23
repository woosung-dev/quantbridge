#!/bin/sh
# 도구 버전은 mise.toml, Python 의존 버전은 uv.lock에서만 읽는다.
set -eu
qb_runner_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$qb_runner_root"
qb_python_base=$(mise exec python -- python -c 'import tomllib; print("python:" + tomllib.load(open("mise.toml", "rb"))["tools"]["python"] + "-slim")')
qb_pine_requirements=$(mise exec python -- python - <<'PY'
import re
import tomllib

with open("apps/api/uv.lock", "rb") as handle:
    packages = {item["name"]: item for item in tomllib.load(handle)["package"]}
todo = ["numpy", "pandas", "pynescript", "pydantic", "pydantic-settings", "cryptography"]
chosen = {}
while todo:
    name = todo.pop()
    if name in chosen:
        continue
    package = packages[name]
    value = f"{name}=={package['version']}"
    if not re.fullmatch(r"[a-zA-Z0-9_.=+-]+", value):
        raise ValueError("유효하지 않은 잠금 의존성")
    chosen[name] = value
    todo.extend(dependency["name"] for dependency in package.get("dependencies", []))
print(" ".join(chosen[name] for name in sorted(chosen)))
PY
)
exec docker build --build-arg "PYTHON_BASE=$qb_python_base" \
    --build-arg "PINE_REQUIREMENTS=$qb_pine_requirements" \
    -f infra/pine-runner/Dockerfile -t quantbridge-pine-runner:local .
