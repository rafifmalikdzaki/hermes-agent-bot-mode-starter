#!/usr/bin/env python3
"""
agent_inspector.py
Discovers, audits, and summarizes all running coding agents (Vibe, Claude, Hermes, Aider, Antigravity, etc.)
Extracts process PID, CPU/RAM, working directory, git branch/dirty diffs, and recent prompt instructions.
Outputs concise terminal summary or saves a structured report directly into Obsidian.
"""

import sys
import os
import re
import json
import psutil
import datetime
import subprocess
from pathlib import Path

DEFAULT_VAULT_PATH = Path.home() / "vaults" / "research-vault" / "Daily Notes" / "Agent Status Summary.md"

KNOWN_AGENTS = {
    "vibe-rs": {"name": "Mistral Vibe", "type": "vibe"},
    "vibe": {"name": "Mistral Vibe", "type": "vibe"},
    "claude-desktop": {"name": "Claude Desktop", "type": "claude"},
    "claude": {"name": "Claude Code", "type": "claude"},
    "aider": {"name": "Aider", "type": "aider"},
    "hermes": {"name": "Hermes Agent", "type": "hermes"},
    "antigravity": {"name": "Antigravity Agent", "type": "antigravity"},
    "agy": {"name": "Antigravity CLI", "type": "antigravity"},
    "codex": {"name": "Codex", "type": "codex"},
    "copilot": {"name": "GitHub Copilot", "type": "copilot"}
}

