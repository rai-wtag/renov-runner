import json
import os

LATEST_DIR = "reports/latest"
PREV_DIR = "reports/previous"
OUTPUT_PATH = os.path.join(LATEST_DIR, "scan-report.json")

summary_report = {"repositories": {}}

for fname in os.listdir(LATEST_DIR):
    if not fname.endswith(".json"):
        continue

    repo_name = fname.replace(".json", "")
    latest_file = os.path.join(LATEST_DIR, fname)
    prev_file = os.path.join(PREV_DIR, fname)

    with open(latest_file) as f:
        latest_data = json.load(f)
    if os.path.exists(prev_file):
        with open(prev_file) as f:
            prev_data = json.load(f)
    else:
        prev_data = {"dependencies": {}}

    latest_deps = latest_data.get("dependencies", {})
    prev_deps = prev_data.get("dependencies", {})

    added, removed, changed = [], [], []
    updates = {"patch": 0, "minor": 0, "major": 0}

    def parse_ver(v):
        parts = v.split(".")
        return [int(p) if p.isdigit() else 0 for p in parts[:3]]

    for dep, info in latest_deps.items():
        prev = prev_deps.get(dep)
        if prev is None:
            added.append(dep)
        else:
            if prev.get("version") != info.get("version"):
                changed.append(dep)
                pv = parse_ver(prev["version"])
                lv = parse_ver(info["version"])
                if lv[0] != pv[0]:
                    updates["major"] += 1
                elif lv[1] != pv[1]:
                    updates["minor"] += 1
                elif lv[2] != pv[2]:
                    updates["patch"] += 1

    for dep in prev_deps:
        if dep not in latest_deps:
            removed.append(dep)

    summary_report["repositories"][repo_name] = {
        "added": added,
        "removed": removed,
        "changed": changed,
        "updates": updates,
        "total_dependencies": len(latest_deps),
    }

with open(OUTPUT_PATH, "w") as f:
    json.dump(summary_report, f, indent=2)

print(f"Saved multi‑repo scan report to {OUTPUT_PATH}")
