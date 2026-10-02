#!/usr/bin/env python
"""[BL-870] ⑵ 재현 — broker 재연결 뒤 새 태스크가 「바쁜」 prefork 자식에 들어가 멈추는가.

무엇을 재나
  운영 ws-stream 과 같은 설정(prefork · concurrency=3 · acks_late · prefetch_multiplier=1)의 워커에
  끝나지 않는 stream 2개 + ticker 1개를 띄운다. redis 를 재시작해 broker 재연결을 일으키고, ticker 를
  죽인 뒤(운영의 InterfaceError 자리) probe 3건을 넣는다(운영의 reconcile 자리). 30초 안에 probe 가
  몇 건 실행되는지, 그리고 풀이 「바쁘다」고 믿는 자식(`_busy_workers`)이 실제와 맞는지 본다.

시나리오
  S1 수정 전 + redis 재시작   — 결함이 재현되면 probe 0/3, reserved 에 probe 1건
  S2 수정 전 + 재시작 없음    — 대조군. probe 3/3 이어야 원인이 재연결로 좁혀진다
  S3 백포트 + redis 재시작    — `src/tasks/_celery_backports.py` 를 건 워커. probe 3/3 이어야 한다
  S4 (선택) 상류 5.7.0a1      — `--celery57-dir` 에 linux 용 celery 5.7.0a1 site-packages 를 주면 돈다

실행 (apps/api 에서, docker 필요 — 전용 네트워크·redis 를 만들고 끝나면 지운다. quantbridge-* 는 안 건드린다)
  uv run python scripts/repro_bl870_broker_reconnect.py --image ghcr.io/woosung-dev/quantbridge-backend:sha-<7자>
  # S4 용 패키지: uv pip install --target /tmp/celery57 --python-platform aarch64-unknown-linux-gnu \\
  #               --python-version 3.12 --prerelease allow "celery[redis]==5.7.0a1"

2026-10-02 실측(`--repeat 3`, 이미지 sha-2f0ac34 = celery 5.6.3, arm64):
  S2 3/3 · S1 3회 전부 0/3(재연결 직후 busy=[] — 실행 중 3개) · S3 3회 전부 3/3 · S4 3회 전부 3/3.
  ★stream/ticker 에 운영과 같은 lease(SET NX)가 있어야 S4 가 공정하다 — 5.7 은 재연결 때 미ack 스트림을
  재배달하고, lease 가 없으면 그 중복이 빈 자식을 차지해 probe 가 0/3 이 된다(첫 판에서 실측).
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import socket
import subprocess
import sys
import tempfile
import time

NODE = "bl870@worker"
NET, REDIS, WORKER = "bl870-net", "bl870-redis", "bl870-worker"
BACKPORT = pathlib.Path(__file__).resolve().parents[1] / "src" / "tasks" / "_celery_backports.py"

APP_SOURCE = """
import importlib.util, os, pathlib, time
from celery import Celery
from celery.worker.control import inspect_command

