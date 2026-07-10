from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Image, LongTable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


DEMO_LOGO_PATH = Path(__file__).resolve().parents[2] / "templates" / "demo-logo.png"


def _text(value) -> str:
    return escape(str(value or "")).replace("\n", "<br/>")


def _demo_logo(center_style):
    if DEMO_LOGO_PATH.is_file():
        return Image(str(DEMO_LOGO_PATH), width=51 * mm, height=16.2 * mm, kind="proportional")
    return Paragraph("<b>MISSION OPERATIONS PORTAL</b>", center_style)


def _remarks(asset) -> str:
    return str(asset.remarks or "").strip()


def _signature_cell(envelope, recipient_index, center_style):
    if not envelope:
        return ""
    recipients = envelope.get("recipients") or []
    if recipient_index >= len(recipients):
        return ""
    recipient = recipients[recipient_index]
    if recipient.get("status") != "signed":
        return Paragraph(f"<b>{_text(recipient.get('status', 'pending')).upper()}</b>", center_style)
    signed_at = recipient.get("signed_at")
    signed_date = signed_at.strftime("%d/%m/%Y") if hasattr(signed_at, "strftime") else str(signed_at or "")[:10]
    verification = recipient.get("verification_number") or ""
    return Paragraph(f"<font size='5.5'><b>SIGNED</b></font><br/><font size='5'>{_text(signed_date)}</font><br/><font size='4.2'>{_text(verification)}</font>", center_style)


