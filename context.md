# Complete Multi-Platform Dependency Scanner — Full Solution

## What We're Building

```
renov-runner/
│
├── One central place that scans ALL your repos
├── Runs daily (or manually)
├── Scans GitHub, GitLab, Bitbucket, Azure DevOps
├── Stores every report with timestamp
├── Compares with previous run
├── Shows exactly what's NEW, REMOVED, or CHANGED
├── Scales to 100+ repos easily
└── Outputs a clean summary
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     renov-runner (GitHub)                   │
│                                                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────┐│
│  │ Job: GitHub │ │ Job: GitLab │ │Job:Bitbucket│ │Job:Azure││
│  │             │ │             │ │             │ │        ││
│  │ Token A     │ │ Token B     │ │ Token C     │ │Token D ││
│  │ 10 repos    │ │ 5 repos     │ │ 3 repos     │ │2 repos ││
│  │             │ │             │ │             │ │        ││
│  │ github.json │ │ gitlab.json │ │bitbucket.json│ │azure.json│
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └───┬────┘│
│         │               │               │            │     │
│         └───────────────┴───────────────┴────────────┘     │
│                              │                              │
│                    ┌─────────▼─────────┐                   │
│                    │  Merge & Compare  │                   │
│                    │                   │                   │
│                    │ combined.json     │                   │
│                    │ diff-report.md    │                   │
│                    └───────────────────┘                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Folder Structure

```
renov-runner/
├── .github/
│   └── workflows/
│       └── scan.yml                 ← The automation
│
├── config/
│   ├── github.json                  ← List of GitHub repos
│   ├── gitlab.json                  ← List of GitLab repos
│   ├── bitbucket.json               ← List of Bitbucket repos
│   └── azure.json                   ← List of Azure DevOps repos
│
├── scripts/
│   ├── compare_reports.py           ← Diff detection
│   ├── merge_reports.py             ← Combine all platforms
│   └── generate_summary.py          ← Human-readable output
│
├── reports/
│   ├── previous/
│   │   ├── github.json              ← Last GitHub scan
│   │   ├── gitlab.json              ← Last GitLab scan
│   │   ├── bitbucket.json           ← Last Bitbucket scan
│   │   ├── azure.json               ← Last Azure scan
│   │   └── combined.json            ← Last combined report
│   │
│   ├── history/                     ← All past reports
│   │   ├── 2025-02-07_0900/
│   │   │   ├── github.json
│   │   │   ├── gitlab.json
│   │   │   └── combined.json
│   │   └── 2025-02-08_0900/
│   │       └── ...
│   │
│   └── latest/
│       ├── diff-report.md           ← Human-readable changes
│       └── combined.json            ← Current state
│
├── .env                             ← Local testing (gitignored)
├── .gitignore
└── README.md
```

---

## Step 1: Create the Folder Structure

```bash
cd ~/Desktop/renov-runner

# Create folders
mkdir -p config
mkdir -p scripts
mkdir -p reports/previous
mkdir -p reports/history
mkdir -p reports/latest
mkdir -p .github/workflows

# Create empty previous files (first run baseline)
echo '{"repositories":{}}' > reports/previous/github.json
echo '{"repositories":{}}' > reports/previous/gitlab.json
echo '{"repositories":{}}' > reports/previous/bitbucket.json
echo '{"repositories":{}}' > reports/previous/azure.json
echo '{"repositories":{}}' > reports/previous/combined.json
```

---

## Step 2: Create Config Files

### config/github.json

```json
{
  "platform": "github",
  "endpoint": null,
  "repositories": [
    "rai-wtag/renov-pilot05",
    "rai-wtag/renov-pilot06"
  ]
}
```

### config/gitlab.json

```json
{
  "platform": "gitlab",
  "endpoint": "https://gitlab.com/api/v4",
  "repositories": [
  ]
}
```

### config/bitbucket.json

```json
{
  "platform": "bitbucket",
  "endpoint": null,
  "repositories": [
  ]
}
```

### config/azure.json

```json
{
  "platform": "azure",
  "endpoint": "https://dev.azure.com",
  "repositories": [
  ]
}
```

**To add repos later, just add them to the array. That's it.**

---

## Step 3: Create the Scripts

### scripts/compare_reports.py

```python
#!/usr/bin/env python3
"""
Compares two Renovate reports and identifies:
- New dependencies
- Removed dependencies
- Version changes in source files
- New repositories
- Removed repositories
"""

