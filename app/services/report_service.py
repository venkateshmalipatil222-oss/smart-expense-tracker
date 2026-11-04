import io
from datetime import date, datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import func
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
)
from app.models.transaction import Transaction
from app.models.category import Category

class ReportService:
    """
    Executive Financial Statement & Tax Summary PDF Generation Engine.
    Generates publication-quality, vectorized financial statements using ReportLab.
    """

    @classmethod
    def generate_pdf_statement(
        cls,
        start_date: date,
        end_date: date,
        user_name: str = "Authorized Account Holder"
    ) -> bytes:
        """
        Compiles ledger data and renders a structured executive PDF statement.
        Returns the raw PDF bytes.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        
        # Custom Typography Styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#0F172A"),
            spaceAfter=4
        )
        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#64748B"),
            spaceAfter=12
        )
        section_heading = ParagraphStyle(
            "SectionHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#1E293B"),
            spaceBefore=12,
            spaceAfter=6
        )
        cell_style = ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#1E293B")
        )
        cell_bold = ParagraphStyle(
            "TableCellBold",
            parent=cell_style,
            fontName="Helvetica-Bold"
        )
        kpi_label_style = ParagraphStyle(
            "KPILabel",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#64748B"),
            alignment=1
        )
        kpi_value_style = ParagraphStyle(
            "KPIValue",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#0F172A"),
            alignment=1
        )
        disclaimer_style = ParagraphStyle(
            "Disclaimer",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#94A3B8"),
            alignment=1,
            spaceBefore=14
        )

        story = []

        # 1. Header Banner & Identity
        story.append(Paragraph("SMARTEXPENSE &bull; EXECUTIVE FINANCIAL STATEMENT", title_style))
        period_str = f"Statement Period: {start_date.strftime('%b %d, %Y')} &mdash; {end_date.strftime('%b %d, %Y')} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        user_info_str = f"Account: <b>{user_name}</b> | Currency Base: <b>USD ($)</b>"
        story.append(Paragraph(f"{period_str}<br/>{user_info_str}", subtitle_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E1"), spaceAfter=10))

        # 2. Gather Data Metrics
        all_txs = Transaction.query.filter(
            Transaction.date >= start_date,
            Transaction.date <= end_date
        ).order_by(Transaction.date.desc()).all()

        inflows = sum(t.amount for t in all_txs if t.transaction_type == "income")
        outflows = sum(t.amount for t in all_txs if t.transaction_type == "expense")
        net_savings = inflows - outflows
        savings_rate = (net_savings / inflows * 100.0) if inflows > 0 else 0.0

        # 3. KPI Executive Summary Table
        kpi_data = [
            [
                Paragraph("TOTAL CASH INFLOW", kpi_label_style),
                Paragraph("TOTAL CASH OUTFLOW", kpi_label_style),
                Paragraph("NET CASH FLOW", kpi_label_style),
                Paragraph("SAVINGS RATE", kpi_label_style)
            ],
            [
                Paragraph(f"${inflows:,.2f}", kpi_value_style),
                Paragraph(f"${outflows:,.2f}", kpi_value_style),
                Paragraph(f"${net_savings:,.2f}", kpi_value_style),
                Paragraph(f"{savings_rate:.1f}%", kpi_value_style)
            ]
        ]
        kpi_table = Table(kpi_data, colWidths=[135, 135, 135, 135])
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(kpi_table)
        story.append(Spacer(1, 12))

        # 4. Category Breakdown Table
        story.append(Paragraph("EXPENSE DISTRIBUTION BY CATEGORY", section_heading))
        cat_map: Dict[int, Dict[str, Any]] = {}
        for t in all_txs:
            if t.transaction_type != "expense":
                continue
            cid = t.category_id
            cname = t.category.name if t.category else "Uncategorized"
            if cid not in cat_map:
                cat_map[cid] = {"name": cname, "count": 0, "amount": 0.0}
            cat_map[cid]["count"] += 1
            cat_map[cid]["amount"] += t.amount

        sorted_cats = sorted(cat_map.values(), key=lambda x: x["amount"], reverse=True)

        cat_rows = [
            [
                Paragraph("Category", cell_bold),
                Paragraph("Transactions", cell_bold),
                Paragraph("Total Amount", cell_bold),
                Paragraph("% of Expenses", cell_bold)
            ]
        ]

        if sorted_cats:
            for c in sorted_cats:
                pct = (c["amount"] / outflows * 100.0) if outflows > 0 else 0.0
                cat_rows.append([
                    Paragraph(c["name"], cell_style),
                    Paragraph(str(c["count"]), cell_style),
                    Paragraph(f"${c['amount']:,.2f}", cell_style),
                    Paragraph(f"{pct:.1f}%", cell_style)
                ])
        else:
            cat_rows.append([
                Paragraph("No expenses recorded in this period.", cell_style),
                Paragraph("-", cell_style),
                Paragraph("$0.00", cell_style),
                Paragraph("0.0%", cell_style)
            ])

        cat_table = Table(cat_rows, colWidths=[200, 100, 120, 120])
        cat_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
        ]))
        story.append(cat_table)
        story.append(Spacer(1, 12))

        # 5. Tax Deductible Analysis
        story.append(Paragraph("POTENTIAL TAX DEDUCTIBLE EXPENDITURES", section_heading))
        tax_keywords = ["medical", "health", "doctor", "clinic", "pharmacy", "charity", "donation", "education", "tuition", "utilities", "home office"]
        tax_txs = [
            t for t in all_txs
            if t.transaction_type == "expense" and (
                any(k in (t.category.name.lower() if t.category else "") for k in ["health", "utilit"]) or
                any(k in t.description.lower() for k in tax_keywords)
            )
        ]

        tax_rows = [
            [
                Paragraph("Date", cell_bold),
                Paragraph("Category", cell_bold),
                Paragraph("Description / Payee", cell_bold),
                Paragraph("Deductible Est.", cell_bold)
            ]
        ]

        if tax_txs:
            for t in tax_txs[:12]:  # Limit to top 12
                cname = t.category.name if t.category else "Uncategorized"
                tax_rows.append([
                    Paragraph(t.date.strftime("%Y-%m-%d"), cell_style),
                    Paragraph(cname, cell_style),
                    Paragraph(t.description[:40], cell_style),
                    Paragraph(f"${t.amount:,.2f}", cell_style)
                ])
            tax_total = sum(t.amount for t in tax_txs)
            tax_rows.append([
                Paragraph("<b>Total Potential Deductions</b>", cell_bold),
                Paragraph("-", cell_style),
                Paragraph(f"<b>{len(tax_txs)} item(s)</b>", cell_style),
                Paragraph(f"<b>${tax_total:,.2f}</b>", cell_bold)
            ])
        else:
            tax_rows.append([
                Paragraph("-", cell_style),
                Paragraph("None Identified", cell_style),
                Paragraph("No qualifying tax deductible expenditures found in this interval.", cell_style),
                Paragraph("$0.00", cell_style)
            ])

        tax_table = Table(tax_rows, colWidths=[90, 130, 210, 110])
        tax_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#FEF3C7")),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#FDE68A")),
        ]))
        story.append(tax_table)
        story.append(Spacer(1, 12))

        # 6. Major Transactions Audit (Top 8 Outflows)
        story.append(Paragraph("LARGEST EXPENDITURES AUDIT", section_heading))
        large_txs = sorted([t for t in all_txs if t.transaction_type == "expense"], key=lambda x: x.amount, reverse=True)[:8]
        large_rows = [
            [
                Paragraph("Date", cell_bold),
                Paragraph("Category", cell_bold),
                Paragraph("Description", cell_bold),
                Paragraph("Currency & Rate", cell_bold),
                Paragraph("Normalized (USD)", cell_bold)
            ]
        ]
        if large_txs:
            for t in large_txs:
                curr_info = f"{t.currency or 'USD'} @ {t.exchange_rate or 1.0}"
                large_rows.append([
                    Paragraph(t.date.strftime("%Y-%m-%d"), cell_style),
                    Paragraph(t.category.name if t.category else "Uncategorized", cell_style),
                    Paragraph(t.description[:35], cell_style),
                    Paragraph(curr_info, cell_style),
                    Paragraph(f"${t.amount:,.2f}", cell_style)
                ])
        else:
            large_rows.append([
                Paragraph("-", cell_style),
                Paragraph("No Expenses", cell_style),
                Paragraph("No major transactions in selected window", cell_style),
                Paragraph("-", cell_style),
                Paragraph("$0.00", cell_style)
            ])

        large_table = Table(large_rows, colWidths=[80, 120, 170, 90, 80])
        large_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
        ]))
        story.append(large_table)

        # 7. Legal & Audit Disclaimer
        story.append(Paragraph(
            "DISCLAIMER: This financial statement is auto-generated by the SmartExpense AI Platform ledger service. "
            "It is provided for informational and financial planning purposes only and does not constitute certified tax or accounting advice. "
            "Consult a licensed CPA or financial advisor for IRS/statutory filings.",
            disclaimer_style
        ))

        # Build document
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
