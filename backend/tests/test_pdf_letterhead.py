"""Tests for the Lino Print letterhead drawn on every page of the generated PDFs."""
import io

import pypdf
from reportlab.lib.pagesizes import A4
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate

from app.services.pdf_letterhead import LETTERHEAD_TOP_MARGIN, draw_letterhead
from app.services.pdf_text import register_pdf_fonts


def _build_two_page_pdf() -> pypdf.PdfReader:
    register_pdf_fonts()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=LETTERHEAD_TOP_MARGIN)
    doc.build(
        [Paragraph("first"), PageBreak(), Paragraph("second")],
        onFirstPage=draw_letterhead,
        onLaterPages=draw_letterhead,
    )
    return pypdf.PdfReader(io.BytesIO(buffer.getvalue()))


def test_every_page_carries_the_header_image():
    reader = _build_two_page_pdf()

    assert len(reader.pages) == 2
    for page in reader.pages:
        assert len(page.images) == 1


def test_every_page_is_numbered_like_the_template():
    reader = _build_two_page_pdf()

    assert "1#" in reader.pages[0].extract_text()
    assert "2#" in reader.pages[1].extract_text()