import json
import sys
import os
from datetime import datetime

def load_report(filepath):
    """Load a Renovate report JSON file."""
    if not os.path.exists(filepath):
        return {"repositories": {}}
    
    try:
        with open(filepath) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"repositories": {}}

def extract_deps(report):
    """Extract all dependencies from a report."""
    result = {}
    
    repos = report.get("repositories", {})
    
    for repo_name, repo_data in repos.items():
        deps = {}
        package_files = repo_data.get("packageFiles", {})
        
        for manager, files in package_files.items():
            for file_info in files:
                package_file = file_info.get("packageFile", "unknown")
                
                for dep in file_info.get("deps", []):
                    dep_name = dep.get("depName", "unknown")
                    current_value = dep.get("currentValue", "unknown")
                    datasource = dep.get("datasource", "unknown")
                    
                    # Get available updates
                    updates = dep.get("updates", [])
                    latest_version = None
                    if updates:
                        # Get the highest version available
                        for update in updates:
                            if update.get("updateType") == "major":
                                latest_version = update.get("newVersion")
                                break
                        if not latest_version and updates:
                            latest_version = updates[-1].get("newVersion")
                    
                    deps[dep_name] = {
                        "version": current_value,
                        "manager": manager,
                        "file": package_file,
                        "datasource": datasource,
                        "latestVersion": latest_version,
                        "updateCount": len(updates)
                    }
        
        result[repo_name] = deps
    
    return result

def compare(old_report, new_report):
    """Compare two reports and return differences."""
    old_deps = extract_deps(old_report)
    new_deps = extract_deps(new_report)
    
    changes = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "newDependencies": 0,
            "removedDependencies": 0,
            "versionChanges": 0,
            "newRepositories": 0,
            "removedRepositories": 0
        },
        "repositories": {},
        "newRepositories": [],
        "removedRepositories": []
    }
    
    all_repos = set(old_deps.keys()) | set(new_deps.keys())
    
    # Check for new/removed repos
    new_repos = set(new_deps.keys()) - set(old_deps.keys())
    removed_repos = set(old_deps.keys()) - set(new_deps.keys())
    
    changes["newRepositories"] = list(new_repos)
    changes["removedRepositories"] = list(removed_repos)
    changes["summary"]["newRepositories"] = len(new_repos)
    changes["summary"]["removedRepositories"] = len(removed_repos)
    
    # Compare each repo
    for repo in sorted(new_deps.keys()):
        old_repo_deps = old_deps.get(repo, {})
        new_repo_deps = new_deps.get(repo, {})
        
        repo_changes = {
            "added": [],
            "removed": [],
            "versionChanged": []
        }
        
        # Find added deps
        for dep_name, dep_info in new_repo_deps.items():
            if dep_name not in old_repo_deps:
                repo_changes["added"].append({
                    "name": dep_name,
                    "version": dep_info["version"],
                    "manager": dep_info["manager"],
                    "file": dep_info["file"],
                    "latestVersion": dep_info["latestVersion"]
                })
                changes["summary"]["newDependencies"] += 1
        
        # Find removed deps
        for dep_name, dep_info in old_repo_deps.items():
            if dep_name not in new_repo_deps:
                repo_changes["removed"].append({
                    "name": dep_name,
                    "version": dep_info["version"],
                    "manager": dep_info["manager"],
                    "file": dep_info["file"]
                })
                changes["summary"]["removedDependencies"] += 1
        
        # Find version changes
        for dep_name, new_info in new_repo_deps.items():
            if dep_name in old_repo_deps:
                old_info = old_repo_deps[dep_name]
                if old_info["version"] != new_info["version"]:
                    repo_changes["versionChanged"].append({
                        "name": dep_name,
                        "oldVersion": old_info["version"],
                        "newVersion": new_info["version"],
                        "manager": new_info["manager"],
                        "file": new_info["file"]
                    })
                    changes["summary"]["versionChanges"] += 1
        
        if repo_changes["added"] or repo_changes["removed"] or repo_changes["versionChanged"]:
            changes["repositories"][repo] = repo_changes
    
    return changes

