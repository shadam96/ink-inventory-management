"""The Lino Print letterhead drawn on every page of the generated PDFs.

Follows the company's Word template ("Lino Print Template"): the logo and
contact block across the top of the page and the page number centred at the
bottom. The header is the template's own image, extracted unchanged, so the
logo and its typeface match the printed stationery exactly - DejaVu, the only
face registered for Hebrew, couldn't reproduce them as live text. A change to
the company's contact details therefore needs a new image from the template.
"""
from pathlib import Path

from reportlab.lib.units import mm

from app.services.pdf_text import FONT_NAME

_HEADER_IMAGE = Path(__file__).resolve().parent.parent / "assets" / "letterhead_header.jpg"
# Pixel size of the image, so it is drawn at its own aspect ratio.
_HEADER_ASPECT = 287 / 2202

_HEADER_TOP_OFFSET = 12 * mm
_HEADER_GAP = 8 * mm
_PAGE_NUMBER_BASELINE = 12 * mm

# Header height at the 170 mm content width both documents use (A4 with 20 mm
# side margins). Pass this as the document's topMargin so the body starts
# below the header instead of underneath it.
LETTERHEAD_TOP_MARGIN = _HEADER_TOP_OFFSET + 170 * mm * _HEADER_ASPECT + _HEADER_GAP


def draw_letterhead(canvas, doc) -> None:
    """Page callback for ``doc.build(onFirstPage=..., onLaterPages=...)``.

    The header spans the content width so its edges line up with the tables
    below it.
    """
    page_width, page_height = doc.pagesize
    header_height = doc.width * _HEADER_ASPECT

    canvas.saveState()
    canvas.drawImage(
        str(_HEADER_IMAGE),
        doc.leftMargin,
        page_height - _HEADER_TOP_OFFSET - header_height,
        width=doc.width,
        height=header_height,
    )
    # The template's Hebrew page-number field displays as "1#"; drawn
    # directly in that visual order, as there is no Hebrew to reorder.
    canvas.setFont(FONT_NAME, 11)
    canvas.drawCentredString(page_width / 2, _PAGE_NUMBER_BASELINE, f"{doc.page}#")
    canvas.restoreState()