def build_asset_form_pdf(user, assets, _organization=None, signature_status=None) -> bytes:
    """Build the demo staff asset form with one row per assigned asset."""
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=7 * mm,
        rightMargin=7 * mm,
        topMargin=6 * mm,
        bottomMargin=6 * mm,
        title=f"Asset Form - {user.full_name}",
        author="Mission Operations Portal",
    )
    body = ParagraphStyle("asset-body", fontName="Helvetica", fontSize=6.2, leading=7.2)
    center = ParagraphStyle("asset-center", parent=body, alignment=TA_CENTER)
    label = ParagraphStyle(
        "asset-label", parent=center, fontName="Helvetica-Bold", fontSize=6.5, leading=7.3
    )
    title = ParagraphStyle(
        "asset-title", fontName="Helvetica-Bold", fontSize=10.2, leading=11, alignment=TA_CENTER
    )
    note_style = ParagraphStyle("asset-note", fontName="Helvetica", fontSize=5.4, leading=6.3)

    first_asset = assets[0] if assets else None
    mission = (getattr(first_asset, "country", None) or "DEMO MISSION").upper()
    base = getattr(first_asset, "location", None) or ""
    role = getattr(user.role, "value", user.role)
    role = str(role or "").replace("_", " ").title()
    signature_status = signature_status or {}
    allocation = signature_status.get("allocation")
    returned = signature_status.get("return")

    identity = Table(
        [
            [
                Paragraph("<b>Logistics Department / Departement Logistique</b>", label),
                "",
                Paragraph("<b>Name-Surname /<br/>Nom-Prenom:</b>", label),
                Paragraph(_text(user.full_name), center),
            ],
            [
                Paragraph("<b>Mission:</b>", label),
                Paragraph(_text(mission), center),
                Paragraph("<b>Department /<br/>Departement:</b>", label),
                Paragraph(_text(user.department), center),
            ],
            [
                Paragraph("<b>Base:</b>", label),
                Paragraph(_text(base), center),
                Paragraph("<b>Position / Poste:</b>", label),
                Paragraph(_text(role), center),
            ],
        ],
        colWidths=[37 * mm, 57 * mm, 30 * mm, 57 * mm],
        rowHeights=[10 * mm, 10 * mm, 10 * mm],
    )
    identity.setStyle(
        TableStyle(
            [
                ("SPAN", (0, 0), (1, 0)),
                ("BACKGROUND", (0, 0), (1, 0), colors.HexColor("#d9d9d9")),
                ("BACKGROUND", (0, 1), (0, 2), colors.HexColor("#d9d9d9")),
                ("BACKGROUND", (2, 0), (2, 2), colors.HexColor("#d9d9d9")),
                ("GRID", (0, 0), (-1, -1), 0.55, colors.black),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    document_title = Table(
        [
            [_demo_logo(center)],
            [
                Paragraph(
                    "STAFF ASSET FORM / FICHE DE<br/>PRISE DE RESPONSABILITE<br/>D'EQUIPEMENTS",
                    title,
                )
            ],
        ],
        colWidths=[88 * mm],
        rowHeights=[17 * mm, 25 * mm],
    )
    document_title.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    header = Table([[document_title, identity]], colWidths=[89 * mm, 181 * mm])
    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    rows = [
        [
            "",
            "",
            "",
            "",
            "",
            Paragraph("<b>Employee signature / Signature de l'employe</b>", label),
            "",
            Paragraph(
                "<b>Logistics Department signature / Signature du departement<br/>logistique</b>",
                label,
            ),
            "",
            "",
        ],
        [
            Paragraph("<b>No</b>", label),
            Paragraph("<b>Designation</b>", label),
            Paragraph("<b>Model / Modele</b>", label),
            Paragraph("<b>Serial Number /<br/>Numero de serie</b>", label),
            Paragraph("<b>Log code / Code Log</b>", label),
            Paragraph("<b>Signature Received*<br/>Date / Signature a la<br/>reception*</b>", label),
            Paragraph("<b>Signature Return<br/>Date / Signature au<br/>retour</b>", label),
            Paragraph("<b>Signature Received<br/>Date / Signature a la<br/>reception</b>", label),
            Paragraph("<b>Signature Return<br/>Date / Signature au<br/>retour</b>", label),
            Paragraph("<b>Remarks<br/>Remarques</b>", label),
        ],
    ]
    for number, asset in enumerate(assets, 1):
        rows.append(
            [
                str(number),
                Paragraph(_text(asset.designation), center),
                Paragraph(_text(" / ".join(filter(None, [asset.brand, asset.model]))), center),
                Paragraph(_text(asset.serial_number), center),
                Paragraph(_text(asset.logistics_code), center),
                _signature_cell(allocation, 0, center),
                _signature_cell(returned, 0, center),
                _signature_cell(returned, 1, center),
                _signature_cell(allocation, 1, center),
                Paragraph(_text(_remarks(asset)), center),
            ]
        )
    if not assets:
        rows.append([Paragraph("<i>No assigned assets found.</i>", center)] + [""] * 9)

    asset_table = LongTable(
        rows,
        repeatRows=2,
        rowHeights=[9 * mm, 24 * mm] + [26 * mm] * max(1, len(assets)),
        colWidths=[
            9 * mm,
            35 * mm,
            29 * mm,
            31 * mm,
            30 * mm,
            27 * mm,
            27 * mm,
            27 * mm,
            27 * mm,
            28 * mm,
        ],
        splitByRow=1,
    )
    table_style = [
        ("SPAN", (5, 0), (6, 0)),
        ("SPAN", (7, 0), (8, 0)),
        ("BACKGROUND", (0, 0), (-1, 1), colors.HexColor("#d9d9d9")),
        ("FONTNAME", (0, 0), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 6.2),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.55, colors.black),
        ("TOPPADDING", (0, 0), (-1, 1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, 1), 5),
        ("TOPPADDING", (0, 2), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 2), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]
    if not assets:
        table_style.append(("SPAN", (0, 2), (-1, 2)))
    asset_table.setStyle(TableStyle(table_style))

    signatures = Table(
        [
            [
                "",
                Paragraph("Issued by Logistics Redige par la logistique:", center),
                Paragraph(
                    "Signature of employee at the end of the contract / Signature de l'employe a la fin<br/>du contrat:",
                    center,
                ),
                Paragraph(
                    "Signature of Finance or Administration at the end of the contract /<br/>"
                    "Signature des finances ou de l'Administration a la fin du contrat",
                    center,
                ),
            ],
            [Paragraph("<b>Name/Nom :</b>", label), "", "", ""],
            [Paragraph("<b>Signature:</b>", label), "", "", ""],
        ],
        colWidths=[41 * mm, 55 * mm, 88 * mm, 86 * mm],
        rowHeights=[16 * mm, 10 * mm, 20 * mm],
    )
    signatures.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (1, 0), (-1, 0), colors.HexColor("#d9d9d9")),
                ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#d9d9d9")),
                ("GRID", (0, 0), (-1, -1), 0.55, colors.black),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTSIZE", (0, 0), (-1, -1), 6.2),
            ]
        )
    )
    responsibility_note = Paragraph(
        "*You are fully responsible for all asset/equipment specified in the form. No asset assigned to you is to be "
        "transferred without the notification of Logistics. All asset/equipment must be transferred properly and "
        "removed from your asset/equipment sheet.<br/><br/>"
        "*Vous etes entierement responsable des equipements qui vous sont remis et mentionne sur ce format. Aucun "
        "equipement qui vous sera remis ne pourra etre transfere sans en informer le service logistique. Tout "
        "equipement doit etre transfere selon les regles et enleve de ce format si besoin et / ou necessaire.",
        note_style,
    )
    document.build(
        [
            header,
            Spacer(1, 2 * mm),
            asset_table,
            Spacer(1, 2 * mm),
            signatures,
            Spacer(1, 2 * mm),
            responsibility_note,
        ]
    )
    return buffer.getvalue()
