"""세 생성 방식·세 실행 언어의 동결·생성·공개 실행 검증. 주문·공유 DB 미사용."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import itertools
import json
import os
import random
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps" / "api"))

from tools.research.sol_codegen import (  # noqa: E402
    CODE_SCHEMA,
    EFFORT,
    MODEL,
    OUTPUT_TOKEN_BUDGET,
    generate,
    digest,
)

PUBLIC_CONTRACT = """
완료봉마다 진입/무효화 의도 하나를 반환하는 코드만 작성한다. SL/TP/수량/펀딩/손익은
공통 trusted broker가 처리한다. 신호는 다음 시가에 체결되며 같은 방향 추가 진입은 없다.
반대 long/short 의도는 잔량 청산 확인 뒤 반전이다. 무효화는 close다. long과 short가
동시에 참이면 hold. 이미 포지션이 있으면 반대 entry를 우선하고 다음으로 무효화를 평가한다.
EMA는 첫 length개 SMA seed, 이전에는NA, alpha=2/(length+1). Wilder RMA는 첫 length개 SMA seed,
alpha=1/length. RSI는 첫 length개 변화량의 상승/하락 SMA seed이후 Wilder RMA,
하락평균0이면100(평탄포함). 이는타깃pine_v2의계약이며TradingView전체동일주장이아니다.
표준편차는 population(ddof=0). 모든 high/low breakout 창은 명시된 current봉 포함 여부를 따른다.
Aroon25는현재포함26개봉창,극값동률은가장최근봉. Stoch/WPR의가격범위0과MFI의
양음금액흐름둘다0은NA(조건거짓). CMF는H=L봉flow0,창총거래량0이면NA.
history에는 현재까지 완료된 봉만 있고 미래정보는 없다. 코드에는 네트워크/파일/시계/난수/
패키지설치/셸/외부프로세스 접근이 없다. 외부 라이브러리 기본 지표 의미를 추측하지 않는다.
"""
LANGUAGE_CONTRACT = {
    "python": """Python: def on_bar(ctx, state) -> dict. init(params)->dict 선택.
ctx['history']는 현재봉포함 list[dict], ctx['bar']는현재봉, ctx['position']은
{'direction':'flat|long|short','size':decimal문자열,'average_price':문자열|None}.
bar키는 index,timestamp(ISO UTC),open,high,low,close,volume(가격/거래량문자열).
ctx['params']도있다. state는재호출간보존dict. 반환은정확히 {'action':'hold|long|short|close'}.
표준라이브러리,numpy,pandas사용가능. 호스트코드나quantbridge앱모듈import금지.""",
    "typescript": """TypeScript: export function onBar(ctx: Context, state: Record<string, any>): Intent.
init(params: Record<string,any>):Record<string,any> 선택. 전역 Context,Intent,Bar,Position타입이
공급되므로 import불필요. ctx.history는현재봉포함배열,ctx.bar는현재봉,ctx.position은
{direction:'flat'|'long'|'short',size:string,average_price:string|null}, ctx.params는객체.
Bar는index:number,timestamp:string,open/high/low/close/volume:string.
Intent는 {action:'hold'|'long'|'short'|'close'}. strict tsc후Node실행. 외부패키지import금지.""",
    "pine": """Pine v5: //@version=5와 strategy 선언. strategy.entry('long',strategy.long) 또는