def print_report(changes):
    """Print a human-readable report."""
    print("\n" + "=" * 60)
    print("  DEPENDENCY CHANGE REPORT")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)
    
    summary = changes["summary"]
    
    print(f"\n📊 SUMMARY:")
    print(f"   🆕 New dependencies:     {summary['newDependencies']}")
    print(f"   ❌ Removed dependencies: {summary['removedDependencies']}")
    print(f"   🔄 Version changes:      {summary['versionChanges']}")
    print(f"   📁 New repositories:     {summary['newRepositories']}")
    print(f"   📁 Removed repositories: {summary['removedRepositories']}")
    
    # New repositories
    if changes["newRepositories"]:
        print(f"\n{'─' * 60}")
        print("📁 NEW REPOSITORIES BEING SCANNED:")
        print("─" * 60)
        for repo in changes["newRepositories"]:
            print(f"   + {repo}")
    
    # Removed repositories
    if changes["removedRepositories"]:
        print(f"\n{'─' * 60}")
        print("📁 REPOSITORIES NO LONGER SCANNED:")
        print("─" * 60)
        for repo in changes["removedRepositories"]:
            print(f"   - {repo}")
    
    # Per-repo changes
    for repo, repo_changes in changes["repositories"].items():
        print(f"\n{'─' * 60}")
        print(f"  {repo}")
        print("─" * 60)
        
        if repo_changes["added"]:
            print(f"\n  🆕 New dependencies:")
            for dep in repo_changes["added"]:
                latest = f" (latest: {dep['latestVersion']})" if dep['latestVersion'] else ""
                print(f"     + {dep['name']} @ {dep['version']}{latest}")
                print(f"       └─ {dep['file']} ({dep['manager']})")
        
        if repo_changes["removed"]:
            print(f"\n  ❌ Removed dependencies:")
            for dep in repo_changes["removed"]:
                print(f"     - {dep['name']} @ {dep['version']}")
                print(f"       └─ was in {dep['file']} ({dep['manager']})")
        
        if repo_changes["versionChanged"]:
            print(f"\n  🔄 Version changed in source:")
            for dep in repo_changes["versionChanged"]:
                print(f"     ~ {dep['name']}: {dep['oldVersion']} → {dep['newVersion']}")
                print(f"       └─ {dep['file']} ({dep['manager']})")
    
    if not changes["repositories"] and not changes["newRepositories"] and not changes["removedRepositories"]:
        print(f"\n  ✅ No changes detected")
    
    print("\n" + "=" * 60 + "\n")

def save_diff_report(changes, output_path):
    """Save the diff as a JSON file."""
    with open(output_path, 'w') as f:
        json.dump(changes, f, indent=2)

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 compare_reports.py <old.json> <new.json> [output.json]")
        sys.exit(1)
    
    old_path = sys.argv[1]
    new_path = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) > 3 else None
    
    old_report = load_report(old_path)
    new_report = load_report(new_path)
    
    changes = compare(old_report, new_report)
    
    print_report(changes)
    
    if output_path:
        save_diff_report(changes, output_path)
        print(f"💾 Diff saved to: {output_path}")

if __name__ == "__main__":
    main()
```

---

### scripts/merge_reports.py

```python
#!/usr/bin/env python3
"""
Merges multiple platform reports into one combined report.
"""

import json
import sys
import os
from datetime import datetime

def load_report(filepath):
    """Load a report file."""
    if not os.path.exists(filepath):
        return {"repositories": {}}
    
    try:
        with open(filepath) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"repositories": {}}