def get_git_info(cwd):
    if not cwd or not os.path.isdir(cwd):
        return None
    try:
        branch = subprocess.check_output(
            ["git", "-C", cwd, "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL, timeout=2
        ).decode().strip()
        status_lines = subprocess.check_output(
            ["git", "-C", cwd, "status", "--porcelain"],
            stderr=subprocess.DEVNULL, timeout=2
        ).decode().strip().splitlines()
        dirty_count = len(status_lines)
        last_commit = subprocess.check_output(
            ["git", "-C", cwd, "log", "-1", "--format=%s (%cr)"],
            stderr=subprocess.DEVNULL, timeout=2
        ).decode().strip()
        return {
            "branch": branch,
            "dirty_files": dirty_count,
            "last_commit": last_commit
        }
    except Exception:
        return None

def get_vibe_recent_activity(cwd):
    """Fetches recent user queries and activity from Vibe logs and history."""
    queries = []
    hist_file = Path.home() / ".vibe" / "vibehistory"
    if hist_file.is_file():
        try:
            lines = hist_file.read_text(encoding="utf-8", errors="ignore").splitlines()
            for line in reversed(lines):
                cleaned = line.strip().strip('"')
                if cleaned and not cleaned.startswith("/") and len(cleaned) > 5:
                    queries.append(cleaned[:120])
                if len(queries) >= 2:
                    break
        except Exception:
            pass
    return queries

def get_hermes_status():
    """Fetches active tasks and telemetry from Hermes."""
    info = {"gateway": "Unknown", "active_jobs": 0, "active_watchdogs": 0}
    try:
        monitors_file = Path.home() / ".hermes" / "monitors.json"
        if monitors_file.is_file():
            data = json.loads(monitors_file.read_text(encoding="utf-8"))
            info["active_watchdogs"] = len(data)
    except Exception:
        pass
    return info

def inspect_running_agents():
    found = []
    seen_pids = set()

    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info', 'create_time', 'cwd']):
        try:
            pinfo = proc.info
            name = (pinfo.get('name') or '').lower()
            cmdline = " ".join(pinfo.get('cmdline') or []).lower()
            pid = pinfo.get('pid')

            if pid in seen_pids:
                continue

            matched_agent = None
            for key, agent_meta in KNOWN_AGENTS.items():
                if key in name or key in cmdline:
                    matched_agent = agent_meta
                    break

            # Filter out helper child processes or chrome zygotes
            if matched_agent:
                if "zygote" in cmdline or "crashpad" in cmdline or "gpu-process" in cmdline or "utility" in cmdline:
                    continue

                seen_pids.add(pid)
                
                # Resolve working directory
                cwd = None
                try:
                    cwd = proc.cwd()
                except Exception:
                    try:
                        cwd = os.readlink(f"/proc/{pid}/cwd")
                    except Exception:
                        pass

                mem_mb = (pinfo.get('memory_info').rss / (1024 * 1024)) if pinfo.get('memory_info') else 0.0
                cpu = proc.cpu_percent(interval=0.1)
                runtime_seconds = datetime.datetime.now().timestamp() - pinfo.get('create_time', 0)
                uptime_str = str(datetime.timedelta(seconds=int(runtime_seconds)))

                git_info = get_git_info(cwd)
                recent_queries = []
                if matched_agent["type"] == "vibe":
                    recent_queries = get_vibe_recent_activity(cwd)
                elif matched_agent["type"] == "hermes":
                    hermes_meta = get_hermes_status()
                    recent_queries.append(f"Gateway daemon running | Watchdogs active: {hermes_meta['active_watchdogs']}")

                project_name = Path(cwd).name if cwd else "Unknown"

                found.append({
                    "name": matched_agent["name"],
                    "type": matched_agent["type"],
                    "pid": pid,
                    "cpu": cpu,
                    "mem_mb": mem_mb,
                    "uptime": uptime_str,
                    "cwd": cwd or "N/A",
                    "project": project_name,
                    "git": git_info,
                    "recent_activity": recent_queries
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return found

def consolidate_agent_processes(agents):
    """Groups multiple processes belonging to the same agent and workspace."""
    grouped = {}
    for a in agents:
        key = (a["name"], a["cwd"])
        if key not in grouped:
            grouped[key] = {
                "name": a["name"],
                "type": a["type"],
                "pids": [a["pid"]],
                "cpu": a["cpu"],
                "mem_mb": a["mem_mb"],
                "uptime": a["uptime"],
                "cwd": a["cwd"],
                "project": a["project"],
                "git": a["git"],
                "recent_activity": a["recent_activity"]
            }
        else:
            grouped[key]["pids"].append(a["pid"])
            grouped[key]["cpu"] += a["cpu"]
            grouped[key]["mem_mb"] += a["mem_mb"]
            if not grouped[key]["git"] and a["git"]:
                grouped[key]["git"] = a["git"]
            if not grouped[key]["recent_activity"] and a["recent_activity"]:
                grouped[key]["recent_activity"] = a["recent_activity"]
    return list(grouped.values())

def format_markdown_report(agents):
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "---",
        "tags:",
        "  - coding-agents",
        "  - system-status",
        "  - telemetry",
        f"updated_at: \"{now_str}\"",
        f"active_agents: {len(agents)}",
        "---",
        "",
        f"# 🤖 Coding Agents Live Status Summary — {now_str}",
        "",
        f"> [!INFO] Active Coding Agent Workspaces: **{len(agents)} running**",
        ""
    ]

    for a in agents:
        pid_str = ", ".join(str(p) for p in a["pids"])
        lines.append(f"## {a['name']} (PID: `{pid_str}`)")
        lines.append(f"- **Project Workspace**: `{a['project']}` (`{a['cwd']}`)")
        lines.append(f"- **Resource Consumption**: Total CPU: `{a['cpu']:.1f}%` | Memory: `{a['mem_mb']:.1f} MB` | Uptime: `{a['uptime']}`")
        
        if a["git"]:
            g = a["git"]
            lines.append(f"- **Git Status**: Branch `{g['branch']}` | Dirty Files: `{g['dirty_files']}`")
            lines.append(f"- **Latest Commit**: _{g['last_commit']}_")

        if a["recent_activity"]:
            lines.append("- **Recent Task / Prompt**:")
            for q in a["recent_activity"]:
                lines.append(f"  - > {q}")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)

def main():
    save_vault = "--save" in sys.argv or "-s" in sys.argv
    json_output = "--json" in sys.argv

    raw_agents = inspect_running_agents()
    agents = consolidate_agent_processes(raw_agents)

    if json_output:
        print(json.dumps(agents, indent=2))
        return

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n🔍 Active Coding Agents Summary ({now_str})")
    print("═" * 75)
    
    if not agents:
        print("No active coding agent processes found.")
    else:
        for a in agents:
            pid_str = f"PID: {a['pids'][0]}" if len(a['pids']) == 1 else f"PIDs: {','.join(str(p) for p in a['pids'])}"
            print(f"• \033[1m{a['name']}\033[0m [{pid_str}] | CPU: {a['cpu']:.1f}% | RAM: {a['mem_mb']:.1f}MB | Up: {a['uptime']}")
            print(f"  📂 Workspace: {a['cwd']}")
            if a["git"]:
                g = a["git"]
                dirty_str = f"(\033[33m{g['dirty_files']} dirty files\033[0m)" if g['dirty_files'] > 0 else "(\033[32mclean\033[0m)"
                print(f"  🌿 Git: {g['branch']} {dirty_str} | Commit: {g['last_commit']}")
            if a["recent_activity"]:
                print(f"  💬 Recent Query/Task: \"{a['recent_activity'][0]}\"")
            print()

    print("═" * 75)

    if save_vault:
        DEFAULT_VAULT_PATH.parent.mkdir(parents=True, exist_ok=True)
        DEFAULT_VAULT_PATH.write_text(format_markdown_report(agents), encoding="utf-8")
        print(f"✅ Saved live status summary to Obsidian: {DEFAULT_VAULT_PATH}")

if __name__ == "__main__":
    main()
