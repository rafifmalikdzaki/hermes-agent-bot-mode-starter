#!/usr/bin/env python3
"""
LibreOffice & Document Automation Tools for Hermes Agents.

Provides headless document processing, format conversions (DOCX, PPTX, XLSX, ODT, PDF, HTML, TXT),
inspection of office documents, and publication of Markdown reports to professional PDF/DOCX.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional


LIBREOFFICE_BIN = shutil.which("libreoffice") or shutil.which("soffice") or "/usr/bin/libreoffice"
PANDOC_BIN = shutil.which("pandoc") or "/usr/bin/pandoc"


def run_cmd(cmd: List[str], timeout: int = 45) -> subprocess.CompletedProcess:
    try:
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=True
        )
        return res
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {' '.join(cmd)}\nStderr: {e.stderr}", file=sys.stderr)
        raise
    except subprocess.TimeoutExpired:
        print(f"Command timed out after {timeout}s: {' '.join(cmd)}", file=sys.stderr)
        raise


def convert_document(input_path: Path, target_format: str, out_dir: Optional[Path] = None) -> Path:
    """Converts any document using LibreOffice headless engine."""
    input_path = input_path.resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    out_dir = (out_dir or input_path.parent).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Special case: markdown to docx/pdf via pandoc if available
    ext = input_path.suffix.lower()
    if ext in (".md", ".markdown"):
        if target_format.lower() == "docx" and os.path.exists(PANDOC_BIN):
            out_file = out_dir / f"{input_path.stem}.docx"
            run_cmd([PANDOC_BIN, str(input_path), "-o", str(out_file)])
            return out_file
        elif target_format.lower() == "pdf" and os.path.exists(PANDOC_BIN):
            # Convert md -> docx -> pdf via libreoffice
            temp_docx = out_dir / f"{input_path.stem}_temp.docx"
            run_cmd([PANDOC_BIN, str(input_path), "-o", str(temp_docx)])
            run_cmd([LIBREOFFICE_BIN, "--headless", "--convert-to", "pdf", str(temp_docx), "--outdir", str(out_dir)])
            if temp_docx.exists():
                temp_docx.unlink()
            return out_dir / f"{temp_docx.stem}.pdf"

    # Native LibreOffice conversion
    cmd = [
        LIBREOFFICE_BIN,
        "--headless",
        "--convert-to",
        target_format,
        str(input_path),
        "--outdir",
        str(out_dir)
    ]
    run_cmd(cmd)

    # Output file name determination
    target_ext = f".{target_format.split(':')[0].lower()}"
    out_file = out_dir / f"{input_path.stem}{target_ext}"
    if not out_file.exists():
        # Search for any recently created file with target extension
        candidates = list(out_dir.glob(f"{input_path.stem}*"))
        if candidates:
            out_file = candidates[0]

    return out_file


def inspect_document(input_path: Path) -> Dict[str, str]:
    """Inspects an office document and extracts metadata and text excerpt."""
    input_path = input_path.resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"File not found: {input_path}")

    size_kb = input_path.stat().st_size / 1024
    ext = input_path.suffix.lower()

    # Extract text preview using pdftotext or libreoffice convert-to txt
    text_preview = ""
    try:
        temp_dir = Path("/tmp/doc_inspect")
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        if ext == ".pdf" and shutil.which("pdftotext"):
            res = subprocess.run(["pdftotext", str(input_path), "-"], stdout=subprocess.PIPE, text=True, timeout=10)
            text_preview = res.stdout[:1500]
        else:
            txt_file = convert_document(input_path, "txt:Text", temp_dir)
            if txt_file.exists():
                text_preview = txt_file.read_text(encoding="utf-8", errors="ignore")[:1500]
                txt_file.unlink()
    except Exception as e:
        text_preview = f"(Could not extract text: {e})"

    return {
        "file_name": input_path.name,
        "path": str(input_path),
        "extension": ext,
        "size_kb": f"{size_kb:.1f} KB",
        "text_preview": text_preview.strip()
    }


def main():
    # If invoked directly via symlink
    prog = Path(sys.argv[0]).stem
    if prog == "doc-convert" and len(sys.argv) > 1 and sys.argv[1] not in ("-h", "--help", "convert", "inspect"):
        sys.argv.insert(1, "convert")
    elif prog == "doc-inspect" and len(sys.argv) > 1 and sys.argv[1] not in ("-h", "--help", "convert", "inspect"):
        sys.argv.insert(1, "inspect")

    parser = argparse.ArgumentParser(description="LibreOffice & Document Automation CLI for Hermes")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Convert
    convert_parser = subparsers.add_parser("convert", help="Convert document format")
    convert_parser.add_argument("input_file", type=str, help="Path to input document")
    convert_parser.add_argument("--to", type=str, required=True, help="Target format (pdf, docx, html, txt, odt, pptx, xlsx)")
    convert_parser.add_argument("--outdir", type=str, default=None, help="Output directory")

    # Inspect
    inspect_parser = subparsers.add_parser("inspect", help="Inspect and extract text from an office document")
    inspect_parser.add_argument("input_file", type=str, help="Path to document")

    args = parser.parse_args()

    if args.command == "convert":
        in_p = Path(args.input_file)
        out_d = Path(args.outdir) if args.outdir else None
        print(f"🔄 Converting {in_p.name} to {args.to.upper()}...")
        out_p = convert_document(in_p, args.to, out_d)
        print(f"✅ Generated: {out_p}")

    elif args.command == "inspect":
        in_p = Path(args.input_file)
        info = inspect_document(in_p)
        print(f"📄 Document: {info['file_name']} ({info['size_kb']})")
        print(f"📂 Path: {info['path']}")
        print("\n--- Text Preview ---")
        print(info["text_preview"][:800] + ("..." if len(info["text_preview"]) > 800 else ""))


if __name__ == "__main__":
    main()
