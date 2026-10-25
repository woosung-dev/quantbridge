"""인증된 부모 두 벌과 작은 추가 입력의 SHA를 검증해 6개월 계획을 조립한다."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
import shutil
import stat
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.research.editor_picks.common import identity, write  # noqa: E402

PARENTS = {
    "base": {
        "cipher_sha256": "b8f38f9d8e665d1be35fe3c04e4ec89f55477d073a7749a31ad05535f976f125",
        "cohort_sha256": "077fb10593e2c38b9213ca18dae371df1b9234d317ad984348826d2a608f9ba2",
    },
    "supplement": {
        "cipher_sha256": "a9165955129390cfa346ee77e4821f4d3ad7f3caff0e3d3293f33c540ec05f21",
        "cohort_sha256": "bd4afe8c1684708b972ff34d2a66efde56fd86d24d707d8eb2740e7385211bf3",
    },
}
OUTPUT = {
    "source_count": 200, "expected_cells": 7200, "periods": [6],
    "shards": 160, "max_parallel": 19, "execution_workers": 1,
    "cohort_sha256": "f16bb5a01627ca5bae307f6b9f3998377ea6ee874fefb41b0d074258183c7258",
    "dataset_sha256": "698d2495e303af4c6676d262fd524b7c8c22f729d901e14f34029689c09227f1",
    "runtime_source_proof_sha256": "1d648d0ac99aa6458ad226b767254f7ff85fc773d3e8367736c95e08dca04924",
}
IMAGES = {
    "quantbridge-pine-runner:local": "sha256:1cde1676ef402425c1848824b20523ae41d1f1838e0249e09a2d56dbebb849a6",
    "quantbridge-python-runner:local": "sha256:b55d403d3ca3e7816fa65c2f3868622e555678396af7ee25b7b95ed1b0bd9c31",
    "quantbridge-typescript-runner:local": "sha256:5c9e900e4baadf4598ab773d8786845221c9bb501c3e63d976fdf4e557ddea87",
}
ALLOWED = {
    "data", "runtime", "sources", "adapted", "augmented", "generation", "native",
    "reviews", "screening", "cohort-review-evidence",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "JSON 중복 키를 거부합니다")
        result[key] = value
    return result


def read(path):
    return json.loads(path.read_text(), object_pairs_hook=unique)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def safe_path(root, name):
    require(isinstance(name, str) and name and "\\" not in name, "상대 경로만 허용합니다")
    path = PurePosixPath(name)
    require(not path.is_absolute() and str(path) == name and not {".", ".."} & set(path.parts), "비정규 경로를 거부합니다")
    target = root / name
    require(not any(p.is_symlink() for p in [target, *target.parents]), "부모를 포함한 링크를 거부합니다")
    require(stat.S_ISREG(target.stat().st_mode), "일반 파일만 허용합니다")
    return target


def assemble(base, supplement, addon, output):
    layers = {"base": base.absolute(), "supplement": supplement.absolute(), "addon": addon.absolute()}
    output = output.absolute()
    require(not any(p.is_symlink() for p in [output, *output.parents]), "출력 링크를 거부합니다")
    require(not output.exists() or output.is_dir() and not any(output.iterdir()), "새 출력 디렉터리만 허용합니다")
    require(all(not output.is_relative_to(p) and not p.is_relative_to(output) for p in layers.values()), "입력과 출력은 겹칠 수 없습니다")
    manifest_path = safe_path(layers["addon"], "layer-manifest.json")
    manifest = read(manifest_path)
    require(manifest["schema_version"] == 1 and manifest["scope"] == "six_month_200_originals", "조립 범위가 다릅니다")
    require(manifest["parents"] == PARENTS, "부모 암호문·cohort provenance가 다릅니다")
    declared = manifest["output"]
    require(set(declared) == set(OUTPUT) | {"plan_sha256"} and all(declared[k] == v for k, v in OUTPUT.items()), "동결 실행 범위가 다릅니다")
    require(isinstance(declared["plan_sha256"], str) and re.fullmatch(r"[a-f0-9]{64}", declared["plan_sha256"]), "계획 SHA 형식이 다릅니다")
    parent_items = {}
    for layer in PARENTS:
        path = safe_path(layers[layer], "cohort.json")
        require(digest(path) == PARENTS[layer]["cohort_sha256"], "실제 부모 cohort SHA가 다릅니다")
        parent_items[layer] = read(path)["items"]
    files = manifest["files"]
    require(isinstance(files, dict) and files, "파일 목록이 비었습니다")
    sources = {}
    for name, entry in files.items():
        path = PurePosixPath(name)
        require(path.parts and (path.parts[0] in ALLOWED or name in {"cohort.json", "full-plan.json", "generation-policy.json"}), "허용 입력 경로 밖입니다")
        require(path.parts[:2] != ("data", "pages") and path.name not in {".lock", "request.json.tmp"}, "pack 제외 파일을 거부합니다")
        require(set(entry) == {"layer", "sha256", "bytes"} and entry["layer"] in layers, "파일 layer 계약이 다릅니다")
        require(isinstance(entry["sha256"], str) and re.fullmatch(r"[a-f0-9]{64}", entry["sha256"]) and type(entry["bytes"]) is int and entry["bytes"] >= 0, "파일 SHA·크기 형식이 다릅니다")
        source = safe_path(layers[entry["layer"]], name)
        require(source.stat().st_size == entry["bytes"] and digest(source) == entry["sha256"], "실제 layer 파일 SHA·크기가 다릅니다")
        sources[name] = source
    require(not any(str(p) in files for name in files for p in PurePosixPath(name).parents), "파일과 부모 경로 충돌을 거부합니다")
    def checked(name, expected):
        require(name in files and files[name]["sha256"] == expected, "동결 provenance 파일이 없거나 SHA가 다릅니다")
        return sources[name]
    cohort = read(checked("cohort.json", declared["cohort_sha256"]))
    items = cohort["items"]
    require(cohort["target"] == cohort["source_count"] == len(items) == 200, "원본 200개 분모가 다릅니다")
    original = [(i["id"], i["source_sha256"]) for i in parent_items["base"]]
    require(len(original) == len(set(i for i, _ in original)) == len(set(s for _, s in original)) == 200 and original == [(i["id"], i["source_sha256"]) for i in items], "원본 ID·SHA·순서가 다릅니다")
    by_id = {i["id"]: i for i in items}
    sample = parent_items["supplement"]
    require(len(sample) == len({i["id"] for i in sample}) == 18 and all(by_id.get(i["id"]) == i for i in sample), "보충 18개 원본·최종 item이 다릅니다")
    checked("data/dataset.json", declared["dataset_sha256"])
    checked("runtime/source-proof.json", declared["runtime_source_proof_sha256"])
    require(read(sources["runtime/manifest.json"])["image_ids"] == IMAGES, "V11 runtime 이미지가 다릅니다")
    plan = read(sources["full-plan.json"])
    require(identity(plan) == declared["plan_sha256"] and plan["phase"] == "full" and plan["cohort_file"] == "cohort.json", "최종 계획 identity가 다릅니다")
    require(plan["cohort_sha256"] == declared["cohort_sha256"] and plan["dataset_sha256"] == declared["dataset_sha256"] and plan.get("periods") == [6] and type(plan.get("execution_workers", 1)) is int and plan.get("execution_workers", 1) == 1, "계획 입력·기간·프로세스가 다릅니다")
    expected = [dict(id=i, arm=a, timeframe=t, months=m, scenario=s) for i, a, t, m, s in itertools.product(by_id, ("pine", "terra", "gemini"), ("1h", "4h", "1d"), (6,), ("baseline", "fees_x2", "slippage_x2", "funding_x2"))]
    require(plan["expected_cells"] == len(plan["jobs"]) == len(expected) == 7200 and plan["jobs"] == expected, "정렬된 7200셀 곱집합이 다릅니다")
    for item in items:
        checked(item["source_file"], item["source_sha256"])
        for prefix in ("adapted",):
            if prefix + "_file" in item:
                checked(item[prefix + "_file"], item[prefix + "_sha256"])
        for key in ("public_review_provenance", "static_screening_evidence"):
            if key in item:
                checked(item[key]["file"], item[key]["sha256"])
        if "pine_preflight" in item:
            value = item["pine_preflight"]
            require(value["source_sha256"] == item["source_sha256"], "Pine 원본 provenance가 다릅니다")
            checked(value["evidence_file"], value["evidence_sha256"])
        if "generation_evidence" in item:
            value = item["generation_evidence"]
            for kind in ("source", "request", "receipt"):
                checked(value[kind + "_file"], value[kind + "_sha256"])
    output.mkdir(parents=True, exist_ok=True)
    for name, source in sources.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    proof = {"schema_version": 1, "scope": manifest["scope"], "manifest_sha256": digest(manifest_path), "parents": PARENTS, "output": declared, "checked_file_count": len(files), "files_identity_sha256": identity(files)}
    write(output / "results/layered-input-proof.json", proof)
    return proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("base", "supplement", "addon", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    proof = assemble(args.base, args.supplement, args.addon, args.output)
    print(f"layered_input_verified:{proof['checked_file_count']}_files:200_sources:7200_cells:6_months")


if __name__ == "__main__":
    main()
