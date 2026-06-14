from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any


_DIMENSION_LABELS = {
    "clarity":       "Clareza",
    "completeness":  "Completude",
    "consistency":   "Consistencia",
    "verifiability": "Verificabilidade",
}
_DIMENSION_ORDER = ["clarity", "completeness", "consistency", "verifiability"]

# Monochrome palette
_BLACK  = (0, 0, 0)
_DARK   = (30, 30, 30)
_MID    = (90, 90, 90)
_LIGHT  = (160, 160, 160)
_RULE   = (200, 200, 200)
_BG     = (245, 245, 245)


def generate_quality_pdf(quality_result: dict[str, Any], output_path: Path) -> Path:
    from fpdf import FPDF

    report      = quality_result.get("report", {})
    summary     = report.get("summary", "")
    suggestions = report.get("suggestions", [])
    today       = date.today().strftime("%d/%m/%Y")

    class PDF(FPDF):
        def header(self):
            pass

        def footer(self):
            self.set_y(-14)
            self.set_draw_color(*_RULE)
            self.set_line_width(0.3)
            self.line(self.l_margin, self.get_y(), self.l_margin + self.w - self.l_margin - self.r_margin, self.get_y())
            self.ln(2)
            self.set_font("Helvetica", "I", 9)
            self.set_text_color(*_LIGHT)
            self.cell(0, 5, f"Relatorio de Qualidade de Requisitos  |  {today}", align="C")

    pdf = PDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    W = pdf.w - pdf.l_margin - pdf.r_margin

    def hrule(thickness: float = 0.3, color=_RULE) -> None:
        pdf.set_draw_color(*color)
        pdf.set_line_width(thickness)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + W, pdf.get_y())
        pdf.ln(5)

    def section_title(text: str) -> None:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*_LIGHT)
        pdf.cell(W, 5, text.upper(), ln=True)
        pdf.ln(1)
        hrule(0.3, _RULE)

    # ── Title block ────────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(*_BLACK)
    pdf.cell(W, 12, "Relatorio de Qualidade", ln=True)

    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(*_MID)
    pdf.cell(W, 7, "Analise de documento de requisitos para geracao de diagramas UML", ln=True)
    pdf.ln(3)
    hrule(0.6, _DARK)

    # ── Summary ────────────────────────────────────────────────────────────────
    section_title("Resumo Geral")
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*_DARK)
    pdf.multi_cell(W, 6, summary)
    pdf.ln(8)

    # ── Dimensions ─────────────────────────────────────────────────────────────
    section_title("Avaliacao por Dimensao")

    for dim in _DIMENSION_ORDER:
        dim_data   = report.get(dim)
        if not dim_data:
            continue
        highlights = dim_data.get("highlights", [])
        issues     = dim_data.get("issues", [])
        label      = _DIMENSION_LABELS.get(dim, dim)

        # Dimension heading
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(*_BLACK)
        pdf.cell(W, 7, label, ln=True)

        # Highlights sub-block
        if highlights:
            pdf.ln(1)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*_MID)
            pdf.cell(W, 5, "Pontos positivos", ln=True)
            pdf.ln(1)
            for h in highlights:
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(*_DARK)
                pdf.set_x(pdf.l_margin + 5)
                pdf.cell(6, 5.5, "+")
                pdf.set_x(pdf.l_margin + 11)
                pdf.multi_cell(W - 11, 5.5, h)

        # Issues sub-block
        if issues:
            pdf.ln(2 if highlights else 1)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*_MID)
            pdf.cell(W, 5, "Problemas identificados", ln=True)
            pdf.ln(1)
            for issue in issues:
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(*_DARK)
                pdf.set_x(pdf.l_margin + 5)
                pdf.cell(6, 5.5, "-")
                pdf.set_x(pdf.l_margin + 11)
                pdf.multi_cell(W - 11, 5.5, issue)

        if not highlights and not issues:
            pdf.set_font("Helvetica", "I", 10)
            pdf.set_text_color(*_LIGHT)
            pdf.set_x(pdf.l_margin + 5)
            pdf.cell(W - 5, 5.5, "Sem observacoes.", ln=True)

        pdf.ln(4)
        # thin divider between dimensions
        pdf.set_draw_color(*_RULE)
        pdf.set_line_width(0.2)
        pdf.line(pdf.l_margin + 2, pdf.get_y(), pdf.l_margin + W, pdf.get_y())
        pdf.ln(5)

    pdf.ln(2)

    # ── Suggestions ────────────────────────────────────────────────────────────
    if suggestions:
        section_title("Sugestoes de Melhoria")
        for i, suggestion in enumerate(suggestions, 1):
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(*_MID)
            pdf.set_x(pdf.l_margin)
            pdf.cell(10, 6, f"{i}.")
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(*_DARK)
            pdf.set_x(pdf.l_margin + 10)
            pdf.multi_cell(W - 10, 6, suggestion)
            pdf.ln(2)

    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)
    pdf_path = output_path / "quality_report.pdf"
    pdf.output(str(pdf_path))
    return pdf_path
