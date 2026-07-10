from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from app.config import settings
from app.services.asset_form_pdf import build_asset_form_pdf


def _logo(settings_record, width=42 * mm, height=18 * mm):
    if settings_record and settings_record.logo_stored_name:
        path = settings.upload_directory / "branding" / settings_record.logo_stored_name
        if path.is_file():
            return Image(str(path), width=width, height=height, kind="proportional")
    return Paragraph(
        "<b>OPERATIONS PORTAL</b><br/><font size='7'>Internal operations platform</font>",
        ParagraphStyle("logo", alignment=TA_CENTER, textColor=colors.HexColor("#17345b")),
    )


def _legacy_build_asset_form_pdf(user, assets, organization) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4), leftMargin=10 * mm, rightMargin=10 * mm,
        topMargin=9 * mm, bottomMargin=8 * mm,
        title=f"Asset Form - {user.full_name}",
    )
    small = ParagraphStyle("small", fontName="Helvetica", fontSize=6.3, leading=7.4)
    center = ParagraphStyle("center", parent=small, alignment=TA_CENTER)
    title = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=12, leading=14, alignment=TA_CENTER)
    org_name = organization.organization_name if organization else "Mission Operations Portal"
    header = Table([
        [_logo(organization), Paragraph(f"<b>{org_name}</b><br/>STAFF ASSET FORM / FICHE DE PRISE DE RESPONSABILITE D'EQUIPEMENTS", title),
         Table([
             [Paragraph("<b>Name-Surname / Nom-Prénom</b>", center), Paragraph(user.full_name, center)],
             [Paragraph("<b>Department / Département</b>", center), Paragraph(user.department or "", center)],
             [Paragraph("<b>Date generated</b>", center), Paragraph(__import__("datetime").date.today().strftime("%d/%m/%Y"), center)],
         ], colWidths=[42 * mm, 45 * mm], rowHeights=[9 * mm] * 3)]
    ], colWidths=[48 * mm, 130 * mm, 87 * mm])
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BOX", (2, 0), (2, 0), .7, colors.black),
        ("INNERGRID", (2, 0), (2, 0), .35, colors.grey),
    ]))
    rows = [[
        Paragraph("<b>No</b>", center), Paragraph("<b>Designation</b>", center),
        Paragraph("<b>Brand / Model</b>", center), Paragraph("<b>Serial Number<br/>Numéro de série</b>", center),
        Paragraph("<b>Log code / Code Log</b>", center), Paragraph("<b>Location</b>", center),
        Paragraph("<b>Condition</b>", center), Paragraph("<b>Accessories</b>", center),
        Paragraph("<b>Remarks / Remarques</b>", center),
    ]]
    for number, asset in enumerate(assets, 1):
        rows.append([
            str(number), Paragraph(asset.designation, center),
            Paragraph(" / ".join(filter(None, [asset.brand, asset.model])), center),
            Paragraph(asset.serial_number or "", center), Paragraph(asset.logistics_code, center),
            Paragraph(asset.location, center), Paragraph(asset.condition or "", center),
            Paragraph(asset.accessories or "", center), Paragraph(asset.remarks or "", center),
        ])
    while len(rows) < 7:
        rows.append([""] * 9)
    asset_table = Table(
        rows, repeatRows=1,
        colWidths=[10 * mm, 39 * mm, 35 * mm, 31 * mm, 43 * mm, 25 * mm, 22 * mm, 35 * mm, 40 * mm],
        rowHeights=[13 * mm] + [10 * mm] * (len(rows) - 1),
    )
    asset_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d8d8d8")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 6.3),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), .55, colors.black),
    ]))
    signatures = Table([
        [Paragraph("<b>Employee signature / Signature de l'employé</b>", center),
         Paragraph("<b>Logistics Department signature / Signature du département logistique</b>", center),
         Paragraph("<b>Finance / Administration validation</b>", center)],
        ["\n\nName / Date / Signature", "\n\nName / Date / Signature", "\n\nName / Date / Signature"],
    ], colWidths=[88 * mm] * 3, rowHeights=[8 * mm, 24 * mm])
    signatures.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d8d8d8")),
        ("GRID", (0, 0), (-1, -1), .55, colors.black), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("FONTSIZE", (0, 0), (-1, -1), 7),
    ]))
    note = Paragraph(
        "*You are fully responsible for all assets/equipment specified in this form. No assigned asset may be transferred without notifying Logistics. "
        "All assets must be transferred properly and removed from this asset sheet when returned.<br/>"
        "*Vous êtes entièrement responsable des équipements indiqués sur ce formulaire. Aucun équipement ne peut être transféré sans informer la Logistique.<br/>"
        "", small,
    )
    doc.build([header, Spacer(1, 5 * mm), asset_table, Spacer(1, 4 * mm), signatures, Spacer(1, 3 * mm), note])
    return buffer.getvalue()


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
