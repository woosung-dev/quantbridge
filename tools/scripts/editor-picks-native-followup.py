"""동결 경제 실행을 다시 돌리지 않고 늦은 native 관측을 별도 이력으로 검증한다."""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

# workflow는 이 파일만 임시 보존한 뒤 동결 checkout의 cwd에서 실행한다.
ROOT = Path.cwd().resolve()
if not (ROOT / "tools/research/editor_picks").is_dir():
    ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "apps/api")]
# 기존 remote worker처럼 거래 설정의 형식만 충족하는 일회용 키다.
# 실제 거래 자격증명이나 연구 번들 인증 키를 코어 설정에 주입하지 않는다.
os.environ.setdefault(
    "TRADING_ENCRYPTION_KEYS", base64.urlsafe_b64encode(os.urandom(32)).decode()
)
os.environ.setdefault("PINE_AST_CACHE_DIR", "")

import pandas as pd  # noqa: E402
from tools.research.editor_picks import verification  # noqa: E402
from tools.research.editor_picks.common import (  # noqa: E402
    NATIVE_POLICY,
    TIMEFRAMES,
    checked_file,
    identity,
    immutable,
    read,
)
from tools.research.editor_picks.crypto import transform  # noqa: E402
from tools.research.editor_picks.execution import artifact, require_runtime  # noqa: E402
from tools.research.editor_picks.remote import remote_namespace, safe_extract  # noqa: E402

from scripts.pine_validation.native_capture import parse_native_capture  # noqa: E402

