---
name: open-deep-research
description: Conducts multi-step deep research and literature synthesis across ArXiv, live web, and local Zotero libraries using open-source SOTA retrieval and synthesis pipelines.
---

# Open Deep Research Skill

Use this skill when you need to perform an in-depth, multi-source literature review, explore state-of-the-art benchmarks, or synthesize evidence across academic preprints and technical implementations.

## Capabilities

1. **Multi-Query Decomposition**: Automatically breaks an open-ended research question into targeted sub-queries.
2. **Multi-Source Retrieval**:
   - **ArXiv API**: Retrieves peer-reviewed papers, preprints, authors, publication dates, and abstracts.
   - **DuckDuckGo Web**: Free, zero-token web search for real-world disclosures and documentation.
   - **Local Zotero Database**: Matches local citation keys in `~/Zotero/zotero.sqlite`.
3. **Synthesis & Obsidian Integration**:
   - Publishes comprehensive, publication-grade markdown reports directly to:
     `~/vaults/research-vault/03_Literature/Deep Research/Deep_Research_<topic_slug>.md`

## CLI Usage

```bash
# Run deep research on any topic:
deep-research "Kolmogorov-Arnold Networks physics surrogate"

# Adjust maximum evidence sources:
deep-research "Graph Neural Networks powder mixing" --max-results 12

# Output raw JSON for programmatic pipelines:
deep-research "DeepSeek MoE architecture" --json
```

## Python Integration

```python
from open_deep_research import OpenDeepResearcher

researcher = OpenDeepResearcher(topic="Surrogate modeling for fluid dynamics", max_results=8)
result = researcher.run_research()
print(result["report_path"])
```
