---
name: system-diagnosis-and-agent-inspector
description: Curated system diagnosis, hardware profiling, resource optimization, and live coding agent inspection for IUABTW workstation. Inspects active coding agents (Claude, Vibe, Hermes, Aider, Antigravity) across repositories and returns real-time status summaries.
---

# System Diagnosis & Coding Agent Inspector (IUABTW Curated)

Use this skill when the user asks to:
- Check what any running coding agent is working on (Claude, Mistral Vibe, Hermes, Aider, Antigravity).
- Summarize live coding agent status, active workspaces, git branches, and current tasks.
- Diagnose local hardware health (CPU load across 20 vCPUs, RAM, NVIDIA RTX 3070 VRAM, Docker containers, remote GPU servers).
- Optimize system resources, clean stale locks, trim daemon memory, or compact logs.

---

## 🛠️ Canonical CLI Commands

### 1. Inspect All Running Coding Agents
To scan all active coding agent processes and summarize their workspaces, git state, and recent prompts:
```bash
agent-status
```
To save the live status report directly into the Obsidian vault:
```bash
agent-status --save
```
*(Saves to `~/vaults/research-vault/Daily Notes/Agent Status Summary.md`).*

For structured JSON parsing:
```bash
agent-status --json
```

### 2. Workstation Diagnostics & Hardware Health
To inspect hardware metrics (RTX 3070 Ti VRAM, thermals, Docker containers, load averages, RAM/Swap):
```bash
system-tune
```

### 3. Safe System Optimization
To trim daemon memory, prune stale locks, and clear oversized logs:
```bash
system-tune --optimize
```

---

## 🤖 Interpreting Agent Findings

When reporting back to the user, format your answer as a concise bulleted briefing:
1. **Agent Name & PID**: (e.g., Claude Code `12214`, Mistral Vibe `126992`).
2. **Project & Directory**: (e.g., `Research/kalbe/crd-dem-surrogate`).
3. **Current Task / Query**: Summarize what prompt the agent was asked to solve.
4. **Git State**: Active branch and number of modified/dirty files.
5. **System Overhead**: CPU and RAM footprint.
