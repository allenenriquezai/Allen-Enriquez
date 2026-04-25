"""
to_markdown.py — Convert HTML or PDF to Markdown for token-efficient Claude context.

Token savings:
  HTML → Markdown: ~90% fewer tokens
  PDF  → Markdown: ~65-70% fewer tokens

Usage:
  python3 tools/shared/to_markdown.py file.pdf
  python3 tools/shared/to_markdown.py file.html
  cat file.html | python3 tools/shared/to_markdown.py --stdin-html
  python3 tools/shared/to_markdown.py file.pdf --output summary.md

Dependencies:
  pip install markdownify pymupdf4llm
"""

import argparse
import sys
from pathlib import Path


def html_to_md(html: str) -> str:
    from markdownify import markdownify
    return markdownify(html, heading_style="ATX", strip=["script", "style"])


def pdf_to_md(path: Path) -> str:
    import pymupdf4llm
    return pymupdf4llm.to_markdown(str(path))


def main():
    parser = argparse.ArgumentParser(description="Convert HTML/PDF to Markdown")
    parser.add_argument("input", nargs="?", help="Input file (.html or .pdf)")
    parser.add_argument("--stdin-html", action="store_true", help="Read HTML from stdin")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    args = parser.parse_args()

    if args.stdin_html:
        result = html_to_md(sys.stdin.read())
    elif args.input:
        path = Path(args.input)
        if not path.exists():
            sys.exit(f"File not found: {path}")
        if path.suffix.lower() == ".pdf":
            result = pdf_to_md(path)
        elif path.suffix.lower() in (".html", ".htm"):
            result = html_to_md(path.read_text(encoding="utf-8"))
        else:
            sys.exit(f"Unsupported file type: {path.suffix}. Use .pdf or .html")
    else:
        parser.print_help()
        sys.exit(1)

    if args.output:
        Path(args.output).write_text(result, encoding="utf-8")
        original_size = len(Path(args.input).read_bytes()) if args.input else 0
        md_size = len(result.encode())
        if original_size:
            saving = round((1 - md_size / original_size) * 100)
            print(f"Saved to {args.output} ({saving}% smaller)", file=sys.stderr)
    else:
        print(result)


if __name__ == "__main__":
    main()
