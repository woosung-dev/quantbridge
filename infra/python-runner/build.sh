#!/bin/sh
# 버전은 mise.toml 에서 읽고 Dockerfile 에는 기본값을 두지 않는다.
set -eu
qb_runner_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$qb_runner_root"
qb_python_base=$(mise exec python -- python -c 'import tomllib; print("python:" + tomllib.load(open("mise.toml", "rb"))["tools"]["python"] + "-slim")')
exec docker build --build-arg "PYTHON_BASE=$qb_python_base" -f infra/python-runner/Dockerfile -t quantbridge-python-runner:local .
