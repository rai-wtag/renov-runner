import json
import os

LATEST_DIR = "reports/latest"
PREVIOUS_DIR = "reports/previous"
summary = {}

# each repo in latest reports
for repo_name in os.listdir(LATEST_DIR):
    latest_repo_path = os.path.join(LATEST_DIR, repo_name)
    prev_repo_path = os.path.join(PREVIOUS_DIR, repo_name)

    latest_file = os.path.join(latest_repo_path, "scan-report.json")
    prev_file = os.path.join(prev_repo_path, "scan-report.json")

    # latest scan
    if os.path.exists(latest_file):
        with open(latest_file) as f:
            latest_data = json.load(f)
    else:
        latest_data = {}

    # previous scan
    if os.path.exists(prev_file):
        with open(prev_file) as f:
            prev_data = json.load(f)
    else:
        prev_data = {}

    changed = []
    added = []
    removed = []
    updates = {"patch": 0, "minor": 0, "major": 0}

    latest_deps = latest_data.get("dependencies", {})
    prev_deps = prev_data.get("dependencies", {})

    for dep, info in latest_deps.items():
        if dep not in prev_deps:
            added.append(dep)
        else:
            prev_version = prev_deps[dep].get("version")
            latest_version = info.get("version")
            if prev_version != latest_version:
                changed.append(dep)
                # type of update
                def parse_semver(v):
                    parts = v.split(".")
                    return [int(p) if p.isdigit() else 0 for p in parts[:3]]
                prev_semver = parse_semver(prev_version)
                latest_semver = parse_semver(latest_version)
                if latest_semver[0] != prev_semver[0]:
                    updates["major"] += 1
                elif latest_semver[1] != prev_semver[1]:
                    updates["minor"] += 1
                elif latest_semver[2] != prev_semver[2]:
                    updates["patch"] += 1

    for dep in prev_deps:
        if dep not in latest_deps:
            removed.append(dep)

    summary[repo_name] = {
        "added": added,
        "removed": removed,
        "changed": changed,
        "updates": updates,
        "total_dependencies": len(latest_deps)
    }

os.makedirs(LATEST_DIR, exist_ok=True)
summary_file = os.path.join(LATEST_DIR, "scan-report.json")
with open(summary_file, "w") as f:
    json.dump(summary, f, indent=2)

for repo, stats in summary.items():
    print(f"Repository: {repo}")
    print(f"  Total dependencies: {stats['total_dependencies']}")
    print(f"  Added: {len(stats['added'])}, Removed: {len(stats['removed'])}, Changed: {len(stats['changed'])}")
    print(f"  Updates: Patch={stats['updates']['patch']}, Minor={stats['updates']['minor']}, Major={stats['updates']['major']}")
    print("-" * 40)
