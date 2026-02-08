import json
import sys
import os

def load_report(filepath):
    if not os.path.exists(filepath):
        print(f"No previous report found: {filepath}")
        print(f"First run")
        return {"repositories": {}}
    
    with open(filepath) as f:
        return json.load(f)

def extract_deps(report):
    result = {}
    for repo, info in report.get("repositories", {}).items():
        deps = {}
        for manager, files in info.get("packageFiles", {}).items():
            for f in files:
                for dep in f.get("deps", []):
                    name = dep.get("depName")
                    version = dep.get("currentValue", "unknown")
                    deps[name] = version
        result[repo] = deps
    return result

def compare(old_path, new_path):
    old_report = load_report(old_path)
    new_report = load_report(new_path)
    
    old_deps = extract_deps(old_report)
    new_deps = extract_deps(new_report)
    
    print("\n" + "=" * 55)
    print("  DEPENDENCY CHANGE REPORT")
    print("=" * 55)
    
    total_added = 0
    total_removed = 0
    total_changed = 0
    
    for repo in sorted(new_deps.keys()):
        old_repo = old_deps.get(repo, {})
        new_repo = new_deps[repo]
        
        added = {k: v for k, v in new_repo.items() if k not in old_repo}
        removed = {k: v for k, v in old_repo.items() if k not in new_repo}
        changed = {
            k: {"old": old_repo[k], "new": new_repo[k]}
            for k in new_repo
            if k in old_repo and old_repo[k] != new_repo[k]
        }
        
        total_added += len(added)
        total_removed += len(removed)
        total_changed += len(changed)
        
        print(f"\n{repo}")
        print("-" * 45)
        
        if added:
            print("NEW dependencies:")
            for name, ver in sorted(added.items()):
                print(f"     + {name} @ {ver}")
        
        if removed:
            print("REMOVED dependencies:")
            for name, ver in sorted(removed.items()):
                print(f"     - {name} @ {ver}")
        
        if changed:
            print("VERSION changed:")
            for name, vers in sorted(changed.items()):
                print(f"     ~ {name}: {vers['old']} → {vers['new']}")
        
        if not added and not removed and not changed:
            print("No changes")
    
    # Summary
    print("\n" + "=" * 55)
    print("  SUMMARY")
    print("=" * 55)
    print(f"  New:     {total_added}")
    print(f"  Removed: {total_removed}")
    print(f"  Changed: {total_changed}")
    print("=" * 55 + "\n")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 scripts/compare.py <previous.json> <latest.json>")
        sys.exit(1)
    
    compare(sys.argv[1], sys.argv[2])


# import json
# import sys

# def get_deps(filepath):
#     with open(filepath) as f:
#         data = json.load(f)
    
#     result = {}
#     for repo, info in data.get("repositories", {}).items():
#         deps = set()
#         for manager, files in info.get("packageFiles", {}).items():
#             for f in files:
#                 for dep in f.get("deps", []):
#                     deps.add(dep.get("depName"))
#         result[repo] = deps
#     return result

# old = get_deps(sys.argv[1])
# new = get_deps(sys.argv[2])

# print("\n" + "=" * 50)
# print("  DEPENDENCY CHANGES DETECTED")
# print("=" * 50)

# for repo in new:
#     old_deps = old.get(repo, set())
#     new_deps = new[repo]
    
#     added = new_deps - old_deps
#     removed = old_deps - new_deps
    
#     print(f"\n {repo}")
#     print("-" * 40)
    
#     if added:
#         print("   NEW:")
#         for d in sorted(added):
#             print(f"     + {d}")
    
#     if removed:
#         print("   REMOVED:")
#         for d in sorted(removed):
#             print(f"     - {d}")
    
#     if not added and not removed:
#         print("   No changes")

# print("\n" + "=" * 50 + "\n")
