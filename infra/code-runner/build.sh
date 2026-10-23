#!/bin/sh
# Node는 mise, TypeScript는 FE lock의 확정 버전에서 읽는다.
set -eu
qb_runner_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$qb_runner_root"
qb_node_base=$(mise exec python -- python -c 'import tomllib; print("node:" + tomllib.load(open("mise.toml", "rb"))["tools"]["node"] + "-bookworm-slim")')
qb_typescript_version=$(mise exec python -- python -c 'import pathlib,re; text=pathlib.Path("apps/web/pnpm-lock.yaml").read_text(); print(re.search(r"(?m)^      typescript:\n        specifier: [^\n]+\n        version: ([0-9.]+)$", text).group(1))')
exec docker build --build-arg "NODE_BASE=$qb_node_base" --build-arg "TYPESCRIPT_VERSION=$qb_typescript_version" -f infra/code-runner/Dockerfile -t quantbridge-typescript-runner:local .