def merge_reports(report_files):
    """Merge multiple reports into one."""
    combined = {
        "generatedAt": datetime.now().isoformat(),
        "platforms": {},
        "repositories": {},
        "summary": {
            "totalRepos": 0,
            "totalDependencies": 0,
            "totalUpdatesAvailable": 0,
            "byPlatform": {}
        }
    }
    
    for platform, filepath in report_files.items():
        report = load_report(filepath)
        repos = report.get("repositories", {})
        
        combined["platforms"][platform] = {
            "repoCount": len(repos),
            "scannedAt": datetime.now().isoformat()
        }
        
        platform_deps = 0
        platform_updates = 0
        
        for repo_name, repo_data in repos.items():
            # Add platform prefix for clarity
            full_name = f"{platform}:{repo_name}"
            combined["repositories"][full_name] = repo_data
            
            # Count deps and updates
            for manager, files in repo_data.get("packageFiles", {}).items():
                for file_info in files:
                    for dep in file_info.get("deps", []):
                        platform_deps += 1
                        platform_updates += len(dep.get("updates", []))
        
        combined["summary"]["byPlatform"][platform] = {
            "repos": len(repos),
            "dependencies": platform_deps,
            "updatesAvailable": platform_updates
        }
        
        combined["summary"]["totalRepos"] += len(repos)
        combined["summary"]["totalDependencies"] += platform_deps
        combined["summary"]["totalUpdatesAvailable"] += platform_updates
    
    return combined

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 merge_reports.py <output.json> [platform:file ...]")
        print("Example: python3 merge_reports.py combined.json github:gh.json gitlab:gl.json")
        sys.exit(1)
    
    output_path = sys.argv[1]
    
    report_files = {}
    for arg in sys.argv[2:]:
        if ':' in arg:
            platform, filepath = arg.split(':', 1)
            report_files[platform] = filepath
    
    combined = merge_reports(report_files)
    
    with open(output_path, 'w') as f:
        json.dump(combined, f, indent=2)
    
    print(f"\n📊 COMBINED REPORT SUMMARY")
    print(f"{'=' * 40}")
    print(f"Total repositories: {combined['summary']['totalRepos']}")
    print(f"Total dependencies: {combined['summary']['totalDependencies']}")
    print(f"Total updates available: {combined['summary']['totalUpdatesAvailable']}")
    print(f"\nBy platform:")
    for platform, stats in combined['summary']['byPlatform'].items():
        print(f"  {platform}: {stats['repos']} repos, {stats['dependencies']} deps, {stats['updatesAvailable']} updates")
    print(f"\n💾 Saved to: {output_path}\n")

if __name__ == "__main__":
    main()
```

---

### scripts/generate_summary.py

```python
#!/usr/bin/env python3
"""
Generates a human-readable markdown summary of the scan.
"""

import json
import sys
import os
from datetime import datetime

def load_report(filepath):
    if not os.path.exists(filepath):
        return {}
    with open(filepath) as f:
        return json.load(f)

def generate_markdown(combined_report, diff_report, output_path):
    """Generate a markdown summary."""
    
    lines = []
    lines.append(f"# Dependency Scan Report")
    lines.append(f"")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append(f"")
    
    # Summary
    summary = combined_report.get("summary", {})
    lines.append(f"## 📊 Summary")
    lines.append(f"")
    lines.append(f"| Metric | Count |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total Repositories | {summary.get('totalRepos', 0)} |")
    lines.append(f"| Total Dependencies | {summary.get('totalDependencies', 0)} |")
    lines.append(f"| Updates Available | {summary.get('totalUpdatesAvailable', 0)} |")
    lines.append(f"")
    
    # By platform
    lines.append(f"## 🌐 By Platform")
    lines.append(f"")
    lines.append(f"| Platform | Repos | Dependencies | Updates |")
    lines.append(f"|----------|-------|--------------|---------|")
    for platform, stats in summary.get("byPlatform", {}).items():
        lines.append(f"| {platform} | {stats['repos']} | {stats['dependencies']} | {stats['updatesAvailable']} |")
    lines.append(f"")
    
    # Changes since last scan
    if diff_report:
        diff_summary = diff_report.get("summary", {})
        lines.append(f"## 🔄 Changes Since Last Scan")
        lines.append(f"")
        
        if any(diff_summary.values()):
            lines.append(f"| Change Type | Count |")
            lines.append(f"|-------------|-------|")
            lines.append(f"| 🆕 New Dependencies | {diff_summary.get('newDependencies', 0)} |")
            lines.append(f"| ❌ Removed Dependencies | {diff_summary.get('removedDependencies', 0)} |")
            lines.append(f"| 🔄 Version Changes | {diff_summary.get('versionChanges', 0)} |")
            lines.append(f"| 📁 New Repositories | {diff_summary.get('newRepositories', 0)} |")
            lines.append(f"| 📁 Removed Repositories | {diff_summary.get('removedRepositories', 0)} |")
            lines.append(f"")
            
            # Detail new deps
            if diff_report.get("repositories"):
                lines.append(f"### Detailed Changes")
                lines.append(f"")
                
                for repo, changes in diff_report.get("repositories", {}).items():
                    lines.append(f"#### {repo}")
                    lines.append(f"")
                    
                    if changes.get("added"):
                        lines.append(f"**New dependencies:**")
                        for dep in changes["added"]:
                            latest = f" → latest: {dep['latestVersion']}" if dep.get('latestVersion') else ""
                            lines.append(f"- `{dep['name']}` @ `{dep['version']}`{latest}")
                        lines.append(f"")
                    
                    if changes.get("removed"):
                        lines.append(f"**Removed dependencies:**")
                        for dep in changes["removed"]:
                            lines.append(f"- `{dep['name']}` @ `{dep['version']}`")
                        lines.append(f"")
                    
                    if changes.get("versionChanged"):
                        lines.append(f"**Version changes:**")
                        for dep in changes["versionChanged"]:
                            lines.append(f"- `{dep['name']}`: `{dep['oldVersion']}` → `{dep['newVersion']}`")
                        lines.append(f"")
        else:
            lines.append(f"✅ No changes since last scan.")
            lines.append(f"")
    
    # Write to file
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))
    
    print(f"📄 Markdown report saved to: {output_path}")

