from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.pdfgen import canvas


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def append_signature_page(
    source_pdf: bytes,
    *,
    envelope_id: str,
    verification_number: str,
    signer_name: str,
    signer_email: str,
    role_name: str | None,
    signed_at: str,
    document_hash: str,
    signature_image_path: Path | None,
    typed_name: str | None,
    signature_page: int = -1,
    signature_x: float = .61,
    signature_y: float = .06,
    signature_width: float = .32,
    signature_height: float = .16,
    add_envelope_label: bool = False,
) -> bytes:
    """Apply a visible authenticated signature stamp to a configured PDF area.

    Coordinates are stored as ratios so the same signing workflow works with
    portrait, landscape, and organization-specific templates. Page numbers are
    one-based; ``-1`` means the final page.
    """
    source = PdfReader(BytesIO(source_pdf))
    if not source.pages:
        raise ValueError("The signing document has no pages")

    page_index = len(source.pages) - 1 if signature_page == -1 else signature_page - 1
    page_index = int(_clamp(page_index, 0, len(source.pages) - 1))
    writer = PdfWriter(clone_from=BytesIO(source_pdf))
    target = writer.pages[page_index]
    page_width = float(target.mediabox.width)
    page_height = float(target.mediabox.height)

    x_ratio = _clamp(signature_x, 0, .95)
    y_ratio = _clamp(signature_y, 0, .95)
    width_ratio = _clamp(signature_width, .08, 1 - x_ratio)
    height_ratio = _clamp(signature_height, .06, 1 - y_ratio)
    box_x, box_y = page_width * x_ratio, page_height * y_ratio
    box_w, box_h = page_width * width_ratio, page_height * height_ratio

    stamp_buffer = BytesIO()
    pdf = canvas.Canvas(stamp_buffer, pagesize=(page_width, page_height))
    pdf.setTitle(f"Signed - {envelope_id}")
    if add_envelope_label:
        pdf.setFillColor(colors.HexColor("#27364a"))
        pdf.setFont("Helvetica-Bold", 6)
        label = f"Envelope ID: {envelope_id}"
        pdf.drawRightString(page_width - 18, page_height - 14, label)
    pdf.setStrokeColor(colors.HexColor("#3268a8"))
    pdf.setFillColor(colors.white)
    pdf.roundRect(box_x, box_y, box_w, box_h, min(5, box_h * .08), fill=1, stroke=1)

    compact = box_w < 145 or box_h < 75
    inset = max(4, min(10, box_w * .05))
    image_h = box_h * (.48 if compact else .42)
    image_w = box_w - inset * 2
    image_y = box_y + box_h - image_h - inset
    if signature_image_path and signature_image_path.is_file():
        pdf.drawImage(
            str(signature_image_path), box_x + inset, image_y,
            width=image_w, height=image_h, preserveAspectRatio=True,
            anchor="sw", mask="auto",
        )
    else:
        pdf.setFont("Helvetica-Oblique", _clamp(box_h * .20, 8, 22))
        pdf.setFillColor(colors.HexColor("#174f91"))
        pdf.drawCentredString(box_x + box_w / 2, image_y + image_h * .35, typed_name or signer_name)

    pdf.setFillColor(colors.HexColor("#13233d"))
    if compact:
        pdf.setFont("Helvetica-Bold", _clamp(box_h * .075, 4.5, 7))
        pdf.drawString(box_x + inset, box_y + box_h * .25, "SIGNED")
        pdf.setFont("Helvetica", _clamp(box_h * .066, 4, 6.5))
        pdf.drawString(box_x + inset, box_y + box_h * .14, signer_name[:28])
        pdf.drawString(box_x + inset, box_y + box_h * .055, verification_number)
    else:
        font_size = _clamp(box_h * .055, 4.8, 6.6)
        lines = [
            f"Signed by: {signer_name}",
            f"Email: {signer_email}",
            f"Role: {role_name or 'Signer'}",
            f"Verification: {verification_number}",
            f"Date signed: {signed_at}",
            f"SHA256: {document_hash[:16]}...{document_hash[-8:]}",
        ]
        line_y = image_y - font_size * 1.6
        for index, line in enumerate(lines):
            pdf.setFont("Helvetica-Bold" if index == 0 else "Helvetica", font_size)
            pdf.drawString(box_x + inset, line_y, line[:120])
            line_y -= font_size * 1.35
            if line_y < box_y + 2:
                break
    pdf.save()

    overlay = PdfReader(BytesIO(stamp_buffer.getvalue())).pages[0]
    target.merge_page(overlay)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()
