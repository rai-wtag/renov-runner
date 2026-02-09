import json
import os

LATEST_DIR = "reports/latest"
PREV_DIR = "reports/previous"
OUTPUT_FILE = os.path.join(LATEST_DIR, "scan-report.json")

with open("config/github.json") as f:
    repos = json.load(f).get("repositories", [])

final_report = {"repositories": {}}

for repo in repos:
    latest_file = os.path.join(LATEST_DIR, f"{repo}.json")
    prev_file = os.path.join(PREV_DIR, f"{repo}.json")

    if not os.path.exists(latest_file):
        print(f"[WARN] Latest scan not found for repo {repo}, skipping.")
        continue

    with open(latest_file) as f:
        latest = json.load(f)

    if os.path.exists(prev_file):
        with open(prev_file) as f:
            previous = json.load(f)
    else:
        previous = {"dependencies": {}}

    latest_deps = latest.get("dependencies", {})
    prev_deps = previous.get("dependencies", {})

    changed = {}
    added = []
    removed = []

    for dep, latest_ver in latest_deps.items():
        prev_ver = prev_deps.get(dep)
        if prev_ver is None:
            added.append(dep)
        elif prev_ver != latest_ver:
            changed[dep] = {"previous": prev_ver, "latest": latest_ver}

    for dep in prev_deps:
        if dep not in latest_deps:
            removed.append(dep)

    final_report["repositories"][repo] = {
        "total_dependencies": len(latest_deps),
        "changed_dependencies": changed,
        "added_dependencies": added,
        "removed_dependencies": removed
    }

    os.makedirs(PREV_DIR, exist_ok=True)
    with open(prev_file, "w") as f:
        json.dump(latest, f, indent=2)

os.makedirs(LATEST_DIR, exist_ok=True)
with open(OUTPUT_FILE, "w") as f:
    json.dump(final_report, f, indent=2)

print(f"Saved multi-repo scan report to {OUTPUT_FILE}")
