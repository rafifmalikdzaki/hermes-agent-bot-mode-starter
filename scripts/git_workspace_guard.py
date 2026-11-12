#!/usr/bin/env python3
"""
git_workspace_guard.py
Audits all research repositories in ~/Research/ for uncommitted changes, modified configs,
and untracked research scripts. Automatically creates timestamped .patch diff backups
in ~/Research/.diff_backups/YYYY-MM-DD/ to protect against evidence loss, and writes
an integrity audit report directly into the Obsidian vault.
Runs 100% locally with 0 LLM tokens spent.
"""

import sys
import os
import subprocess
import datetime
from pathlib import Path

RESEARCH_DIR = Path.home() / "Research"
BACKUP_ROOT = RESEARCH_DIR / ".diff_backups"
VAULT_OUTPUT = Path.home() / "vaults" / "research-vault" / "Daily Notes" / "Workspace Integrity Audit.md"

def find_git_repos():
    repos = []
    skip_dirs = {
        "node_modules", ".venv", "venv", "data", "outputs", "archive", "archive-old",
        "archive-221026", ".local", ".npm", ".cache", "checkpoints", "artifacts"
    }
    for root, dirs, _ in os.walk(RESEARCH_DIR):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        if ".git" in dirs:
            repos.append(Path(root))
            dirs.remove(".git")
    return sorted(repos)

def inspect_repo(repo_path, backup_date_dir=None):
    try:
        branch = subprocess.check_output(
            ["git", "-C", str(repo_path), "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL, timeout=3
        ).decode().strip()

        status_raw = subprocess.check_output(
            ["git", "-C", str(repo_path), "status", "--porcelain"],
            stderr=subprocess.DEVNULL, timeout=3
        ).decode().strip()

        status_lines = status_raw.splitlines() if status_raw else []
        last_commit = subprocess.check_output(
            ["git", "-C", str(repo_path), "log", "-1", "--format=%h %s (%cr)"],
            stderr=subprocess.DEVNULL, timeout=3
        ).decode().strip()

        diff_text = ""
        backup_patch = None

        if status_lines:
            # Capture working tree diff
            diff_text = subprocess.check_output(
                ["git", "-C", str(repo_path), "diff"],
                stderr=subprocess.DEVNULL, timeout=5
            ).decode()

            if backup_date_dir and diff_text.strip():
                patch_file = backup_date_dir / f"{repo_path.name}_{branch.replace('/', '_')}.patch"
                patch_file.write_text(diff_text, encoding="utf-8")
                backup_patch = patch_file

        return {
            "path": repo_path,
            "rel_path": repo_path.relative_to(RESEARCH_DIR),
            "name": repo_path.name,
            "branch": branch,
            "dirty_count": len(status_lines),
            "status_lines": status_lines,
            "last_commit": last_commit,
            "backup_patch": backup_patch
        }
    except Exception:
        return None

def format_markdown(audited_repos, backup_date_dir):
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    dirty_repos = [r for r in audited_repos if r["dirty_count"] > 0]
    clean_repos = [r for r in audited_repos if r["dirty_count"] == 0]

    lines = [
        "---",
        "tags:",
        "  - git-audit",
        "  - workspace-integrity",
        "  - evidence-protection",
        f"audited_at: \"{now_str}\"",
        f"total_repositories: {len(audited_repos)}",
        f"dirty_repositories: {len(dirty_repos)}",
        "---",
        "",
        f"# 🛡️ Research Git Workspace Integrity & Diff Preservation Audit",
        "",
        f"> [!INFO] Audit Summary — {now_str}",
        f"> Audited **{len(audited_repos)}** repositories across `~/Research/`. **{len(dirty_repos)}** repos have uncommitted changes; **{len(clean_repos)}** are completely clean.",
        ""
    ]

    if dirty_repos:
        lines.append("## ⚠️ Repositories with Uncommitted Research Changes")
        lines.append("")
        lines.append("| Repository | Active Branch | Dirty Files | Diff Backup Patch | Last Commit |")
        lines.append("| :--- | :---: | :---: | :--- | :--- |")
        for r in dirty_repos:
            patch_str = f"`{r['backup_patch'].name}`" if r['backup_patch'] else "_No text diff (untracked only)_"
            lines.append(f"| **`{r['rel_path']}`** | `{r['branch']}` | `⚠️ {r['dirty_count']} files` | {patch_str} | _{r['last_commit']}_ |")
        lines.append("")
        
        lines.append("### Detailed File Modifications by Repository")
        for r in dirty_repos:
            lines.append(f"#### `{r['rel_path']}` (`{r['branch']}`)")
            lines.append("```")
            for line in r["status_lines"][:12]:
                lines.append(line)
            if len(r["status_lines"]) > 12:
                lines.append(f"... and {len(r['status_lines']) - 12} more uncommitted files")
            lines.append("```")
            lines.append("")

    lines.append("## ✅ Clean Repositories (Synchronized)")
    lines.append("")
    lines.append("| Repository | Active Branch | Last Commit |")
    lines.append("| :--- | :---: | :--- |")
    for r in clean_repos[:15]:
        lines.append(f"| `{r['rel_path']}` | `{r['branch']}` | _{r['last_commit']}_ |")
    if len(clean_repos) > 15:
        lines.append(f"| _... and {len(clean_repos) - 15} more clean repositories_ | | |")

    lines.append("")
    lines.append("---")
    lines.append(f"💾 **Timestamped Diff Backups**: Saved under `{backup_date_dir}`")

    return "\n".join(lines)

def main():
    today_str = datetime.date.today().isoformat()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    backup_date_dir = BACKUP_ROOT / today_str
    backup_date_dir.mkdir(parents=True, exist_ok=True)

    repos = find_git_repos()
    audited = []
    for r in repos:
        res = inspect_repo(r, backup_date_dir=backup_date_dir)
        if res:
            audited.append(res)

    dirty = [r for r in audited if r["dirty_count"] > 0]
    
    print(f"\n🛡️ Research Workspace Integrity Scan ({now_str})")
    print("═" * 75)
    print(f"• Total Repositories Audited: {len(audited)}")
    print(f"• Repositories with Uncommitted Work: {len(dirty)}")
    
    for r in dirty:
        patch_info = f" -> Backup: {r['backup_patch'].name}" if r['backup_patch'] else ""
        print(f"  ⚠️  {str(r['rel_path']):35s} [{r['branch']}] : {r['dirty_count']} dirty files{patch_info}")

    print("═" * 75)
    
    VAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    VAULT_OUTPUT.write_text(format_markdown(audited, backup_date_dir), encoding="utf-8")
    print(f"✅ Saved workspace integrity report to Obsidian: {VAULT_OUTPUT}")

if __name__ == "__main__":
    main()
