"""Tests for the PDF font/bidi helpers backing the generated documents."""
from app.services.pdf_text import (
    FONT_NAME,
    FONT_NAME_BOLD,
    register_pdf_fonts,
    shape,
    shape_paragraph,
)

HEBREW_TITLE = "תעודת משלוח"


def test_register_pdf_fonts_is_idempotent():
    """Called once per PDF, so calling it twice must not raise or reload."""
    register_pdf_fonts()
    register_pdf_fonts()

    from reportlab.pdfbase import pdfmetrics

    assert pdfmetrics.getFont(FONT_NAME).fontName == FONT_NAME
    assert pdfmetrics.getFont(FONT_NAME_BOLD).fontName == FONT_NAME_BOLD


def test_shape_reverses_hebrew_into_visual_order():
    assert shape(HEBREW_TITLE) == HEBREW_TITLE[::-1]


def test_shape_leaves_latin_and_numbers_alone():
    """Reference numbers and quantities must not be flipped."""
    assert shape("DN-260722-0001") == "DN-260722-0001"
    assert shape("12.00") == "12.00"
    assert shape("Acme Ltd") == "Acme Ltd"


def test_shape_moves_trailing_colon_to_the_left_of_a_hebrew_label():
    """In an RTL run the colon belongs at the visual end - the left."""
    assert shape("תאריך:").startswith(":")


def test_shape_handles_none_and_empty():
    assert shape(None) == ""
    assert shape("") == ""
    assert shape_paragraph(None, FONT_NAME, 12, 100) == ""


def test_shape_paragraph_escapes_markup():
    """Paragraph parses its input as markup, so raw < & would break the build."""
    result = shape_paragraph("2 < 3 & 4", FONT_NAME, 12, 500)
    assert "&lt;" in result and "&amp;" in result
    assert "<" not in result.replace("&lt;", "")


def test_shape_paragraph_wraps_before_reordering():
    """Reordering is per visual line, so wrapping has to happen first -
    a single reordered blob wrapped by ReportLab would break at the wrong
    points. A narrow width must therefore produce explicit <br/> breaks."""
    register_pdf_fonts()
    wide = shape_paragraph("alpha beta gamma delta", FONT_NAME, 12, 500)
    narrow = shape_paragraph("alpha beta gamma delta", FONT_NAME, 12, 40)

    assert "<br/>" not in wide
    assert "<br/>" in narrow
    assert narrow.replace("<br/>", " ") == wide


def test_shape_paragraph_keeps_explicit_newlines():
    result = shape_paragraph("line one\nline two", FONT_NAME, 12, 500)
    assert result == "line one<br/>line two"
