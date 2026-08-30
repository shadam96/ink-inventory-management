"""Font registration and bidirectional text shaping for the generated PDFs.

Two things have to be arranged before ReportLab can draw Hebrew at all.

First, a font: ReportLab's built-in faces are Latin-1 only, so every Hebrew
character in a delivery note or pick note rendered as a fallback box. We
register a vendored DejaVu Sans instead - one face that covers Hebrew, Latin,
Greek and Turkish, so a customer or item name comes out readable in any of the
four languages the app supports.

Second, ordering: ReportLab only reorders right-to-left runs when the
unmaintained, C-compiled ``pyfribidi2`` package is importable, which it isn't
here. So we run the Unicode bidi algorithm ourselves via ``python-bidi`` and
hand ReportLab text that is already in visual order.
"""
from pathlib import Path
from typing import List, Optional
from xml.sax.saxutils import escape

from bidi import get_display
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily, stringWidth
from reportlab.pdfbase.ttfonts import TTFont

FONT_NAME = "DejaVuSans"
FONT_NAME_BOLD = "DejaVuSans-Bold"

_FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
_fonts_registered = False


def register_pdf_fonts() -> None:
    """Register the vendored DejaVu faces with ReportLab.

    Idempotent, and called from each PDF generator rather than at import time
    so that merely importing this module doesn't parse 1.4 MB of TTF.
    """
    global _fonts_registered
    if _fonts_registered:
        return

    pdfmetrics.registerFont(TTFont(FONT_NAME, str(_FONT_DIR / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont(FONT_NAME_BOLD, str(_FONT_DIR / "DejaVuSans-Bold.ttf")))
    # Without a registered family, <b> inside a Paragraph silently resolves to
    # Helvetica-Bold - which has no Hebrew glyphs, reintroducing the boxes.
    registerFontFamily(
        FONT_NAME,
        normal=FONT_NAME,
        bold=FONT_NAME_BOLD,
        italic=FONT_NAME,
        boldItalic=FONT_NAME_BOLD,
    )
    _fonts_registered = True


def shape(text: Optional[object]) -> str:
    """Reorder a single line of text into the visual order ReportLab draws.

    The base direction is auto-detected from the first strong character, per
    the Unicode bidi algorithm, so a Hebrew label and an ASCII reference
    number each come out the right way round. Latin-only text is unchanged.
    """
    value = "" if text is None else str(text)
    return get_display(value) if value else value


def shape_paragraph(
    text: Optional[object],
    font_name: str,
    font_size: float,
    max_width: float,
) -> str:
    """Shape free-form text for a ``Paragraph``, wrapping before reordering.

    Reordering is per visual line, so the line breaks have to be decided
    first: handing ReportLab one long reordered string and letting it wrap
    would slice the text at points that no longer correspond to word
    boundaries. Returns escaped markup with explicit ``<br/>`` breaks.
    """
    lines: List[str] = []
    for logical_line in ("" if text is None else str(text)).split("\n"):
        words = logical_line.split()
        if not words:
            lines.append("")
            continue

        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if stringWidth(candidate, font_name, font_size) <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)

    return "<br/>".join(escape(shape(line)) for line in lines)