BASE_HEAD = "897e3028a57b02a631a9331ed59de79a0f57b5fe"
BASE_INPUT = "ee8f9834c2d0e18c0a056ba7e22e94d1d3a14f1fecfba01ccb7f84896dda647f"
PLAN_SHA = "a3f20b1c1aeb7e40590858c0676036525cdc8652bc105706795c02cce5da8f1d"
RUNTIME_SHA = "6659484fe513ddb431737dc30028a8493d69aa1bc259672b5f7863dd22bf8756"
SOURCE_PROOF_SHA = "8a52828d29a084095f031b1a753c0015ccb653cb527a9d7f0a2e2991bcf9c9ca"
CONTEXT = "editor-picks/native-followup-v1"


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def checkout_head() -> str:
    return subprocess.run(
        ["/usr/bin/git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def base(root: Path) -> tuple[dict, dict, dict]:
    frozen = read(root / "full-plan.json")
    if frozen["phase"] != "full" or identity(frozen) != PLAN_SHA:
        raise ValueError("후속 검증의 원래 전체 계획이 다릅니다")
    cohort = verification.frozen_inputs(root, frozen)
    runtime = read(root / "runtime/manifest.json")
    if (
        digest(root / "runtime/manifest.json") != RUNTIME_SHA
        or digest(root / "runtime/source-proof.json") != SOURCE_PROOF_SHA
    ):
        raise ValueError("원래 runtime manifest·빌드 출처가 다릅니다")
    images = {
        k: runtime["image_ids"][f"quantbridge-{k}-runner:local"]
        for k in ("pine", "python")
    }
    for item in cohort["items"]:
        for arm, selection in frozen["artifacts"][item["id"]].items():
            if "source_sha256" in selection:
                _, language, sha = artifact(root, item, arm)
                if selection != {"language": language, "source_sha256": sha}:
                    raise ValueError("원래 동결 생성물이 다릅니다")
    provenance = {
        "head": BASE_HEAD,
        "input_sha256": BASE_INPUT,
        "plan_sha256": PLAN_SHA,
        "cohort_sha256": frozen["cohort_sha256"],
        "runtime_sha256": digest(root / "runtime/manifest.json"),
        "runtime_source_sha256": digest(root / "runtime/source-proof.json"),
        "images": images,
    }
    return frozen, cohort, provenance


def capture_file(root: Path, capture: dict) -> Path:
    path = Path(capture["file"])
    sha = capture["sha256"]
    if (
        set(capture) != {"file", "sha256"}
        or not path.parts
        or path.parts[0] != "native-followup-captures"
        or path.suffix != ".json"
        or path.is_absolute()
        or ".." in path.parts
        or type(sha) is not str
        or len(sha) != 64
        or any(c not in "0123456789abcdef" for c in sha)
    ):
        raise ValueError("후속 관측은 별도 캡처 경로·정확한 SHA만 허용합니다")
    return checked_file(root, capture["file"], sha)


def prior_evidence(candidate: dict) -> None:
    """외부 실패 원시는 열거나 배포하지 않고 식별명·SHA 참조만 보존한다."""
    seen = set()
    for reference in candidate.get("prior_evidence", []):
        path, sha = Path(reference["file"]), reference["sha256"]
        if (
            set(reference) != {"file", "sha256"}
            or path.is_absolute()
            or ".." in path.parts
            or len(path.parts) < 2
            or path.parts[0] != "editor-picks-20261025-expansion-v5"
            or path.suffix != ".json"
            or type(sha) is not str
            or len(sha) != 64
            or any(c not in "0123456789abcdef" for c in sha)
            or str(path) in seen
        ):
            raise ValueError(
                "외부 원시는 정해진 회차의 상대 식별명·SHA 참조만 허용합니다"
            )
        seen.add(str(path))


def collection(root: Path, item: dict, captures: dict, frozen: dict) -> None:
    """성과를 읽지 않고 기존 parser와 관측 범위 조건만 검사한다."""
    if set(captures) != set(TIMEFRAMES):
        raise ValueError("최초 선택에는 세 시간봉 묶음이 필요합니다")
    source, _ = verification.native_reference(root, item)
    for tf, capture in captures.items():
        raw = read(capture_file(root, capture))
        if (
            identity(raw.get("collection_policy")) != identity(NATIVE_POLICY)
            or raw.get("quota_popup_observed") is not False
        ):
            raise ValueError("Basic 수집 정책 또는 팝업 근거가 다릅니다")
        native = parse_native_capture(
            raw,
            source=source,
            signal_bindings=verification.native_bindings(item),
            expected_indicator_id=item["id"],
            expected_symbol="BYBIT:BTCUSDT.P",
            expected_timeframe=tf,
            expected_inputs=item.get("inputs", {}),
            max_total_bars=5000,
            require_full_prefix=True,
        )
        if native.ohlcv.index[0] != pd.Timestamp(native.metadata["price_first_bar"]):
            raise ValueError(
                "원래 고정 코어가 초기 가격을 제외하는 관측은 새 회차가 필요합니다"
            )
        cutoff = pd.Timestamp(frozen["dataset"]["end"])
        frame = native.ohlcv.loc[native.ohlcv.index < cutoff]
        warmup = item["warmup_bars"]
        if len(frame) <= warmup + 1:
            raise ValueError("동결 종료 전 준비봉 이후 이력이 부족합니다")
        end = min(cutoff, frame.index[-1] + pd.Timedelta(tf))
        events = native.window_events(
            frame.index[0].to_pydatetime(), end.to_pydatetime()
        )
        seen, directions = set(), set()
        for event in events:
            if (
                event.direction not in {"long", "short"}
                or event.bar_time not in frame.index
                or event.bar_time in seen
            ):
                raise ValueError("native 사건의 방향·동봉 충돌이 모호합니다")
            seen.add(event.bar_time)
            if event.bar_time >= frame.index[warmup]:
                directions.add(event.direction)
        if {"long", "short"} - directions:
            raise ValueError("준비봉 이후 양방향 사건 근거가 부족합니다")


def freeze(root: Path, ledger_path: Path, destination: Path) -> dict:
    frozen, cohort, provenance = base(root)
    items = {item["id"]: item for item in cohort["items"]}
    ledger = read(ledger_path)
    if set(ledger) != {"schema_version", "candidates"} or ledger["schema_version"] != 1:
        raise ValueError("후속 후보 원장의 형식이 다릅니다")
    attempts, selected, seen = [], {}, set()
    for candidate in ledger["candidates"]:
        identifier, captures = candidate["id"], candidate["captures"]
        if (
            not {"id", "captures"}
            <= set(candidate)
            <= {"id", "captures", "prior_evidence"}
            or identifier not in items
            or set(captures) - set(TIMEFRAMES)
        ):
            raise ValueError("코호트 밖 원문 또는 미지 시간봉입니다")
        prior_evidence(candidate)
        for value in captures.values():
            if set(value) != {"file", "sha256"}:
                raise ValueError("캡처 파일·해시 형식이 다릅니다")
            capture_file(root, value)
        key = identity(candidate)
        if key in seen:
            raise ValueError("같은 관측 묶음을 중복 제출했습니다")
        seen.add(key)
        record = {**candidate, "status": "not_selected"}
        if identifier not in selected:
            try:
                collection(root, items[identifier], captures, frozen)
            except (ValueError, KeyError, TypeError) as error:
                record.update(
                    status="collection_failed", error_type=type(error).__name__
                )
            else:
                record["status"] = "selected"
                selected[identifier] = len(attempts)
        attempts.append(record)
    if not selected:
        raise ValueError("관측 조건을 통과한 새 세 시간봉 묶음이 없습니다")
    value = {
        "schema_version": 1,
        "base": provenance,
        "control_head": checkout_head(),
        "helper_sha256": digest(Path(__file__)),
        "external_evidence_references_not_embedded": True,
        "ledger_sha256": digest(ledger_path),
        "attempts": attempts,
        "selected": selected,
    }
    immutable(destination, value)
    return value


def validate(root: Path, selection: dict) -> None:
    _, cohort, provenance = base(root)
    if (
        selection.get("schema_version") != 1
        or selection.get("base") != provenance
        or selection.get("helper_sha256") != digest(Path(__file__))
        or selection.get("external_evidence_references_not_embedded") is not True
    ):
        raise ValueError("후속 선택의 코어·입력·실행기 출처가 다릅니다")
    items = {item["id"]: item for item in cohort["items"]}
    selected = {}
    seen = set()
    for index, attempt in enumerate(selection["attempts"]):
        identifier = attempt["id"]
        candidate = {
            key: attempt[key]
            for key in ("id", "captures", "prior_evidence")
            if key in attempt
        }
        prior_evidence(candidate)
        if (
            identifier not in items
            or set(attempt["captures"]) - set(TIMEFRAMES)
            or identity(candidate) in seen
        ):
            raise ValueError("코호트 밖 원문입니다")
        seen.add(identity(candidate))
        for value in attempt["captures"].values():
            capture_file(root, value)
        status, error_type = "not_selected", None
        if identifier not in selected:
            try:
                collection(
                    root,
                    items[identifier],
                    attempt["captures"],
                    read(root / "full-plan.json"),
                )
            except (ValueError, KeyError, TypeError) as error:
                status = "collection_failed"
                error_type = type(error).__name__
            else:
                status = "selected"
                selected[identifier] = index
        expected_keys = (
            set(candidate) | {"status"} | ({"error_type"} if error_type else set())
        )
        if (
            attempt["status"] != status
            or set(attempt) != expected_keys
            or attempt.get("error_type") != error_type
        ):
            raise ValueError("최초 수집 통과 묶음의 선택을 바꿀 수 없습니다")
    if not selected or selected != selection["selected"]:
        raise ValueError("후속 선택의 최초 통과 인덱스가 다릅니다")


def pack(root: Path, selection_path: Path, archive: Path) -> dict:
    value = read(selection_path)
    validate(root, value)
    paths = {"selection.json": selection_path}
    for attempt in value["attempts"]:
        for capture in attempt["captures"].values():
            paths[f"captures/{capture['sha256']}.json"] = checked_file(
                root, capture["file"], capture["sha256"]
            )
    with tarfile.open(archive, "x:gz", compresslevel=1) as output:
        for name, path in sorted(paths.items()):
            output.add(path, arcname=name, recursive=False)
    return {
        "files": len(paths),
        "selection_sha256": identity(value),
        "archive_sha256": digest(archive),
    }


def unpack(
    cipher: Path, expected_sha: str, key_env: str, context: str, target: Path
) -> None:
    if digest(cipher) != expected_sha:
        raise ValueError("후속 암호문 SHA가 다릅니다")
    key = base64.b64decode(os.environ[key_env], altchars=b"-_", validate=True)
    with tempfile.TemporaryDirectory() as directory:
        archive = Path(directory) / "bundle.tar.gz"
        transform("decrypt", cipher, archive, key, context)
        safe_extract(archive, target)


def prepare(root: Path, overlay: Path, expected_selection: str) -> dict:
    selection = read(overlay / "selection.json")
    if identity(selection) != expected_selection:
        raise ValueError("실행 전 선택 SHA가 다릅니다")
    allowed = {"selection.json"}
    # 파싱·출처 검증 전에 허용 경로와 전체 목록부터 확인한다.
    for attempt in selection["attempts"]:
        for capture in attempt["captures"].values():
            relative = Path(capture["file"])
            if (
                relative.is_absolute()
                or ".." in relative.parts
                or relative.parts[0] != "native-followup-captures"
            ):
                raise ValueError("후속 overlay의 쓰기 경로가 다릅니다")
            allowed.add(f"captures/{capture['sha256']}.json")
    if {
        str(path.relative_to(overlay)) for path in overlay.rglob("*") if path.is_file()
    } != allowed:
        raise ValueError("미등재 overlay 파일입니다")
    for attempt in selection["attempts"]:
        for capture in attempt["captures"].values():
            name = f"captures/{capture['sha256']}.json"
            source = checked_file(overlay, name, capture["sha256"])
            allowed.add(name)
            destination = root / capture["file"]
            if destination.is_symlink() or not destination.resolve().is_relative_to(
                root.resolve()
            ):
                raise ValueError("후속 관측 경로가 root 밖입니다")
            if destination.exists():
                checked_file(root, capture["file"], capture["sha256"])
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open("xb") as output, source.open("rb") as incoming:
                    shutil.copyfileobj(incoming, output)
    if {
        str(path.relative_to(overlay)) for path in overlay.rglob("*") if path.is_file()
    } != allowed:
        raise ValueError("미등재 overlay 파일입니다")
    validate(root, selection)
    immutable(root / "native-followup-selection.json", selection)
    return selection


def namespace(run: str, attempt: str) -> Path:
    if not run.isdigit() or not attempt.isdigit() or int(run) < 1 or int(attempt) < 1:
        raise ValueError("원격 실행·시도 번호가 다릅니다")
    return Path("native-checks-followups") / run / attempt


def worker(root: Path, run: str, attempt: str, control_head: str) -> dict:
    selection = read(root / "native-followup-selection.json")
    validate(root, selection)
    if (
        checkout_head() != BASE_HEAD
        or selection["control_head"] != control_head
        or (root / "results").exists()
        or require_runtime() != selection["base"]["images"]
    ):
        raise ValueError("경제 결과 없는 고정 checkout·이미지에서만 후속 검증합니다")
    prefix = root / namespace(run, attempt)
    if prefix.exists():
        raise ValueError("같은 원격 실행의 후속 증거를 덮어쓸 수 없습니다")
    prefix.mkdir(parents=True)
    env = {
        key: value
        for key, value in os.environ.items()
        if key in {"PATH", "HOME", "LANG"}
    }
    env.update(
        TRADING_ENCRYPTION_KEYS=base64.urlsafe_b64encode(os.urandom(32)).decode(),
        PINE_AST_CACHE_DIR="",
    )
    codes = {}
    for identifier, index in selection["selected"].items():
        for tf, capture in selection["attempts"][index]["captures"].items():
            destination = root / "native" / identifier / f"{tf}.json"
            if destination.exists() and digest(destination) != capture["sha256"]:
                raise ValueError("원래 입력의 native 관측을 교체하지 않습니다")
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists():
                shutil.copyfile(
                    checked_file(root, capture["file"], capture["sha256"]), destination
                )
        with (prefix / f"{identifier}.log").open("x") as log:
            result = subprocess.run(  # noqa: S603 — 고정 CLI의 verify만 호출하며 코드는 gVisor 안에서 실행한다
                [
                    sys.executable,
                    "-m",
                    "tools.research.editor_picks",
                    "--run-dir",
                    str(root),
                    "verify",
                    "--plan",
                    str(root / "full-plan.json"),
                    "--id",
                    identifier,
                ],
                cwd=ROOT,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
        codes[identifier] = result.returncode
        proof = root / "verification" / f"{identifier}.json"
        if proof.is_file():
            shutil.copyfile(proof, prefix / f"{identifier}.json")
    value = {
        "run_id": run,
        "attempt": attempt,
        "control_head": control_head,
        "selection_sha256": identity(selection),
        "base": selection["base"],
        "helper_sha256": selection["helper_sha256"],
        "returncodes": codes,
    }
    immutable(prefix / "terminal.json", value)
    shutil.copyfile(root / "runtime-installed.json", prefix / "runtime-installed.json")
    shutil.copyfile(root / "native-followup-selection.json", prefix / "selection.json")
    return value


def bundle(root: Path, run: str, attempt: str, archive: Path) -> dict:
    prefix = root / namespace(run, attempt)
    paths = {
        path.name: path
        for path in prefix.iterdir()
        if path.is_file() and not path.is_symlink()
    }
    if "terminal.json" not in paths:
        raise ValueError("실제 실행 종료 근거가 없습니다")
    envelope = {
        "run_id": run,
        "attempt": attempt,
        "files": {name: digest(path) for name, path in paths.items()},
    }
    immutable(prefix / "envelope.json", envelope)
    with tarfile.open(archive, "x:gz", compresslevel=1) as output:
        for path in sorted(prefix.iterdir()):
            output.add(path, arcname=path.name, recursive=False)
    return envelope


def validate_result(
    root: Path, incoming: Path, run: str, attempt: str, selection_path: Path
) -> dict:
    selection = read(selection_path)
    validate(root, selection)
    envelope = read(incoming / "envelope.json")
    if envelope.get("run_id") != run or envelope.get("attempt") != attempt:
        raise ValueError("후속 결과 실행 출처가 다릅니다")
    if set(envelope["files"]) | {"envelope.json"} != {
        path.name for path in incoming.iterdir()
    }:
        raise ValueError("후속 결과의 파일 목록이 다릅니다")
    for name, sha in envelope["files"].items():
        if Path(name).name != name:
            raise ValueError("후속 결과 경로가 다릅니다")
        checked_file(incoming, name, sha)
    terminal = read(incoming / "terminal.json")
    if (
        any(
            terminal.get(key) != expected
            for key, expected in {
                "run_id": run,
                "attempt": attempt,
                "selection_sha256": identity(selection),
                "base": selection["base"],
                "helper_sha256": selection["helper_sha256"],
                "control_head": selection["control_head"],
            }.items()
        )
        or read(incoming / "selection.json") != selection
    ):
        raise ValueError("후속 결과의 선택·동결 입력이 다릅니다")
    installed = read(incoming / "runtime-installed.json")
    runtime = read(root / "runtime/manifest.json")
    if (
        installed["images"] != runtime["image_ids"]
        or installed["runtime"] != runtime["files"]
        or installed["source_proof"] != read(root / "runtime/source-proof.json")
    ):
        raise ValueError("후속 결과의 실제 runtime 이미지가 다릅니다")
    if set(terminal["returncodes"]) != set(selection["selected"]):
        raise ValueError("선택한 원문의 종료 기록이 누락됐습니다")
    items = {item["id"]: item for item in read(root / "cohort.json")["items"]}
    expected_names = {"terminal.json", "selection.json", "runtime-installed.json"}
    for identifier, index in selection["selected"].items():
        expected_names.add(f"{identifier}.log")
        path = incoming / f"{identifier}.json"
        if type(terminal["returncodes"][identifier]) is not int:
            raise ValueError("종료 코드는 정수여야 합니다")
        if terminal["returncodes"][identifier] == 0 and not path.is_file():
            raise ValueError("성공 종료의 실제 판정 파일이 없습니다")
        if path.exists():
            expected_names.add(path.name)
            proof = read(path)
            if (
                proof.get("id") != identifier
                or proof.get("source_sha256") != items[identifier]["source_sha256"]
                or proof.get("plan_sha256") != PLAN_SHA
                or proof.get("images") != selection["base"]["images"]
            ):
                raise ValueError("후속 판정의 원문·계획·이미지가 다릅니다")
            for tf, window in proof["native_windows"].items():
                if (
                    window.get("status") == "checked_partial_window"
                    and window.get("capture_sha256")
                    != selection["attempts"][index]["captures"][tf]["sha256"]
                ):
                    raise ValueError("후속 판정의 실제 캡처가 선택과 다릅니다")
    if set(envelope["files"]) != expected_names:
        raise ValueError("후속 결과의 허용 파일이 다릅니다")
    return terminal


def collect(
    root: Path, incoming: Path, run: str, attempt: str, selection_path: Path
) -> Path:
    validate_result(root, incoming, run, attempt, selection_path)
    destination = root / namespace(run, attempt)
    shutil.copytree(incoming, destination)
    return destination


def install_projection() -> None:
    spec = importlib.util.spec_from_file_location(
        "followup_postprocess", ROOT / "tools/scripts/editor-picks-postprocess.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.install()


def derive(
    root: Path, destination: Path, selections: list[dict], economic_final: Path
) -> dict:
    """별도 clone에만 선택한 판정을 배치하고 기존 결합·수출을 호출한다."""
    final = read(economic_final)
    if (
        final.get("complete") is not True
        or final.get("failures") != []
        or final.get("provenance", final).get("plan_sha256") != PLAN_SHA
    ):
        raise ValueError("원래 경제 수거의 정상 종결 근거가 없습니다")
    provenance = final["provenance"]
    if any(
        provenance.get(key) != value
        for key, value in {
            "head": BASE_HEAD,
            "input_sha256": BASE_INPUT,
            "run_id": "40151197662",
            "plan": "full-plan.json",
            "plan_sha256": PLAN_SHA,
            "shards": 20,
        }.items()
    ):
        raise ValueError("원래 경제 실행 출처가 다릅니다")
    canonical_final = root / remote_namespace(provenance) / "finalization.json"
    if digest(canonical_final) != digest(economic_final):
        raise ValueError("경제 종결 기록의 원본 SHA가 다릅니다")
    envelopes = {}
    for shard in range(20):
        path = root / remote_namespace(provenance) / str(shard) / "envelope.json"
        envelope = read(path)
        if any(
            envelope.get(key) != value
            for key, value in {**provenance, "shard": shard}.items()
        ):
            raise ValueError("원래 경제 분할 봉투의 출처가 다릅니다")
        for name, sha in envelope["files"].items():
            checked_file(root, name, sha)
        envelopes[str(shard)] = digest(path)
    if (
        destination.exists()
        or destination.resolve().is_relative_to(root.resolve())
        or root.resolve().is_relative_to(destination.resolve())
    ):
        raise ValueError("원본과 분리한 새 파생 root만 허용합니다")
    base(root)
    manifest, seen = [], set()
    for selected in selections:
        prefix = root / namespace(selected["run_id"], selected["attempt"])
        selection_path = prefix / "selection.json"
        selection = read(selection_path)
        if digest(prefix / "envelope.json") != selected["envelope_sha256"]:
            raise ValueError("선택한 후속 봉투 SHA가 다릅니다")
        terminal = validate_result(
            root, prefix, selected["run_id"], selected["attempt"], selection_path
        )
        if any(terminal["returncodes"].values()):
            raise ValueError("실패 실행은 이력으로 보존하며 결합은 중단합니다")
        for identifier in selection["selected"]:
            if identifier in seen:
                raise ValueError("동일 원문에 여러 후속 판정을 선택할 수 없습니다")
            seen.add(identifier)
        manifest.append({**selected, "selection_sha256": identity(selection)})
    if sys.platform == "darwin":
        # APFS 압축 영수증의 논리 크기를 다시 풀지 않고 동일 블록을 복제한다.
        subprocess.run(["/bin/cp", "-cR", str(root), str(destination)], check=True)
    else:
        shutil.copytree(root, destination)
    for selected in manifest:
        prefix = root / namespace(selected["run_id"], selected["attempt"])
        selection = read(prefix / "selection.json")
        terminal = read(prefix / "terminal.json")
        for identifier, index in selection["selected"].items():
            if terminal["returncodes"][identifier] != 0:
                raise ValueError("실패한 후속 실행을 기술 통과로 결합할 수 없습니다")
            for tf, capture in selection["attempts"][index]["captures"].items():
                target = destination / "native" / identifier / f"{tf}.json"
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(
                    checked_file(root, capture["file"], capture["sha256"]), target
                )
            shutil.copyfile(
                prefix / f"{identifier}.json",
                destination / "native-checks" / f"{identifier}.json",
            )
    value = {
        "base": base(root)[2],
        "economic_final_sha256": digest(economic_final),
        "economic_envelopes_sha256": envelopes,
        "followups": manifest,
    }
    immutable(destination / "native-followup-derived.json", value)
    install_projection()
    verification.reconcile(destination, destination / "full-plan.json")
    return {
        **value,
        "export": verification.export(destination, destination / "full-plan.json"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=("freeze", "pack", "prepare", "worker", "bundle", "collect", "derive"),
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    for name in (
        "ledger",
        "selection",
        "archive",
        "overlay",
        "cipher",
        "output",
        "economic-final",
        "followups",
    ):
        parser.add_argument(f"--{name}", type=Path)
    for name in (
        "sha256",
        "selection-sha",
        "key-env",
        "run-id",
        "attempt",
        "control-head",
    ):
        parser.add_argument(f"--{name}")
    args = parser.parse_args()
    root = args.run_dir.resolve()
    if args.action == "freeze":
        result = freeze(root, args.ledger, args.selection)
    elif args.action == "pack":
        result = pack(root, args.selection, args.archive)
    elif args.action == "prepare":
        unpack(
            args.cipher,
            args.sha256,
            args.key_env,
            f"{CONTEXT}/input/{args.selection_sha}",
            args.overlay,
        )
        result = prepare(root, args.overlay, args.selection_sha)
    elif args.action == "worker":
        result = worker(root, args.run_id, args.attempt, args.control_head)
    elif args.action == "bundle":
        result = bundle(root, args.run_id, args.attempt, args.archive)
    elif args.action == "collect":
        with tempfile.TemporaryDirectory() as directory:
            incoming = Path(directory) / "incoming"
            selection = read(args.selection)
            unpack(
                args.cipher,
                args.sha256,
                args.key_env,
                f"{CONTEXT}/result/{identity(selection)}/{args.run_id}/{args.attempt}",
                incoming,
            )
            result = {
                "folder": str(
                    collect(root, incoming, args.run_id, args.attempt, args.selection)
                )
            }
    else:
        result = derive(root, args.output, read(args.followups), args.economic_final)
    failed = args.action == "worker" and any(result["returncodes"].values())
    summary = {
        "status": "failed" if failed else "completed",
        "result_sha256": identity(result),
    }
    if args.action in {"freeze", "prepare"}:
        summary["selection_sha256"] = identity(result)
    elif "selection_sha256" in result:
        summary["selection_sha256"] = result["selection_sha256"]
    print(json.dumps(summary))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
