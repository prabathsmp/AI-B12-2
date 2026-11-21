"""One-page PDF report (answer + charts)."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fpdf import FPDF

_REPL = {"₹": "Rs ", "–": "-", "—": "-", "’": "'", "‘": "'", "“": '"', "”": '"', "•": "-", "…": "...", "→": "->", "×": "x"}


def _latin(text: str) -> str:
    for a, b in _REPL.items():
        text = text.replace(a, b)
    return text.replace("**", "").encode("latin-1", "replace").decode("latin-1")


def build_pdf(question: str, sections: dict[str, str], charts: list[Path]) -> bytes:
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()

    pdf.set_fill_color(15, 23, 42)
    pdf.rect(0, 0, 210, 26, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 17)
    pdf.set_xy(10, 7)
    pdf.cell(0, 8, "DataPilot - Analysis Report")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_xy(10, 15)
    pdf.cell(0, 6, datetime.now().strftime("Generated %d %b %Y, %H:%M"))

    pdf.set_text_color(20, 20, 20)
    pdf.set_xy(10, 32)
    pdf.set_font("Helvetica", "B", 11)
    pdf.multi_cell(0, 6, _latin("Question: " + question))
    pdf.ln(2)

    for key in ("ANSWER", "WHERE IT CAME FROM", "SUGGESTED NEXT QUESTION"):
        if sections.get(key):
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(13, 148, 136)
            pdf.cell(0, 6, key, new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(30, 30, 30)
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 5.2, _latin(sections[key]))
            pdf.ln(1.5)

    # charts: two per row
    imgs = charts[:4]
    if imgs:
        w = 93
        h = w * 5.5 / 10
        y = pdf.get_y() + 2
        if y + h > 285:
            pdf.add_page()
            y = 12
        for i, img in enumerate(imgs):
            col = i % 2
            if i and col == 0:
                y += h + 3
                if y + h > 285:
                    pdf.add_page()
                    y = 12
            pdf.image(str(img), x=10 + col * (w + 4), y=y, w=w)
    return bytes(pdf.output())
