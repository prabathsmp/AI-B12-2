"""Markdown -> styled PDF using xhtml2pdf (pure Python, Docker friendly)."""
from __future__ import annotations

import io
import re

import markdown
from xhtml2pdf import pisa

PDF_CSS = """
@page { size: A4; margin: 1.6cm 1.5cm; }
body { font-family: Helvetica; font-size: 10pt; color: #1f2333; line-height: 1.45; }
h1 { font-size: 20pt; color: #4b2bd6; border-bottom: 2px solid #7c5cff; padding-bottom: 6px; }
h2 { font-size: 13.5pt; color: #ffffff; background-color: #5b3df0; padding: 5px 8px; margin-top: 16px; }
h3 { font-size: 11.5pt; color: #4b2bd6; }
table { width: 100%; border: 1px solid #d6d2f5; margin: 6px 0; }
th { background-color: #ece8ff; color: #2b1d80; padding: 5px; font-weight: bold; text-align: left; }
td { padding: 5px; border-top: 1px solid #e4e1f7; vertical-align: top; }
blockquote { background-color: #f4f1ff; border-left: 4px solid #7c5cff; padding: 6px 10px; color: #2b1d80; }
a { color: #3b6cf6; text-decoration: none; }
code { font-family: Courier; font-size: 9pt; }
li { margin-bottom: 2px; }
"""


def _autolink(md_text: str) -> str:
    # Turn bare URLs into links so sources are clickable in the PDF.
    return re.sub(r"(?<![\(\[<\"])(https?://[^\s\)\]>|]+)", r"<\1>", md_text)


def markdown_to_pdf(md_text: str) -> bytes:
    # Base PDF fonts lack some glyphs (e.g. the rupee sign); swap for safe text.
    md_text = md_text.replace("₹", "Rs ").replace("€", "EUR ").replace("—", "-").replace("–", "-")
    html_body = markdown.markdown(_autolink(md_text), extensions=["tables", "sane_lists", "nl2br"])
    html = f"<html><head><meta charset='utf-8'><style>{PDF_CSS}</style></head><body>{html_body}</body></html>"
    buf = io.BytesIO()
    status = pisa.CreatePDF(html, dest=buf, encoding="utf-8")
    if status.err:
        raise RuntimeError("PDF generation failed")
    return buf.getvalue()