if os.environ.get("BL870_PATCH") == "1":
    spec = importlib.util.spec_from_file_location("qb_backport", "/qb/_celery_backports.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    print("BL870 backport applied:", mod.apply_asynpool_flush_backport(), flush=True)

app = Celery("bl870", broker=os.environ["BL870_BROKER"])
app.conf.update(task_acks_late=True, task_reject_on_worker_lost=True,
                worker_prefetch_multiplier=1, broker_connection_retry_on_startup=True)
FLAGS = pathlib.Path(os.environ["BL870_FLAGS"])

def _lease(name):
    # 운영 ws:lease:* 와 같은 SET NX — 재배달된 같은 스트림은 즉시 끝난다(duplicate).
    import redis
    return redis.Redis.from_url(os.environ["BL870_BROKER"]).set(f"lease:{name}", 1, nx=True)

@app.task(name="bl870.stream")
def stream(name):
    if not _lease(name):
        return "duplicate"
    while not (FLAGS / "stop").exists():
        time.sleep(0.5)
    return name

@app.task(name="bl870.ticker")
def ticker():
    if not _lease("ticker"):
        return "duplicate"
    while not (FLAGS / "kill_ticker").exists() and not (FLAGS / "stop").exists():
        time.sleep(0.5)
    raise RuntimeError("connection is closed (simulated)")

@app.task(name="bl870.probe")
def probe(i):
    return i

@inspect_command()
def pool_busy(state):
    pool = state.consumer.pool._pool
    fd_to_pid = {p.inqW_fd: p.pid for p in pool._pool}
    return {"busy_pids": sorted(fd_to_pid.get(fd, -1) for fd in pool._busy_workers),
            "pids": sorted(fd_to_pid.values())}
"""


def sh(*args: str, check: bool = True) -> str:
    r = subprocess.run(list(args), capture_output=True, text=True)  # noqa: S603
    if check and r.returncode != 0:
        raise SystemExit(f"✗ {' '.join(args)}\n{r.stdout}\n{r.stderr}")
    return r.stdout + r.stderr


def run_client(workdir: pathlib.Path, port: int, *args: str) -> str:
    env = {
        **os.environ,
        "PYTHONPATH": str(workdir),
        "BL870_BROKER": f"redis://127.0.0.1:{port}/0",
        "BL870_FLAGS": str(workdir / "flags"),
    }
    r = subprocess.run(  # noqa: S603
        [sys.executable, __file__, "--client", *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if r.returncode != 0:
        raise SystemExit(f"✗ client {args}\n{r.stderr[-2000:]}")
    return r.stdout.strip()


def client_main(args: list[str]) -> None:
    """새 프로세스 = 새 broker 연결(재시작 뒤 끊긴 풀 연결을 쓰지 않는다)."""
    from bl870_app import app, probe, stream, ticker  # type: ignore[import-not-found]

    if args[0] == "observe":
        insp = app.control.inspect(destination=[NODE], timeout=5)
        active = (insp.active() or {}).get(NODE, [])
        reserved = (insp.reserved() or {}).get(NODE, [])
        busy = app.control.broadcast("pool_busy", reply=True, destination=[NODE], timeout=5)
        busy = busy[0][NODE] if busy else {}
        print(
            json.dumps(
                {
                    "active": sorted(
                        f"{t['name'].split('.')[-1]}@{t['worker_pid']}" for t in active
                    ),
                    "reserved": sorted(t["name"].split(".")[-1] for t in reserved),
                    "busy_pids": busy.get("busy_pids"),
                }
            )
        )
        return
    for item in args[1:]:
        kind, _, arg = item.partition(":")
        if kind == "stream":
            stream.delay(arg)
        elif kind == "ticker":
            ticker.delay()
        else:
            probe.delay(int(arg))


def scenario(
    name: str,
    *,
    image: str,
    patch: bool,
    restart: bool,
    workdir: pathlib.Path,
    port: int,
    pythonpath: str = "",
) -> dict[str, object]:
    flags = workdir / "flags"
    sh("docker", "rm", "-f", WORKER, check=False)
    sh("docker", "exec", REDIS, "redis-cli", "FLUSHALL")
    for f in flags.iterdir():
        f.unlink()
    extra = (
        ["-e", f"PYTHONPATH={pythonpath}", "-v", f"{pythonpath}:{pythonpath}:ro"]
        if pythonpath
        else []
    )
    sh(
        "docker",
        "run",
        "-d",
        "--name",
        WORKER,
        "--network",
        NET,
        "-v",
        f"{workdir}:/repro:ro",
        "-v",
        f"{BACKPORT}:/qb/_celery_backports.py:ro",
        *extra,
        "-e",
        f"BL870_PATCH={int(patch)}",
        "-e",
        f"BL870_BROKER=redis://{REDIS}:6379/0",
        "-e",
        "BL870_FLAGS=/repro/flags",
        "-w",
        "/repro",
        "--entrypoint",
        "/app/.venv/bin/python",
        image,
        "-m",
        "celery",
        "-A",
        "bl870_app",
        "worker",
        "--pool=prefork",
        "--concurrency=3",
        "--loglevel=info",
        "-n",
        NODE,
    )

    def logs() -> str:
        return sh("docker", "logs", WORKER, check=False)

    def wait_log(pattern: str, count: int = 1, timeout: float = 60) -> None:
        t0 = time.time()
        while time.time() - t0 < timeout:
            if logs().count(pattern) >= count:
                return
            time.sleep(0.5)
        raise SystemExit(f"✗ {name}: {pattern!r} x{count} 를 못 봤다\n{logs()[-3000:]}")

    def observe() -> dict[str, list[object]]:
        return json.loads(run_client(workdir, port, "observe"))

    wait_log("ready.")
    version = sh(
        "docker",
        "exec",
        WORKER,
        "/app/.venv/bin/python",
        "-c",
        "import celery;print(celery.__version__)",
    ).strip()
    run_client(workdir, port, "send", "stream:A", "stream:B", "ticker")
    for _ in range(60):
        if len(observe()["active"]) == 3:
            break
        time.sleep(1)
    s1 = observe()
    if restart:
        sh("docker", "restart", "-t", "2", REDIS)
        wait_log("Connection to broker lost")
        wait_log("Connected to redis", count=2)
    else:
        time.sleep(5)
    time.sleep(2)
    s2 = observe()
    (flags / "kill_ticker").touch()
    wait_log("raised unexpected")
    time.sleep(1)
    s3 = observe()
    run_client(workdir, port, "send", "probe:0", "probe:1", "probe:2")
    deadline = time.time() + 30
    while time.time() < deadline and logs().count("bl870.probe[") < 6:
        time.sleep(0.5)
    time.sleep(2)
    s4 = observe()
    lines = logs().splitlines()
    (flags / "stop").touch()
    sh("docker", "rm", "-f", WORKER, check=False)
    return {
        "scenario": name,
        "celery": version,
        "probes_run": sum("bl870.probe[" in ln and "succeeded" in ln for ln in lines),
        "reserved_30s": s4["reserved"],
        "running_1": s1["active"],
        "busy_1": s1["busy_pids"],
        "running_2_reconnected": s2["active"],
        "busy_2_reconnected": s2["busy_pids"],
        "running_3_ticker_died": s3["active"],
        "busy_3_ticker_died": s3["busy_pids"],
    }


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--client":
        client_main(sys.argv[2:])
        return
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--image", required=True, help="celery 5.6.x 가 든 quantbridge-backend 이미지")
    ap.add_argument(
        "--celery57-dir", default="", help="(선택) linux 용 celery 5.7.0a1 site-packages"
    )
    ap.add_argument("--repeat", type=int, default=1, help="S1·S3 반복 횟수")
    opts = ap.parse_args()

    # resolve — 맥의 /var/folders 는 /private 아래 실경로여야 Docker Desktop 이 마운트한다.
    workdir = pathlib.Path(tempfile.mkdtemp(prefix="bl870-")).resolve()
    (workdir / "bl870_app.py").write_text(APP_SOURCE)
    (workdir / "flags").mkdir()
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    for c in (WORKER, REDIS):
        sh("docker", "rm", "-f", c, check=False)
    sh("docker", "network", "rm", NET, check=False)
    sh("docker", "network", "create", NET)
    sh(
        "docker",
        "run",
        "-d",
        "--name",
        REDIS,
        "--network",
        NET,
        "-p",
        f"127.0.0.1:{port}:6379",
        "redis:7-alpine",
        "redis-server",
        "--appendonly",
        "yes",
    )
    plan = [("S2-수정전-재시작없음", False, False, "")]
    for i in range(opts.repeat):
        plan += [
            (f"S1-수정전-재시작#{i + 1}", False, True, ""),
            (f"S3-백포트-재시작#{i + 1}", True, True, ""),
        ]
    if opts.celery57_dir:
        pp = str(pathlib.Path(opts.celery57_dir).resolve())
        plan += [(f"S4-상류5.7.0a1-재시작#{i + 1}", False, True, pp) for i in range(opts.repeat)]
    try:
        for name, patch, restart, pp in plan:
            res = scenario(
                name,
                image=opts.image,
                patch=patch,
                restart=restart,
                workdir=workdir,
                port=port,
                pythonpath=pp,
            )
            print(json.dumps(res, ensure_ascii=False), flush=True)
    finally:
        for c in (WORKER, REDIS):
            sh("docker", "rm", "-f", c, check=False)
        sh("docker", "network", "rm", NET, check=False)
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    main()
