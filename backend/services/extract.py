"""PDF (PyMuPDF) and DOCX (python-docx) text extraction."""
def extract_text(path):
    if str(path).lower().endswith('.pdf'):
        import pymupdf as fitz
        with fitz.open(path) as doc:
            return '\n'.join(p.get_text() for p in doc)
    import docx
    d = docx.Document(path)
    parts = [p.text for p in d.paragraphs]
    for t in d.tables:
        for row in t.rows:
            parts.append(' | '.join(c.text for c in row.cells))
    return '\n'.join(parts)