strategy.entry('short',strategy.short), 무효화에는 strategy.close_all() 사용.
strategy.position_size는외부확정포지션이다. qty/limit/stop/strategy.exit/cancel/pyramiding금지.
기본 OHLCV,time,bar_index,과거[],var,if/for,ta.ema/sma/rsi/atr/highest/lowest/stdev/
crossover/crossunder 등의 기존 pine_v2 지원문법을 사용한다.
ta.macd/stoch/cci/roc/wpr/tsi 직접호출은미지원이라기본수식으로계산해야한다.
request.security와heikinashi는정확한MTF/HA계산이아니므로사용하지않는다.
중첩if/else-if 대신 조건을boolean변수로분리하고 독립된1단계if로 주문의도를 낸다.
Pine 주문을 호스트에서 직접 체결하지 않으며 공통 broker가 의도를 처리한다.""",
}
DEV_CASES = [
    (
        "D01",
        "SMA3이 SMA8 상향교차 long,하향교차 short. L SMA3<SMA8/S SMA3>SMA8 무효화.",
    ),
    (
        "D02",
        "현재봉제외직전7봉최고가를종가상향교차 long/최저가하향교차 short. L종가<7봉채널중간/S종가>중간이면무효화.",
    ),
    (
        "D03",
        "종가>EMA15이고RSI7이50상향교차 long. 종가<EMA15이고RSI7이50하향교차 short. L RSI<45또는종가<EMA15/S RSI>55또는종가>EMA15 무효화.",
    ),
    (
        "D04",
        "종가>EMA15이고MACD(3,7)가signal EMA2상향교차 long. 반대short. L반대MACD교차또는종가<EMA15/S대칭 무효화.",
    ),
    (
        "D05",
        "UTC당일누적VWAP=sum(hlc3*V)/sum(V). 종가>EMA15,VWAP상승,종가VWAP상향교차 long. 반대short. LVWAP아래종가/S위종가 무효화. 거래량합0은hold.",
    ),
    (
        "D06",
        "표준OHLC로수동HA계산(첫open=(O+C)/2,이후open=(이전HAO+이전HAC)/2,HAC=(O+H+L+C)/4). 실제종가>EMA15이고HA양봉2개가처음연속확정long,반대short. 반대HA색한봉에무효화. 합성가격체결금지.",
    ),
]
_EXECUTION_LOCK = threading.Lock()


def frozen_environment() -> dict[str, Any]:
    """작업 트리 소스와 실제 이미지 ID를 고정한다. 공유 Docker context는 변경하지 않는다."""
    paths = []
    for directory in (
        "apps/api/src/strategy/code_runtime",
        "apps/api/src/strategy/pine_v2",
        "apps/api/src/strategy/python_runtime",
        "apps/api/src/backtest/engine",
    ):
        paths.extend((ROOT / directory).rglob("*.py"))
    paths += [
        ROOT / "tools/research" / name
        for name in (
            "sol_codegen.py",
            "sol_strategy_lab.py",
            "sol_semantic_eval.py",
            "strategy_oracle.py",
            "strategy_catalogue30.py",
        )
    ]
    for directory in ("infra/python-runner", "infra/code-runner", "infra/pine-runner"):
        paths.extend((ROOT / directory).glob("*"))
    hashes = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(paths)
        if path.is_file()
    }
    images = {}
    for image in (
        "quantbridge-python-runner:local",
        "quantbridge-typescript-runner:local",
        "quantbridge-pine-runner:local",
    ):
        response = subprocess.run(
            ["docker", "image", "inspect", image, "--format", "{{.Id}}"],
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
        )
        images[image] = response.stdout.strip()
    docker = subprocess.run(
        ["docker", "info", "--format", "{{json .Runtimes}}"],
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    )
    if "runsc" not in json.loads(docker.stdout):
        raise RuntimeError("gVisor runsc runtime이 없는 endpoint입니다")
    return {
        "source_hashes": hashes,
        "image_ids": images,
        "docker_endpoint": os.environ.get("DOCKER_HOST", "default"),
        "pine_boundary": "gvisor_network_none_readonly_nonroot",
        "python_typescript_boundary": "gvisor_network_none_readonly_nonroot",
        "oracle_scope": "independent_signals_shared_broker",
    }


def json_write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str))


def smoke_frame() -> pd.DataFrame:
    """공개 smoke는 정답 채점용이 아니며 모든 경로가 같은 입력을 받는다."""
    t = np.arange(360)
    close = 100 + 0.015 * t + 3 * np.sin(t / 8) + np.sin(t / 2)
    open_ = np.concatenate(([close[0]], close[:-1]))
    return pd.DataFrame(
        {
            "open": open_,
            "high": np.maximum(open_, close) + 0.7,
            "low": np.minimum(open_, close) - 0.7,
            "close": close,
            "volume": 10 + t % 17,
        },
        index=pd.date_range("2026-01-01", periods=len(t), freq="1h", tz="UTC"),
    )


def public_check(source: str, language: str) -> dict[str, Any]:
    from src.backtest.engine.types import BacktestConfig
    from src.strategy.code_runtime.backtest import run_code_backtest

    try:
        # 연구 VM은 CPU 두 개다. 컴파일/실행 경합을 지연 비교에 섞지 않는다.
        with _EXECUTION_LOCK:
            start = time.monotonic()
            result = run_code_backtest(
                source,
                language,
                smoke_frame(),
                replace(BacktestConfig(), include_funding=False, freq="1h"),
                warmup_bars=200,
            )
            elapsed = time.monotonic() - start
        return {
            "passed": True,
            "runtime_seconds": elapsed,
            "closed_trades": len(result.trades),
        }
    except Exception as exc:
        return {
            "passed": False,
            "error_type": type(exc).__name__,
            "error": str(exc)[:1500],
        }


def trial(root: Path, case: dict, arm: str, language: str, repetition: int) -> dict:
    from src.strategy.code_runtime.compiler import compile_strategy
    from src.strategy.code_runtime.spec import StrategySpec

    folder = root / "trials" / arm / language / case["id"] / str(repetition)
    final_path = folder / "trial.json"
    base_prompt = (
        PUBLIC_CONTRACT
        + "\n"
        + LANGUAGE_CONTRACT[language]
        + "\n전략의 정확한 요구:\n"
        + case["prompt"]
    )
    if arm == "C":
        base_prompt += (
            "\n실행코드를내지말고주어진닫힌StrategySpec schema의명세를내세요. "
            "지표id/parameters/entry/invalidation을정확히표현하세요. warmup_bars=200. "
            "가격은open/high/low/close/volume/hlc3를참조합니다. "
            "지원못하는패턴을다른전략으로바꾸지마세요."
        )
        schema = StrategySpec.model_json_schema()
    else:
        schema = CODE_SCHEMA
    manifest_hash = hashlib.sha256((root / "manifest.json").read_bytes()).hexdigest()
    identity = digest(
        {
            "prompt": base_prompt,
            "schema": schema,
            "model": MODEL,
            "effort": EFFORT,
            "arm": arm,
            "language": language,
            "repetition": repetition,
            "manifest_hash": manifest_hash,
        }
    )
    if final_path.exists():
        cached = json.loads(final_path.read_text())
        if cached.get("input_identity") != identity:
            raise ValueError("기존 trial의 실험 입력이 다릅니다")
        if cached["status"] == "public_pass" and (
            not (folder / "source.txt").exists()
            or hashlib.sha256((folder / "source.txt").read_bytes()).hexdigest()
            != cached["source_hash"]
        ):
            raise ValueError("기존 trial의 실행 소스가 없거나 손상됐습니다")
        for index, attempt in enumerate(cached["attempts"]):
            destination = folder / f"attempt-{index}"
            generation = json.loads((destination / "generation.json").read_text())
            request = json.loads((destination / "request.json").read_text())
            if generation != attempt["generation"] or generation["job_hash"] != digest(
                request
            ):
                raise ValueError("기존 생성 증거의 hash가 다릅니다")
            if (
                generation["status"] == "completed"
                and digest(json.loads((destination / "payload.json").read_text()))
                != generation["payload_hash"]
            ):
                raise ValueError("기존 생성 응답의 hash가 다릅니다")
        return cached
    attempts, total_tokens, generation_seconds = [], 0, 0.0
    prompt = base_prompt
    source = None
    for attempt in range(1 if arm == "A" else 3):
        remaining = round(max(1, 180 - generation_seconds), 3)
        generation = generate(
            prompt, folder / f"attempt-{attempt}", schema=schema, timeout=remaining
        )
        total_tokens += generation.get("usage", {}).get("output_tokens", 0)
        generation_seconds += generation.get("duration_seconds", 0)
        entry: dict[str, Any] = {"generation": generation}
        payload_file = folder / f"attempt-{attempt}" / "payload.json"
        if generation["status"] != "completed" or total_tokens > OUTPUT_TOKEN_BUDGET:
            entry["validation"] = {
                "passed": False,
                "error": generation.get("error") or "총 생성 토큰 초과",
            }
        else:
            payload = json.loads(payload_file.read_text())
            try:
                source = (
                    compile_strategy(StrategySpec.model_validate(payload), language)
                    if arm == "C"
                    else payload["source_code"]
                )
                if not isinstance(source, str) or not source.strip():
                    raise ValueError("빈 생성 코드")
                entry["validation"] = public_check(source, language)
                if entry["validation"]["passed"]:
                    (folder / "source.txt").write_text(source)
            except Exception as exc:
                entry["validation"] = {
                    "passed": False,
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:1500],
                }
        attempts.append(entry)
        if (
            entry["validation"]["passed"]
            or total_tokens > OUTPUT_TOKEN_BUDGET
            or generation_seconds >= 180
        ):
            break
        prompt = (
            base_prompt
            + "\n이전 산출물:\n"
            + (payload_file.read_text() if payload_file.exists() else "응답 없음")
            + "\n공개검사오류만수정하세요:\n"
            + json.dumps(entry["validation"], ensure_ascii=False)
        )
    result = {
        "case_id": case["id"],
        "input_identity": identity,
        "arm": arm,
        "language": language,
        "repetition": repetition,
        "status": "public_pass" if attempts[-1]["validation"]["passed"] else "failed",
        "attempts": attempts,
        "generation_output_tokens": total_tokens,
        "generation_seconds": generation_seconds,
        "source_hash": hashlib.sha256(source.encode()).hexdigest() if source else None,
        "semantic_status": "not_evaluated",
        "economic_status": "not_evaluated",
    }
    json_write(final_path, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--stage", choices=("pilot", "evaluation"), default="pilot")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--arm", choices=("A", "B", "C"))
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--semantics", action="store_true", help="생성 후 비공개 독립 채점"
    )
    args = parser.parse_args()
    root = args.run_dir.resolve()
    if not root.is_relative_to(ROOT / "runs"):
        parser.error("산출물은 레포 runs/ 안에 둡니다")
    if not 1 <= args.workers <= 3:
        parser.error("생성 동시 실행은 1..3입니다")
    root.mkdir(parents=True, exist_ok=True)
    run_lock = (root / ".runner.lock").open("a")
    try:
        fcntl.flock(run_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        parser.error("같은 run-dir을 다른 runner가 사용 중입니다")
    if args.stage == "pilot":
        cases = [{"id": key, "prompt": prompt} for key, prompt in DEV_CASES]
        repetitions = 2
    else:
        from tools.research.strategy_catalogue30 import candidates

        cases = [{"id": x["id"], "prompt": x["prompt"]} for x in candidates()]
        repetitions = 5
    jobs = list(
        itertools.product(
            cases,
            [args.arm] if args.arm else "ABC",
            LANGUAGE_CONTRACT,
            range(repetitions),
        )
    )
    random.Random(20261022).shuffle(jobs)
    manifest = {
        "model": MODEL,
        "effort": EFFORT,
        "stage": args.stage,
        "cases": cases,
        "total_jobs": len(jobs),
        "repetitions": repetitions,
        "job_order_seed": 20261022,
        "arms": [args.arm] if args.arm else list("ABC"),
        "languages": list(LANGUAGE_CONTRACT),
        "contract": PUBLIC_CONTRACT,
        "language_contracts": LANGUAGE_CONTRACT,
        "output_token_budget": OUTPUT_TOKEN_BUDGET,
        "token_limit_enforcement": "post_response_cli_usage",
        "environment": frozen_environment(),
    }
    from src.strategy.python_runtime.serialization import bars_payload
    from tools.research.sol_semantic_eval import hidden_frame

    manifest["data"] = {
        "public_smoke_sha256": digest(bars_payload(smoke_frame())),
        "hidden_sha256": digest(bars_payload(hidden_frame())),
        "historical_economics": "separate_retrospective_snapshot",
    }
    manifest_path = root / "manifest.json"
    if manifest_path.exists() and json.loads(manifest_path.read_text()) != manifest:
        parser.error("동결 manifest가 다릅니다. 새 run-dir을 사용하세요")
    json_write(manifest_path, manifest)
    selected = jobs[: args.limit] if args.limit is not None else jobs
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(trial, root, *job) for job in selected]
        for future in as_completed(futures):
            result = future.result()
            print(
                json.dumps(
                    {
                        k: result[k]
                        for k in ("case_id", "arm", "language", "repetition", "status")
                    }
                ),
                flush=True,
            )
    if args.semantics:
        from tools.research.sol_semantic_eval import evaluate, paired_summary

        evaluated = []
        for case, arm, language, repetition in selected:
            folder = root / "trials" / arm / language / case["id"] / str(repetition)
            result = json.loads((folder / "trial.json").read_text())
            semantic_path = folder / "semantic.json"
            if semantic_path.exists():
                semantic = json.loads(semantic_path.read_text())
                if semantic.get("input_identity") != result["input_identity"]:
                    raise ValueError("독립 채점 캐시의 실행 소스/실험 입력이 다릅니다")
            elif result["status"] == "public_pass":
                semantic = evaluate(
                    (folder / "source.txt").read_text(), language, case["id"]
                )
            else:
                semantic = {
                    "status": "generation_or_public_failure",
                    "contract_points": 0,
                    "ledger_points": 0,
                    "reproducibility_points": 0,
                }
            semantic["input_identity"] = result["input_identity"]
            json_write(semantic_path, semantic)
            result["semantic"] = semantic
            evaluated.append(result)
            print(
                json.dumps(
                    {
                        "semantic": semantic["status"],
                        "arm": arm,
                        "language": language,
                        "case_id": case["id"],
                        "repetition": repetition,
                    }
                ),
                flush=True,
            )
        json_write(root / "semantic-summary.json", paired_summary(evaluated))


if __name__ == "__main__":
    main()
