"""Compare matched experimental previews; counts are diagnostics, not accuracy."""

import argparse
import csv
import hashlib
import json
from copy import deepcopy
from pathlib import Path


def summarize(directory: Path) -> tuple[dict, dict]:
    manifest = json.loads((directory / "run_manifest.json").read_text(encoding="utf-8"))
    with (directory / "frames.csv").open(encoding="utf-8", newline="") as stream:
        frames = list(csv.DictReader(stream))
    with (directory / "tracks_2d.csv").open(encoding="utf-8", newline="") as stream:
        tracks = list(csv.DictReader(stream))
    return manifest, {
        "directory": str(directory), "data_source": manifest["data_source"], "frame_count": len(frames),
        "area_candidates": sum(int(row["area_candidate_count"]) for row in frames),
        "retained_candidates": sum(int(row["candidate_count"]) for row in frames),
        "shape_rejected": sum(int(row["shape_rejected_count"]) for row in frames),
        "track_segments": len({row["fish_id"] for row in tracks}),
        "valid_observations": sum(row["is_valid"].lower() == "true" for row in tracks),
        "five_observation_frames": sum(int(row["valid_track_count"]) == 5 for row in frames),
        "status_counts": manifest["track_status_counts"],
        "min_axis_ratio": manifest["effective_centroid_config"]["min_axis_ratio"],
        "birth_confirmation_frames": manifest["config_snapshot"]["multi_tracking"].get("birth_confirmation_frames", 1),
        "config_sha256": manifest["config_sha256"],
    }


def compare(baseline: Path, filtered: Path, output: Path, parameter: str = "shape") -> dict:
    """Require one-variable configs and identical foreground masks for a fair comparison."""

    before, first = summarize(baseline)
    after, second = summarize(filtered)
    for key in ("input_sha256", "frame_count", "start_s", "end_s", "view", "effective_scale_xy"):
        if before[key] != after[key]:
            raise ValueError(f"comparison differs in {key}")
    configurations = [deepcopy(item["config_snapshot"]) for item in (before, after)]
    section, name = ("centroid", "min_axis_ratio") if parameter == "shape" else ("multi_tracking", "birth_confirmation_frames")
    for document in configurations:
        document[section].pop(name, None)
    if configurations[0] != configurations[1]:
        raise ValueError(f"only {section}.{name} may change")
    masks = sorted((baseline / "scaled_masks").glob("*.png"))
    other_masks = sorted((filtered / "scaled_masks").glob("*.png"))
    if [path.name for path in masks] != [path.name for path in other_masks] or len(masks) != before["frame_count"]:
        raise ValueError("foreground mask sets differ or are incomplete")
    for left, right in zip(masks, other_masks):
        if hashlib.sha256(left.read_bytes()).digest() != hashlib.sha256(right.read_bytes()).digest():
            raise ValueError(f"foreground differs at {left.name}")
    result = {"input_sha256": before["input_sha256"], "foreground_masks_byte_identical": True,
              "changed_parameter": f"{section}.{name}", "baseline": first, "variant": second,
              "interpretation": "Diagnostic counts only; fewer candidates/segments do not establish recall or identity accuracy."}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--filtered", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--parameter", choices=("shape", "confirmation"), default="shape")
    arguments = parser.parse_args()
    compare(arguments.baseline, arguments.filtered, arguments.output, arguments.parameter)
