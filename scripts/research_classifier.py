#!/usr/bin/env python3
"""
Research vs Non-Research Project Classifier & Findings Synthesizer.

Independently scans workstation directories (~/Research, ~/Projects, ~/Documents/Academic),
evaluates repository artifacts (LaTeX, BibTeX, ML checkpoints, papers, datasets, configs),
classifies projects into Research vs Non-Research/Tooling, synthesizes current findings,
and publishes a comprehensive catalog directly to the Obsidian Research Vault.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class ProjectMetadata:
    name: str
    path: str
    category: str  # ACADEMIC_RESEARCH, APPLIED_ML_TRIAL, ENGINEERING_TOOLING, INFRASTRUCTURE_DEV, ARCHIVE_EXPLORATORY
    is_research: bool
    confidence: float
    reasoning: List[str]
    git_branch: Optional[str] = None
    git_uncommitted_changes: int = 0
    git_last_commit: Optional[str] = None
    git_last_commit_date: Optional[str] = None
    has_latex: bool = False
    has_bibtex: bool = False
    has_checkpoints: bool = False
    has_datasets: bool = False
    ml_frameworks: List[str] = field(default_factory=list)
    key_metrics: List[str] = field(default_factory=list)
    summary: str = ""
    findings: str = ""
    next_steps: str = ""


SCAN_ROOTS = [
    Path.home() / "Research",
    Path.home() / "Projects" / "active",
    Path.home() / "Projects" / "tools",
    Path.home() / "Projects" / "experiments",
    Path.home() / "Documents" / "Academic",
]

# Nested directories inside ~/Research that are containers of multiple projects
CONTAINER_ROOTS = [
    Path.home() / "Research" / "kalbe",
    Path.home() / "Research" / "llmnetops",
    Path.home() / "Research" / "learn-research",
]

EXCLUDE_DIRS = {
    ".git", ".venv", "venv", "node_modules", ".cache", "__pycache__", 
    ".diff_backups", ".antigravitycli", ".commandcode", "Credentials",
    "archive", "archive-221026", "archive-old", "archive", "dist", "build"
}


def run_git(cwd: Path, args: List[str]) -> str:
    try:
        res = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
        )
        return res.stdout.strip() if res.returncode == 0 else ""
    except Exception:
        return ""


def get_git_info(p: Path) -> Tuple[Optional[str], int, Optional[str], Optional[str]]:
    if not (p / ".git").exists():
        return None, 0, None, None
    branch = run_git(p, ["rev-parse", "--abbrev-ref", "HEAD"]) or "detached"
    status = run_git(p, ["status", "--porcelain"])
    dirty = len(status.splitlines()) if status else 0
    last_log = run_git(p, ["log", "-1", "--format=%cd | %s", "--date=short"])
    if last_log and " | " in last_log:
        date, msg = last_log.split(" | ", 1)
        return branch, dirty, msg, date
    return branch, dirty, None, None


def analyze_directory(p: Path) -> ProjectMetadata:
    name = p.name
    path_str = str(p)
    reasons: List[str] = []

    # Check git
    branch, dirty, last_commit, last_commit_date = get_git_info(p)

    # Detect files & signatures
    has_latex = False
    has_bibtex = False
    has_checkpoints = False
    has_datasets = False
    ml_frameworks = set()
    key_metrics = set()
    is_tooling_artifact = False
    tooling_reasons = []

    # Scan shallow tree (depth <= 3) to be fast
    for root, dirs, files in os.walk(p):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".")]
        rel_depth = len(Path(root).relative_to(p).parts)
        if rel_depth > 3:
            continue

        for f in files:
            low = f.lower()
            if low.endswith(".tex"):
                has_latex = True
            elif low.endswith(".bib"):
                has_bibtex = True
            elif low.endswith((".pth", ".pt", ".ckpt", ".onnx", ".safetensors", ".bin")):
                has_checkpoints = True
            elif low.endswith((".h5", ".csv", ".parquet", ".arrow", ".npy", ".npz", ".nii", ".nii.gz")):
                has_datasets = True
            elif low in ("dockerfile", "docker-compose.yml", "docker-compose.yaml"):
                is_tooling_artifact = True
                tooling_reasons.append("Docker infrastructure")
            elif low.startswith("next.config") or low.startswith("vite.config") or low == "webpack.config.js":
                is_tooling_artifact = True
                tooling_reasons.append("Web application frontend")

    # Inspect README / pyproject / requirements for text signatures
    readme_text = ""
    for rname in ["README.md", "README.rst", "README.txt", "README"]:
        rpath = p / rname
        if rpath.is_file():
            try:
                readme_text = rpath.read_text(encoding="utf-8", errors="ignore")[:6000]
                break
            except Exception:
                pass

    req_text = ""
    for req_name in ["requirements.txt", "pyproject.toml", "environment.yml"]:
        req_path = p / req_name
        if req_path.is_file():
            try:
                req_text += "\n" + req_path.read_text(encoding="utf-8", errors="ignore")[:3000]
            except Exception:
                pass

    combined_text = (readme_text + "\n" + req_text).lower()

    # ML Frameworks detection
    for fw in ["torch", "pytorch", "jax", "tensorflow", "scikit-learn", "sklearn", "xgboost", "lightgbm", "transformers", "pysr", "deepspeed"]:
        if fw in combined_text:
            ml_frameworks.add(fw)

    # Scientific / Research metrics & keywords
    scientific_keywords = [
        "hypothesis", "ablation", "benchmark", "surrogate", "dem", "loss", "accuracy",
        "auc-roc", "f1-score", "dice", "iou", "rmse", "mae", "cross-entropy",
        "peer-reviewed", "arxiv", "preprint", "methodology", "dataset", "ground truth"
    ]
    for kw in scientific_keywords:
        if re.search(r"\b" + re.escape(kw) + r"\b", combined_text):
            key_metrics.add(kw)

    # Tooling keywords
    tooling_keywords = [
        "cli", "dashboard", "ui portal", "agent runtime", "mcp server",
        "fastapi", "express", "react", "vue", "router", "webhook", "monitoring"
    ]
    found_tooling = [kw for kw in tooling_keywords if re.search(r"\b" + re.escape(kw) + r"\b", combined_text)]

    # Scoring and Classification
    research_score = 0.0
    tooling_score = 0.0

    if has_latex:
        research_score += 0.35
        reasons.append("Contains LaTeX manuscripts (.tex)")
    if has_bibtex:
        research_score += 0.25
        reasons.append("Contains academic bibliography (.bib)")
    if has_checkpoints:
        research_score += 0.20
        reasons.append("Contains deep learning checkpoints/weights")
    if has_datasets:
        research_score += 0.15
        reasons.append("Houses research datasets/arrays")
    if len(ml_frameworks) > 0:
        research_score += 0.15
        reasons.append(f"Employs ML frameworks: {', '.join(sorted(ml_frameworks))}")
    if len(key_metrics) >= 3:
        research_score += 0.25
        reasons.append(f"Explicit scientific terms: {', '.join(list(key_metrics)[:4])}")

    if is_tooling_artifact:
        tooling_score += 0.30
        reasons.extend(tooling_reasons[:2])
    if len(found_tooling) >= 2:
        tooling_score += 0.35
        reasons.append(f"Tooling keywords detected: {', '.join(found_tooling[:3])}")
    if "projects/tools" in path_str.lower() or "llmnetops" in path_str.lower():
        tooling_score += 0.30
        reasons.append("Located in tools/operations namespace")

    # Specific directory context overrides
    if "archive" in path_str.lower():
        category = "ARCHIVE_EXPLORATORY"
        is_research = research_score >= 0.4
        confidence = 0.85
        reasons.append("Archived/legacy exploration")
    elif "research-template" in name or "kalbe-factory" in name or "kalbe-ai-skills" in name:
        category = "INFRASTRUCTURE_DEV"
        is_research = False
        confidence = 0.90
        reasons.append("Project template, factory orchestrator, or agent skill scaffolding")
    elif research_score >= 0.45 and research_score >= tooling_score:
        if has_latex or has_bibtex or "academic" in path_str.lower() or "skripsi" in name.lower() or "study" in name.lower():
            category = "ACADEMIC_RESEARCH"
            is_research = True
            confidence = min(0.98, 0.65 + research_score * 0.3)
        else:
            category = "APPLIED_ML_TRIAL"
            is_research = True
            confidence = min(0.95, 0.60 + research_score * 0.3)
    elif tooling_score > research_score:
        category = "ENGINEERING_TOOLING"
        is_research = False
        confidence = min(0.95, 0.60 + tooling_score * 0.3)
    elif "documents/academic" in path_str.lower():
        category = "ACADEMIC_RESEARCH"
        is_research = True
        confidence = 0.90
        reasons.append("Housed within Documents/Academic")
    else:
        # Default fallback
        if "research" in path_str.lower():
            category = "APPLIED_ML_TRIAL"
            is_research = True
            confidence = 0.65
        else:
            category = "ENGINEERING_TOOLING"
            is_research = False
            confidence = 0.65

    # Extract Summary & Findings from README
    summary_lines = []
    if readme_text:
        for line in readme_text.splitlines():
            sline = line.strip()
            if sline and not sline.startswith("#") and not sline.startswith("[!") and len(sline) > 20:
                summary_lines.append(sline)
                if len(summary_lines) >= 3:
                    break
    summary = " ".join(summary_lines) if summary_lines else "No formal README summary found."

    findings = ""
    if last_commit:
        findings = f"Latest Activity: {last_commit} ({last_commit_date or 'Recent'})"
    else:
        findings = "Local directory without commit history."

    next_steps = f"Branch '{branch or 'main'}' with {dirty} uncommitted changes." if branch else "Static codebase."

    return ProjectMetadata(
        name=name,
        path=path_str,
        category=category,
        is_research=is_research,
        confidence=round(confidence, 2),
        reasoning=reasons,
        git_branch=branch,
        git_uncommitted_changes=dirty,
        git_last_commit=last_commit,
        git_last_commit_date=last_commit_date,
        has_latex=has_latex,
        has_bibtex=has_bibtex,
        has_checkpoints=has_checkpoints,
        has_datasets=has_datasets,
        ml_frameworks=sorted(list(ml_frameworks)),
        key_metrics=sorted(list(key_metrics)),
        summary=summary,
        findings=findings,
        next_steps=next_steps,
    )


def collect_projects() -> List[ProjectMetadata]:
    projects: List[ProjectMetadata] = []
    seen_paths = set()

    # Step 1: Scan individual top-level dirs in SCAN_ROOTS
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for item in sorted(root.iterdir()):
            if not item.is_dir() or item.name in EXCLUDE_DIRS or item.name.startswith("."):
                continue
            # If item is in CONTAINER_ROOTS, recurse into its subdirectories
            if item in CONTAINER_ROOTS:
                continue
            canonical = str(item.resolve())
            if canonical not in seen_paths:
                seen_paths.add(canonical)
                projects.append(analyze_directory(item))

    # Step 2: Scan CONTAINER_ROOTS explicitly
    for container in CONTAINER_ROOTS:
        if not container.exists():
            continue
        for item in sorted(container.iterdir()):
            if not item.is_dir() or item.name in EXCLUDE_DIRS or item.name.startswith("."):
                continue
            canonical = str(item.resolve())
            if canonical not in seen_paths:
                seen_paths.add(canonical)
                projects.append(analyze_directory(item))

    return projects


def generate_obsidian_report(projects: List[ProjectMetadata]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    research_projects = [p for p in projects if p.is_research]
    non_research_projects = [p for p in projects if not p.is_research]

    # Category counts
    counts: Dict[str, int] = {}
    for p in projects:
        counts[p.category] = counts.get(p.category, 0) + 1

    lines = [
        "---",
        "title: Research Project Classification & Synthesis",
        f"date: {datetime.now().strftime('%Y-%m-%d')}",
        "tags: [research, catalog, synthesis, workspace, audit]",
        "generated_by: hermes/research-classifier",
        "---",
        "",
        "# 🔬 Research vs Non-Research Project Classification & Synthesis",
        "",
        f"> **Generated at**: `{now}` | **Total Repositories Scanned**: `{len(projects)}`",
        f"> **Research Projects**: `{len(research_projects)}` | **Engineering/Tooling/Scaffolding**: `{len(non_research_projects)}`",
        "",
        "## 📊 Portfolio Distribution Overview",
        "",
        "| Category | Projects | Description |",
        "| :--- | :---: | :--- |",
        f"| **Academic Research** | `{counts.get('ACADEMIC_RESEARCH', 0)}` | Peer-reviewed manuscripts, novel scientific formulations, papers, and thesis |",
        f"| **Applied ML Trials** | `{counts.get('APPLIED_ML_TRIAL', 0)}` | Empirical surrogate models, ML benchmarks, and exploratory simulations |",
        f"| **Engineering & Tooling** | `{counts.get('ENGINEERING_TOOLING', 0)}` | CLI tools, network emulation testbeds, MCP servers, and UI dashboards |",
        f"| **Infrastructure & Scaffolding** | `{counts.get('INFRASTRUCTURE_DEV', 0)}` | Factory frameworks, project templates, and agent orchestration skills |",
        f"| **Archive & Exploratory** | `{counts.get('ARCHIVE_EXPLORATORY', 0)}` | Historical prototypes and reference implementations |",
        "",
        "---",
        "",
        "## 🧪 Active & High-Priority Research Portfolio",
        "",
        "Detailed findings, hypotheses, and status synthesis for verified scientific and applied ML initiatives:",
        "",
    ]

    # Group research projects by category
    for cat in ["ACADEMIC_RESEARCH", "APPLIED_ML_TRIAL"]:
        cat_items = [p for p in research_projects if p.category == cat]
        if not cat_items:
            continue

        cat_title = "🎓 Academic Research (Publications & Manuscripts)" if cat == "ACADEMIC_RESEARCH" else "⚙️ Applied ML Trials & Scientific Surrogates"
        lines.append(f"### {cat_title}")
        lines.append("")

        for p in cat_items:
            dirty_badge = f"⚠️ `{p.git_uncommitted_changes} uncommitted`" if p.git_uncommitted_changes > 0 else "✅ clean"
            fw_badge = f"`{'`, `'.join(p.ml_frameworks)}`" if p.ml_frameworks else "_none_"
            artifacts = []
            if p.has_latex: artifacts.append("LaTeX 📄")
            if p.has_bibtex: artifacts.append("BibTeX 📚")
            if p.has_checkpoints: artifacts.append("Weights 🧠")
            if p.has_datasets: artifacts.append("Data 📊")
            art_str = ", ".join(artifacts) if artifacts else "_standard code_"

            lines.extend([
                f"#### `{p.name}` ({p.confidence * 100:.0f}% confidence)",
                f"- **Path**: `{p.path}`",
                f"- **Artifacts**: {art_str}",
                f"- **ML Stack**: {fw_badge}",
                f"- **Git Status**: branch `{p.git_branch or 'N/A'}` ({dirty_badge})",
                f"- **Activity / Finding**: {p.findings}",
                f"- **Classification Evidence**: {'; '.join(p.reasoning[:3])}",
                f"- **Objective / Summary**: {p.summary[:300]}...",
                "",
            ])

    lines.extend([
        "---",
        "",
        "## 🛠️ Non-Research Projects (Tooling, Infrastructure & Network Operations)",
        "",
        "The following projects provide engineering automation, developer tooling, or network simulation and are **excluded** from research publication pipelines:",
        "",
        "| Project Name | Path | Category | Confidence | Key Evidence |",
        "| :--- | :--- | :--- | :---: | :--- |",
    ])

    for p in non_research_projects:
        short_path = p.path.replace(str(Path.home()), "~")
        evidence = "; ".join(p.reasoning[:2]) if p.reasoning else "Tooling signature"
        lines.append(f"| **`{p.name}`** | `{short_path}` | `{p.category}` | `{p.confidence * 100:.0f}%` | {evidence} |")

    lines.extend([
        "",
        "---",
        "",
        "## 🧭 Synthesis & Actionable Recommendations for Research Agents",
        "",
        "1. **Prioritize Peer-Reviewed Deliverables**:",
        "   - `crd-dem-surrogate`: Active DEM bin-mixing surrogate model under Kalbe. Ensure verification runs adhere to factory protocols.",
        "   - `histodae` & `BoneTumor`: Retain clinical rigor, checkpoint versioning, and evaluation metrics.",
        "   - `indonesian-pii-benchmark`: Focus on benchmark evaluation tables and dataset privacy annotations.",
        "2. **Maintain Strict Separation**:",
        "   - Projects such as `clab-mt`, `NetOpsUI`, `mcp-llmnetops`, and `stock-screener` are engineering tools; keep their issue trackers and PR workflows separate from scientific ERT reporting.",
        "3. **Uncommitted Workspace Hygiene**:",
        "   - All research repositories flagged with uncommitted changes should undergo pre-EOD patch backup via `git-guard`.",
        "",
    ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Research Project Classifier & Findings Synthesizer")
    parser.add_argument("--json", action="store_true", help="Output raw JSON to stdout")
    parser.add_argument("--vault", type=str, default=str(Path.home() / "vaults" / "research-vault"), help="Obsidian vault path")
    args = parser.parse_args()

    projects = collect_projects()

    # Save JSON cache in ~/.hermes/data/
    data_dir = Path.home() / ".hermes" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    json_path = data_dir / "project_classification.json"
    json_path.write_text(json.dumps([asdict(p) for p in projects], indent=2), encoding="utf-8")

    # Generate Obsidian Report
    vault_dir = Path(args.vault)
    if vault_dir.exists():
        report_md = generate_obsidian_report(projects)
        target_file = vault_dir / "02_Projects" / "Research Project Classification & Synthesis.md"
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text(report_md, encoding="utf-8")
        print(f"✅ Published Obsidian Synthesis Report to: {target_file}")

    if args.json:
        print(json.dumps([asdict(p) for p in projects], indent=2))
    else:
        research_count = sum(1 for p in projects if p.is_research)
        non_research_count = len(projects) - research_count
        print(f"📊 Classification Complete: {len(projects)} projects analyzed.")
        print(f"   🔬 Research Projects: {research_count}")
        print(f"   🛠️ Non-Research Projects: {non_research_count}")
        print(f"   💾 Cache stored at: {json_path}")


if __name__ == "__main__":
    main()
