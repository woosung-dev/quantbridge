#!/bin/sh
# 도구 버전은 mise.toml, numpy·pandas 버전은 apps/api/uv.lock 에서만 읽는다. Dockerfile 에는 기본값을 두지 않는다.
set -eu
qb_runner_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$qb_runner_root"
qb_python_base=$(mise exec python -- python -c 'import tomllib; print("python:" + tomllib.load(open("mise.toml", "rb"))["tools"]["python"] + "-slim")')
qb_runner_requirements=$(mise exec python -- python - <<'PY'
import tomllib

with open("apps/api/uv.lock", "rb") as handle:
    packages = {item["name"]: item["version"] for item in tomllib.load(handle)["package"]}
print(" ".join(f"{name}=={packages[name]}" for name in ("numpy", "pandas")))
PY
)
exec docker build --build-arg "PYTHON_BASE=$qb_python_base" \
    --build-arg "RUNNER_REQUIREMENTS=$qb_runner_requirements" -f infra/python-runner/Dockerfile -t quantbridge-python-runner:local .
