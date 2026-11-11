"""Build the two-page note and one-page architecture from Markdown sources.

Documentation-only dependencies: reportlab4.4.9, pypdf6.21.4.
Run from the repository root. No application code or credentials imported.
"""
from html import escape
from pathlib import Path
import re

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf"


def inline(text):
    text = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", text)
    text = escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    return text.replace("`", "")


def render(source, target, expected_pages, font=10.4, leading=13.4):
    styles = {
        "body": ParagraphStyle("body", fontName="Helvetica", fontSize=font, leading=leading,
                               textColor=colors.HexColor("#253143"), spaceAfter=7, alignment=TA_LEFT),
        "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=20, leading=24,
                                textColor=colors.HexColor("#162238"), spaceAfter=7),
        "heading": ParagraphStyle("heading", fontName="Helvetica-Bold", fontSize=11.3, leading=14,
                                  textColor=colors.HexColor("#162238"), spaceBefore=7, spaceAfter=5,
                                  keepWithNext=True),
    }
    story = []
    for block in source.read_text(encoding="utf-8").strip().split("\n\n"):
        if block.strip() == "<!-- PAGEBREAK -->":
            story.append(PageBreak())
            continue
        style = "title" if block.startswith("# ") else "heading" if block.startswith("## ") else "body"
        text = re.sub(r"^#{1,2} ", "", block.strip()).replace("\n", " ")
        story.append(Paragraph(inline(text), styles[style]))
    def footer(canvas, doc):
        canvas.setStrokeColor(colors.HexColor("#D6DCE5"))
        canvas.line(18*mm, 16*mm, A4[0]-18*mm, 16*mm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#647084"))
        canvas.drawString(18*mm, 11*mm, "SOUP / FULL-STACK TAKE-HOME / 11 NOV 2026")
        canvas.drawRightString(A4[0]-18*mm, 11*mm, f"{doc.page} / {expected_pages}")
    document = SimpleDocTemplate(str(target), pagesize=A4, leftMargin=18*mm, rightMargin=18*mm,
                                 topMargin=17*mm, bottomMargin=22*mm,
                                 title=source.stem.replace("_", " "), author="Madi",
                                 pageCompression=1)
    document.build(story, onFirstPage=footer, onLaterPages=footer)
    pages = len(PdfReader(target).pages)
    print(f"{target.relative_to(ROOT)}: pages={pages}, words={len(source.read_text(encoding='utf-8').split())}")
    if pages != expected_pages:
        raise SystemExit(f"Expected exactly{expected_pages} pages; got{pages}. Inspect and correct the source/layout.")


if __name__ == "__main__":
    OUTPUT.mkdir(parents=True, exist_ok=True)
    render(ROOT / "docs" / "SUBMISSION_NOTE.md", OUTPUT / "Soup-Submission-Note.pdf", 2)
    render(ROOT / "docs" / "DESIGN.md", OUTPUT / "Soup-Architecture.pdf", 1, font=10.5, leading=13.5)
