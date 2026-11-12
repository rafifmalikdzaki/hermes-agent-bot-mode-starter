---
name: libreoffice-tools
description: Headless LibreOffice and Pandoc document automation — convert between DOCX, PPTX, XLSX, ODT, PDF, HTML, and Markdown, and inspect document structure.
---

# LibreOffice & Document Automation Skill

Use this skill when you need to convert, inspect, or generate Microsoft Office (`.docx`, `.pptx`, `.xlsx`), OpenDocument (`.odt`, `.odp`, `.ods`), and PDF files using the workstation's local LibreOffice 26.8 headless engine and Pandoc.

## Capabilities

1. **Format Conversion (`doc-convert`)**:
   - Markdown $\to$ `.docx` (via Pandoc) or `.pdf` (via LibreOffice Writer).
   - `.docx` / `.odt` $\to$ `.pdf`, `.html`, or plain `.txt`.
   - `.pptx` / `.odp` $\to$ `.pdf` or slide HTML.
   - `.xlsx` / `.ods` $\to$ `.pdf` or `.csv`.
2. **Document Inspection (`doc-inspect`)**:
   - Extracts document metadata, file size, and previews embedded plain text without opening a graphical window.
3. **Report Generation**:
   - Compiles research reports or ERT summaries into publication-ready PDF or Word documents for human review.

## CLI Usage

```bash
# Convert a Markdown note to a formatted Word document:
doc-convert report.md --to docx

# Convert a Markdown note or Word document directly to PDF:
doc-convert report.md --to pdf
doc-convert contract.docx --to pdf

# Convert an Excel spreadsheet to CSV:
doc-convert data.xlsx --to csv

# Inspect and read text from an office document:
doc-inspect presentation.pptx
doc-inspect trial_results.xlsx
```

## Python Integration

```python
from libreoffice_tools import convert_document, inspect_document
from pathlib import Path

# Convert document
pdf_path = convert_document(Path("report.docx"), target_format="pdf")

# Inspect document
info = inspect_document(Path("contract.docx"))
print(info["text_preview"])
```
