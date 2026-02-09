import json
import sys
import os
from datetime import datetime

def load_report(filepath):
    if not os.path.exists(filepath):
        return {"repositories": {}}
    try:
        with open(filepath) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"repositories": {}}


def extract_deps(report):
    result = {}
    repos = report.get("repositories", {})

    for repo_name, repo_data in repos.items():
        deps = {}
        package_files = repo_data.get("packageFiles", {})

        for manager, files in package_files.items():
            for file_info in files:
                package_file = file_info.get("packageFile", "unknown")

                for dep in file_info.get("deps", []):
                    dep_name = dep.get("depName")
                    if not dep_name:
                        continue

                    current_value = dep.get("currentValue", "unknown")
                    raw_updates = dep.get("updates", [])

                    latest_version = None
                    update_type = None

                    for upd in raw_updates:
                        t = upd.get("updateType")
                        v = upd.get("newVersion")
                        if not v:
                            continue
                        if t == "major":
                            update_type = "major"
                            latest_version = v
                        elif t == "minor" and update_type != "major":
                            update_type = "minor"
                            latest_version = v
                        elif t == "patch" and update_type not in ("major", "minor"):
                            update_type = "patch"
                            latest_version = v

                    deps[dep_name] = {
                        "version": current_value,
                        "manager": manager,
                        "file": package_file,
                        "latestVersion": latest_version,
                        "updateType": update_type,
                    }

        result[repo_name] = deps
    return result


def find_changes(old_deps, new_deps):
    changes = {
        "totals": {"added": 0, "removed": 0, "versionChanged": 0},
        "details": {}
    }

    for repo in sorted(new_deps.keys()):
        old_repo = old_deps.get(repo, {})
        new_repo = new_deps[repo]

        added = []
        removed = []
        version_changed = []

        for name in sorted(new_repo.keys()):
            if name not in old_repo:
                info = new_repo[name]
                added.append({
                    "name": name,
                    "version": info["version"],
                    "latestVersion": info["latestVersion"],
                    "updateType": info["updateType"],
                })

        for name in sorted(old_repo.keys()):
            if name not in new_repo:
                info = old_repo[name]
                removed.append({
                    "name": name,
                    "version": info["version"],
                })

        for name in sorted(new_repo.keys()):
            if name in old_repo:
                if old_repo[name]["version"] != new_repo[name]["version"]:
                    version_changed.append({
                        "name": name,
                        "previousVersion": old_repo[name]["version"],
                        "currentVersion": new_repo[name]["version"],
                        "latestVersion": new_repo[name]["latestVersion"],
                        "updateType": new_repo[name]["updateType"],
                    })

        changes["totals"]["added"] += len(added)
        changes["totals"]["removed"] += len(removed)
        changes["totals"]["versionChanged"] += len(version_changed)

        if added or removed or version_changed:
            changes["details"][repo] = {}
            if added:
                changes["details"][repo]["added"] = added
            if removed:
                changes["details"][repo]["removed"] = removed
            if version_changed:
                changes["details"][repo]["versionChanged"] = version_changed

    return changes


def build_report(new_deps, changes):
    report = {
        "generatedAt": datetime.now().isoformat(),
        "overview": {
            "repositoriesScanned": len(new_deps),
            "totalDependencies": 0,
            "updatesAvailable": {"patch": 0, "minor": 0, "major": 0}
        },
        "changes": changes["totals"],
        "repositories": {}
    }

    for repo_name in sorted(new_deps.keys()):
        deps = new_deps[repo_name]
        manager = None
        file = None
        dep_list = []

        for name in sorted(deps.keys()):
            info = deps[name]
            if manager is None:
                manager = info["manager"]
            if file is None:
                file = info["file"]

            report["overview"]["totalDependencies"] += 1

            if info["updateType"] == "patch":
                report["overview"]["updatesAvailable"]["patch"] += 1
            elif info["updateType"] == "minor":
                report["overview"]["updatesAvailable"]["minor"] += 1
            elif info["updateType"] == "major":
                report["overview"]["updatesAvailable"]["major"] += 1

            dep_list.append({
                "name": name,
                "currentVersion": info["version"],
                "latestVersion": info["latestVersion"],
                "updateType": info["updateType"],
            })

        report["repositories"][repo_name] = {
            "manager": manager,
            "file": file,
            "dependencies": dep_list,
        }

    if changes["details"]:
        report["changeDetails"] = changes["details"]

    return report


def main():
    if len(sys.argv) != 4:
        print("Usage: python3 scripts/compare.py <previous.json> <latest.json> <output.json>")
        sys.exit(1)

    old_path = sys.argv[1]
    new_path = sys.argv[2]
    output_path = sys.argv[3]

    old_report = load_report(old_path)
    new_report = load_report(new_path)

    old_deps = extract_deps(old_report)
    new_deps = extract_deps(new_report)

    changes = find_changes(old_deps, new_deps)
    report = build_report(new_deps, changes)

    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"Repositories: {report['overview']['repositoriesScanned']}")
    print(f"Dependencies: {report['overview']['totalDependencies']}")
    print(f"Updates — patch: {report['overview']['updatesAvailable']['patch']}, minor: {report['overview']['updatesAvailable']['minor']}, major: {report['overview']['updatesAvailable']['major']}")
    print(f"Changes — added: {changes['totals']['added']}, removed: {changes['totals']['removed']}, changed: {changes['totals']['versionChanged']}")
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()