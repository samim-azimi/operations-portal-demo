from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from app.config import settings

def _logo(settings_record, width=42 * mm, height=18 * mm):
    if settings_record and settings_record.logo_stored_name:
        path = settings.upload_directory / "branding" / settings_record.logo_stored_name
        if path.is_file():
            return Image(str(path), width=width, height=height, kind="proportional")
    return Paragraph(
        "<b>OPERATIONS PORTAL</b><br/><font size='7'>Internal operations platform</font>",
        ParagraphStyle("logo", alignment=TA_CENTER, textColor=colors.HexColor("#17345b")),
    )


def build_stock_card_pdf(card, movements, previous_balance, date_from, date_to, organization) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4), leftMargin=9 * mm, rightMargin=9 * mm,
        topMargin=8 * mm, bottomMargin=8 * mm, title=f"Stock Card {card.stock_card_number}",
    )
    small = ParagraphStyle("stock-small", fontName="Helvetica", fontSize=6.5, leading=7.2)
    center = ParagraphStyle("stock-center", parent=small, alignment=TA_CENTER)
    title = ParagraphStyle("stock-title", fontName="Helvetica-Bold", fontSize=14, alignment=TA_CENTER)
    header = Table([[
        _logo(organization), Paragraph("<b>STOCK CARD</b>", title),
        Table([[Paragraph("<b>Stock Card Number</b>", center)], [Paragraph(card.stock_card_number, center)]],
              colWidths=[52 * mm], rowHeights=[8 * mm, 10 * mm]),
    ]], colWidths=[50 * mm, 160 * mm, 52 * mm])
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BOX", (2, 0), (2, 0), .7, colors.black)]))
    details = Table([
        [Paragraph("<b>Base</b>", center), card.base, Paragraph("<b>Code Opé / Grant Number</b>", center), card.project_code or ""],
        [Paragraph("<b>Item Description / Description du bien</b>", center), card.item_name, Paragraph("<b>DONOR NAME</b>", center), card.donor or ""],
        [Paragraph("<b>Unit / Unité</b>", center), card.unit, Paragraph("<b>Reference if needed</b>", center), card.comments or ""],
    ], colWidths=[45 * mm, 86 * mm, 48 * mm, 83 * mm], rowHeights=[9 * mm] * 3)
    details.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), .55, colors.black), ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#d8d8d8")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#d8d8d8")), ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    rows = [[
        Paragraph("<b>Date</b>", center), Paragraph("<b>Goods Received Note No</b>", center),
        Paragraph("<b>In / Entrée</b>", center), Paragraph("<b>Out / Sortie</b>", center),
        Paragraph("<b>Stock Transfer No</b>", center), Paragraph("<b>Balance (Weight)</b>", center),
        Paragraph("<b>Balance (Unit)</b>", center), Paragraph("<b>Destination / Remarks</b>", center),
        Paragraph("<b>Signature</b>", center),
    ]]
    balance = float(previous_balance)
    rows.append([date_from.strftime("%d/%m/%Y"), "", "", "", "", "", f"{balance:g}",
                 "Previous balance brought forward / Balance précédente reportée", ""])
    for movement in movements:
        balance += float(movement.quantity_in or 0) - float(movement.quantity_out or 0)
        rows.append([
            movement.movement_date.strftime("%d/%m/%Y"), movement.goods_received_note_no or "",
            f"{movement.quantity_in:g}" if movement.quantity_in else "",
            f"{movement.quantity_out:g}" if movement.quantity_out else "",
            movement.stock_transfer_no or "", "", f"{balance:g}",
            movement.destination or movement.remarks or movement.comments or "", movement.signature_name or "",
        ])
    while len(rows) < 12:
        rows.append([""] * 9)
    table = Table(rows, repeatRows=1, colWidths=[22*mm,31*mm,17*mm,17*mm,29*mm,24*mm,24*mm,72*mm,26*mm], rowHeights=[15*mm]+[10*mm]*(len(rows)-1))
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d8d8d8")), ("GRID", (0, 0), (-1, -1), .55, colors.black),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 0), (-1, -1), 6.5),
    ]))
    footer = Paragraph(
        f"Period: {date_from:%d/%m/%Y} - {date_to:%d/%m/%Y}",
        center,
    )
    doc.build([header, Spacer(1, 4*mm), details, Spacer(1, 4*mm), table, Spacer(1, 3*mm), footer])
    return buffer.getvalue()