def main():
    if len(sys.argv) != 4:
        print("Usage: python3 generate_summary.py <combined.json> <diff.json> <output.md>")
        sys.exit(1)
    
    combined = load_report(sys.argv[1])
    diff = load_report(sys.argv[2])
    
    generate_markdown(combined, diff, sys.argv[3])

if __name__ == "__main__":
    main()
```

---

## Step 4: Create the GitHub Action

### .github/workflows/scan.yml

```yaml
name: Daily Dependency Scan

on:
  schedule:
    - cron: '0 9 * * *'  # Every day at 9 AM UTC
  workflow_dispatch:       # Manual trigger

permissions:
  contents: write

env:
  SCAN_DATE: ""

jobs:

  # ════════════════════════════════════════════════════════════
  # JOB 1: SCAN GITHUB REPOS
  # ════════════════════════════════════════════════════════════
  scan-github:
    runs-on: ubuntu-latest
    outputs:
      has_repos: ${{ steps.check.outputs.has_repos }}
    
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Check if GitHub repos exist
        id: check
        run: |
          REPOS=$(cat config/github.json | jq -r '.repositories | length')
          if [ "$REPOS" -gt 0 ]; then
            echo "has_repos=true" >> "$GITHUB_OUTPUT"
          else
            echo "has_repos=false" >> "$GITHUB_OUTPUT"
            echo "No GitHub repos configured, skipping..."
          fi

      - name: Setup Node
        if: steps.check.outputs.has_repos == 'true'
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install Renovate
        if: steps.check.outputs.has_repos == 'true'
        run: npm install -g renovate

      - name: Read repo list
        if: steps.check.outputs.has_repos == 'true'
        id: repos
        run: |
          REPOS=$(cat config/github.json | jq -r '.repositories | join(" ")')
          echo "list=$REPOS" >> "$GITHUB_OUTPUT"

      - name: Run Renovate on GitHub repos
        if: steps.check.outputs.has_repos == 'true'
        env:
          RENOVATE_TOKEN: ${{ secrets.GITHUB_RENOVATE_TOKEN }}
        run: |
          renovate \
            --platform=github \
            --dry-run=full \
            --report-type=file \
            --report-path=reports/latest/github.json \
            ${{ steps.repos.outputs.list }}

      - name: Upload GitHub report
        if: steps.check.outputs.has_repos == 'true'
        uses: actions/upload-artifact@v4
        with:
          name: report-github
          path: reports/latest/github.json

  # ════════════════════════════════════════════════════════════
  # JOB 2: SCAN GITLAB REPOS
  # ════════════════════════════════════════════════════════════
  scan-gitlab:
    runs-on: ubuntu-latest
    outputs:
      has_repos: ${{ steps.check.outputs.has_repos }}
    
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Check if GitLab repos exist
        id: check
        run: |
          REPOS=$(cat config/gitlab.json | jq -r '.repositories | length')
          if [ "$REPOS" -gt 0 ]; then
            echo "has_repos=true" >> "$GITHUB_OUTPUT"
          else
            echo "has_repos=false" >> "$GITHUB_OUTPUT"
            echo "No GitLab repos configured, skipping..."
          fi

      - name: Setup Node
        if: steps.check.outputs.has_repos == 'true'
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install Renovate
        if: steps.check.outputs.has_repos == 'true'
        run: npm install -g renovate

      - name: Read config
        if: steps.check.outputs.has_repos == 'true'
        id: config
        run: |
          REPOS=$(cat config/gitlab.json | jq -r '.repositories | join(" ")')
          ENDPOINT=$(cat config/gitlab.json | jq -r '.endpoint // empty')
          echo "repos=$REPOS" >> "$GITHUB_OUTPUT"
          echo "endpoint=$ENDPOINT" >> "$GITHUB_OUTPUT"

      - name: Run Renovate on GitLab repos
        if: steps.check.outputs.has_repos == 'true'
        env:
          RENOVATE_TOKEN: ${{ secrets.GITLAB_RENOVATE_TOKEN }}
        run: |
          ENDPOINT_ARG=""
          if [ -n "${{ steps.config.outputs.endpoint }}" ]; then
            ENDPOINT_ARG="--endpoint=${{ steps.config.outputs.endpoint }}"
          fi
          
          renovate \
            --platform=gitlab \
            $ENDPOINT_ARG \
            --dry-run=full \
            --report-type=file \
            --report-path=reports/latest/gitlab.json \
            ${{ steps.config.outputs.repos }}

      - name: Upload GitLab report
        if: steps.check.outputs.has_repos == 'true'
        uses: actions/upload-artifact@v4
        with:
          name: report-gitlab
          path: reports/latest/gitlab.json

  # ════════════════════════════════════════════════════════════
  # JOB 3: SCAN BITBUCKET REPOS
  # ════════════════════════════════════════════════════════════
  scan-bitbucket:
    runs-on: ubuntu-latest
    outputs:
      has_repos: ${{ steps.check.outputs.has_repos }}
    
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Check if Bitbucket repos exist
        id: check
        run: |
          REPOS=$(cat config/bitbucket.json | jq -r '.repositories | length')
          if [ "$REPOS" -gt 0 ]; then
            echo "has_repos=true" >> "$GITHUB_OUTPUT"
          else
            echo "has_repos=false" >> "$GITHUB_OUTPUT"
            echo "No Bitbucket repos configured, skipping..."
          fi

      - name: Setup Node
        if: steps.check.outputs.has_repos == 'true'
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install Renovate
        if: steps.check.outputs.has_repos == 'true'
        run: npm install -g renovate

      - name: Read config
        if: steps.check.outputs.has_repos == 'true'
        id: config
        run: |
          REPOS=$(cat config/bitbucket.json | jq -r '.repositories | join(" ")')
          echo "repos=$REPOS" >> "$GITHUB_OUTPUT"

      - name: Run Renovate on Bitbucket repos
        if: steps.check.outputs.has_repos == 'true'
        env:
          RENOVATE_TOKEN: ${{ secrets.BITBUCKET_RENOVATE_TOKEN }}
          RENOVATE_USERNAME: ${{ secrets.BITBUCKET_USERNAME }}
        run: |
          renovate \
            --platform=bitbucket \
            --username=$RENOVATE_USERNAME \
            --dry-run=full \
            --report-type=file \
            --report-path=reports/latest/bitbucket.json \
            ${{ steps.config.outputs.repos }}

      - name: Upload Bitbucket report
        if: steps.check.outputs.has_repos == 'true'
        uses: actions/upload-artifact@v4
        with:
          name: report-bitbucket
          path: reports/latest/bitbucket.json

  # ════════════════════════════════════════════════════════════
  # JOB 4: SCAN AZURE DEVOPS REPOS
  # ════════════════════════════════════════════════════════════
  scan-azure:
    runs-on: ubuntu-latest
    outputs:
      has_repos: ${{ steps.check.outputs.has_repos }}
    
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Check if Azure repos exist
        id: check
        run: |
          REPOS=$(cat config/azure.json | jq -r '.repositories | length')
          if [ "$REPOS" -gt 0 ]; then
            echo "has_repos=true" >> "$GITHUB_OUTPUT"
          else
            echo "has_repos=false" >> "$GITHUB_OUTPUT"
            echo "No Azure DevOps repos configured, skipping..."
          fi

      - name: Setup Node
        if: steps.check.outputs.has_repos == 'true'
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install Renovate
        if: steps.check.outputs.has_repos == 'true'
        run: npm install -g renovate

      - name: Read config
        if: steps.check.outputs.has_repos == 'true'
        id: config
        run: |
          REPOS=$(cat config/azure.json | jq -r '.repositories | join(" ")')
          ENDPOINT=$(cat config/azure.json | jq -r '.endpoint // empty')
          echo "repos=$REPOS" >> "$GITHUB_OUTPUT"
          echo "endpoint=$ENDPOINT" >> "$GITHUB_OUTPUT"

      - name: Run Renovate on Azure repos
        if: steps.check.outputs.has_repos == 'true'
        env:
          RENOVATE_TOKEN: ${{ secrets.AZURE_RENOVATE_TOKEN }}
        run: |
          ENDPOINT_ARG=""
          if [ -n "${{ steps.config.outputs.endpoint }}" ]; then
            ENDPOINT_ARG="--endpoint=${{ steps.config.outputs.endpoint }}"
          fi
          
          renovate \
            --platform=azure \
            $ENDPOINT_ARG \
            --dry-run=full \
            --report-type=file \
            --report-path=reports/latest/azure.json \
            ${{ steps.config.outputs.repos }}

      - name: Upload Azure report
        if: steps.check.outputs.has_repos == 'true'
        uses: actions/upload-artifact@v4
        with:
          name: report-azure
          path: reports/latest/azure.json

  # ════════════════════════════════════════════════════════════
  # JOB 5: MERGE, COMPARE, AND COMMIT
  # ════════════════════════════════════════════════════════════
  finalize:
    needs: [scan-github, scan-gitlab, scan-bitbucket, scan-azure]
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set date
        id: date
        run: |
          DATE=$(date +%Y-%m-%d_%H%M%S)
          echo "date=$DATE" >> "$GITHUB_OUTPUT"

      - name: Create directories
        run: |
          mkdir -p reports/latest
          mkdir -p reports/history/${{ steps.date.outputs.date }}

      - name: Download GitHub report
        if: needs.scan-github.outputs.has_repos == 'true'
        uses: actions/download-artifact@v4
        with:
          name: report-github
          path: reports/latest/
        continue-on-error: true

      - name: Download GitLab report
        if: needs.scan-gitlab.outputs.has_repos == 'true'
        uses: actions/download-artifact@v4
        with:
          name: report-gitlab
          path: reports/latest/
        continue-on-error: true

      - name: Download Bitbucket report
        if: needs.scan-bitbucket.outputs.has_repos == 'true'
        uses: actions/download-artifact@v4
        with:
          name: report-bitbucket
          path: reports/latest/
        continue-on-error: true

      - name: Download Azure report
        if: needs.scan-azure.outputs.has_repos == 'true'
        uses: actions/download-artifact@v4
        with:
          name: report-azure
          path: reports/latest/
        continue-on-error: true

      - name: Create empty reports for missing platforms
        run: |
          for platform in github gitlab bitbucket azure; do
            if [ ! -f "reports/latest/${platform}.json" ]; then
              echo '{"repositories":{}}' > "reports/latest/${platform}.json"
            fi
          done

      - name: Merge all reports
        run: |
          python3 scripts/merge_reports.py \
            reports/latest/combined.json \
            github:reports/latest/github.json \
            gitlab:reports/latest/gitlab.json \
            bitbucket:reports/latest/bitbucket.json \
            azure:reports/latest/azure.json

      - name: Compare with previous
        run: |
          python3 scripts/compare_reports.py \
            reports/previous/combined.json \
            reports/latest/combined.json \
            reports/latest/diff.json

      - name: Generate markdown summary
        run: |
          python3 scripts/generate_summary.py \
            reports/latest/combined.json \
            reports/latest/diff.json \
            reports/latest/summary.md

      - name: Display summary in logs
        run: |
          echo ""
          echo "════════════════════════════════════════════════════════════"
          cat reports/latest/summary.md
          echo "════════════════════════════════════════════════════════════"

      - name: Archive to history
        run: |
          cp reports/latest/*.json reports/history/${{ steps.date.outputs.date }}/
          cp reports/latest/summary.md reports/history/${{ steps.date.outputs.date }}/

      - name: Update previous baseline
        run: |
          cp reports/latest/combined.json reports/previous/combined.json
          cp reports/latest/github.json reports/previous/github.json 2>/dev/null || true
          cp reports/latest/gitlab.json reports/previous/gitlab.json 2>/dev/null || true
          cp reports/latest/bitbucket.json reports/previous/bitbucket.json 2>/dev/null || true
          cp reports/latest/azure.json reports/previous/azure.json 2>/dev/null || true

      - name: Commit reports
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add reports/
          git diff --cached --quiet || git commit -m "📊 Dependency scan ${{ steps.date.outputs.date }}"
          git push
```

---

## Step 5: Update .gitignore

```
.env
node_modules/
```

---

## Step 6: Add Secrets to GitHub

Go to: `https://github.com/rai-wtag/renov-runner/settings/secrets/actions`

Add these secrets (only add the ones you need now):

| Secret Name | Value | Required Now? |
|-------------|-------|---------------|
| `GITHUB_RENOVATE_TOKEN` | Your GitHub PAT | ✅ YES |
| `GITLAB_RENOVATE_TOKEN` | GitLab access token | ❌ Later |
| `BITBUCKET_RENOVATE_TOKEN` | Bitbucket app password | ❌ Later |
| `BITBUCKET_USERNAME` | Your Bitbucket username | ❌ Later |
| `AZURE_RENOVATE_TOKEN` | Azure DevOps PAT | ❌ Later |

---

## Step 7: Commit Everything

```bash
git add .
git status
```

You should see:

```
new file:   .github/workflows/scan.yml
new file:   config/azure.json
new file:   config/bitbucket.json
new file:   config/github.json
new file:   config/gitlab.json
new file:   reports/previous/azure.json
new file:   reports/previous/bitbucket.json
new file:   reports/previous/combined.json
new file:   reports/previous/github.json
new file:   reports/previous/gitlab.json
new file:   scripts/compare_reports.py
new file:   scripts/generate_summary.py
new file:   scripts/merge_reports.py
```

```bash
git commit -m "complete multi-platform dependency scanner"
git push
```

---

## Step 8: Run It

Go to: `https://github.com/rai-wtag/renov-runner/actions`

Click **"Daily Dependency Scan"** → **"Run workflow"** → **"Run workflow"**

Wait 3-5 minutes.

---

## Step 9: Test Change Detection

After the first run succeeds:

### Add new deps to pilot05 (Ruby):

Edit `Gemfile`, add:

```ruby
gem "bcrypt", "3.1.16"
gem "pg", "1.3.0"
```

Commit and push.

### Add new deps to pilot06 (Node.js):

Edit `package.json`, add to dependencies:

```json
"dotenv": "10.0.0",
"cors": "2.8.0"
```

Commit and push.

### Run the action again

The output will show:

```
📊 SUMMARY:
   🆕 New dependencies:     4
   ❌ Removed dependencies: 0
   🔄 Version changes:      0

───────────────────────────────────────────────────────────
  github:rai-wtag/renov-pilot05
───────────────────────────────────────────────────────────

  🆕 New dependencies:
     + bcrypt @ 3.1.16 (latest: 3.1.20)
       └─ Gemfile (bundler)
     + pg @ 1.3.0 (latest: 1.5.4)
       └─ Gemfile (bundler)

───────────────────────────────────────────────────────────
  github:rai-wtag/renov-pilot06
───────────────────────────────────────────────────────────

  🆕 New dependencies:
     + cors @ 2.8.0 (latest: 2.8.5)
       └─ package.json (npm)
     + dotenv @ 10.0.0 (latest: 16.4.5)
       └─ package.json (npm)
```

---

## Adding More Repos Later

Just edit `config/github.json`:

```json
{
  "platform": "github",
  "repositories": [
    "rai-wtag/renov-pilot05",
    "rai-wtag/renov-pilot06",
    "rai-wtag/new-repo-1",
    "rai-wtag/new-repo-2",
    "rai-wtag/new-repo-3"
  ]
}
```

Commit and push. Next scan picks them up automatically.

---

## Adding GitLab Later

1. Get GitLab token (Settings → Access Tokens → Create with `api` scope)
2. Add secret `GITLAB_RENOVATE_TOKEN` in GitHub
3. Edit `config/gitlab.json`:

```json
{
  "platform": "gitlab",
  "endpoint": "https://gitlab.com/api/v4",
  "repositories": [
    "your-group/your-repo1",
    "your-group/your-repo2"
  ]
}
```

4. Commit and push. Done.

---

## What You Get

```
✅ Scans GitHub repos
✅ Scans GitLab repos (when configured)
✅ Scans Bitbucket repos (when configured)
✅ Scans Azure DevOps repos (when configured)
✅ Merges all into one combined report
✅ Compares with previous scan
✅ Shows NEW, REMOVED, VERSION CHANGED
✅ Generates markdown summary
✅ Saves history with timestamps
✅ Runs daily automatically
✅ Can trigger manually anytime
✅ Scales to 100+ repos
✅ All dry-run — nothing modified
```

---

**Run Steps 1-8 now. Share the action output when it completes.**