from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


DEFAULT_LOG_ROOT = Path.home() / r"AppData/LocalLow/Game Labs/Ultimate Admiral Dreadnoughts"

RULES = (
    (
        "duplicate_playerdata",
        re.compile(r"same key has already been added\. Key:\s*(PlayerData-[\w-]+)", re.I),
        "Duplicate campaign player row. Run the patcher and inspect save player rows before loading again.",
    ),
    (
        "il2cpp_exception",
        re.compile(r"Il2CppException|BEGIN IL2CPP STACK TRACE", re.I),
        "Managed/native exception bridge fired. Check the surrounding grouped errors.",
    ),
    (
        "null_reference",
        re.compile(r"NullReferenceException|Object reference not set", re.I),
        "Null reference spam. Usually bad table rows, invalid names, or broken campaign objects.",
    ),
    (
        "invalid_tech_type",
        re.compile(r"invalid tech type:\s*([\w_]+)", re.I),
        "Mission or data table references a tech type that does not exist. Run the patcher to sanitize missions.",
    ),
    (
        "gamedata_assertion",
        re.compile(r"GameData\.PostProcessAll|Exception:\s*assertion failed", re.I),
        "GameData post-processing failed. Fix invalid table references before loading a campaign.",
    ),
    (
        "ship_generation_fail",
        re.compile(r"Generate random ship.*failed|random ship.*failed", re.I),
        "Random ship generator failed. Hull tonnage, allowed parts, or randParts rules may be too tight.",
    ),
    (
        "critical_move_port",
        re.compile(r"CRITICAL ERROR.*Move.*port|Move.*CRITICAL ERROR", re.I),
        "Campaign route/port assignment failed. Save port sanitizer should be rerun.",
    ),
    (
        "boxcollider_warning",
        re.compile(r"BoxColliders? does not support negative scale or size", re.I),
        "Unity collider warning spam from preview/model data. Usually not fatal but hurts log volume.",
    ),
    (
        "task_escape",
        re.compile(r"Task Escape|escape task", re.I),
        "Campaign task/route state is noisy. Save route sanitizer may help.",
    ),
    (
        "route_spike",
        re.compile(r"\b([2-9]\d{2,}|1\d{3,})\s+routes\b", re.I),
        "Large route counts can slow turns. Consider route cleanup or fewer active AI fleets.",
    ),
    (
        "asset_unload_spike",
        re.compile(r"Unloading\s+([1-9]\d{3,})\s+unused Assets|Loaded Objects now:\s+([1-9]\d{5,})", re.I),
        "Large Unity asset unload/load pass. Heavy session memory pressure or oversized campaign state.",
    ),
)


def log_files(root: Path) -> list[Path]:
    candidates = [root / "Player.log", root / "Player-prev.log"]
    candidates.extend(sorted(root.glob("Player*.log")))
    seen = set()
    result = []
    for path in candidates:
        if path in seen or not path.exists() or not path.is_file():
            continue
        seen.add(path)
        result.append(path)
    return result


def scan_path(path: Path, sample_limit: int) -> dict:
    counts = Counter()
    details = defaultdict(Counter)
    samples = defaultdict(list)
    total_lines = 0
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            total_lines += 1
            stripped = line.rstrip()
            for rule_id, pattern, _help_text in RULES:
                match = pattern.search(stripped)
                if not match:
                    continue
                counts[rule_id] += 1
                groups = [group for group in match.groups() if group]
                if groups:
                    details[rule_id][groups[0]] += 1
                if len(samples[rule_id]) < sample_limit:
                    samples[rule_id].append({"line": line_number, "text": stripped[:240]})
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "modified": path.stat().st_mtime,
        "lines": total_lines,
        "counts": dict(counts),
        "details": {key: counter.most_common(sample_limit) for key, counter in details.items()},
        "samples": dict(samples),
    }


def summarize(scans: list[dict], sample_limit: int) -> dict:
    total_counts = Counter()
    merged_details = defaultdict(Counter)
    for scan in scans:
        total_counts.update(scan["counts"])
        for key, values in scan["details"].items():
            for detail, count in values:
                merged_details[key][detail] += count
    recommendations = [
        {"id": rule_id, "count": total_counts[rule_id], "recommendation": help_text}
        for rule_id, _pattern, help_text in RULES
        if total_counts[rule_id]
    ]
    return {
        "files_scanned": len(scans),
        "counts": dict(total_counts),
        "details": {key: counter.most_common(sample_limit) for key, counter in merged_details.items()},
        "recommendations": recommendations,
    }


def print_human(report: dict) -> None:
    summary = report["summary"]
    print(f"files_scanned: {summary['files_scanned']}")
    if not summary["counts"]:
        print("No known UAD error patterns found.")
        return
    print("counts:")
    for key, count in sorted(summary["counts"].items(), key=lambda item: (-item[1], item[0])):
        print(f"  {key}: {count}")
    if summary["details"]:
        print("top_details:")
        for key, values in summary["details"].items():
            formatted = ", ".join(f"{detail}={count}" for detail, count in values)
            print(f"  {key}: {formatted}")
    print("recommendations:")
    for item in summary["recommendations"]:
        print(f"  {item['id']}: {item['recommendation']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan Ultimate Admiral Dreadnoughts logs for known campaign/performance errors.")
    parser.add_argument("--log-root", type=Path, default=DEFAULT_LOG_ROOT)
    parser.add_argument("--json", action="store_true", help="Print full JSON report instead of a short summary.")
    parser.add_argument("--sample-limit", type=int, default=5)
    args = parser.parse_args()

    paths = log_files(args.log_root)
    scans = [scan_path(path, args.sample_limit) for path in paths]
    report = {"summary": summarize(scans, args.sample_limit), "files": scans}
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_human(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
