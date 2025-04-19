from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from typing import Dict
import os

class ReportGenerator:
    def __init__(self, data: Dict[str, float]):
        self.data = data
        self.styles = getSampleStyleSheet()
        self.output_file = "project_cost_report.pdf"

    def generate_pdf(self):
        """Generate a PDF report using ReportLab."""
        try:
            doc = SimpleDocTemplate(self.output_file, pagesize=letter)
            elements = []

            # Title
            title_style = self.styles['Heading1']
            elements.append(Paragraph("Project Cost Estimation Report", title_style))
            elements.append(Spacer(1, 12))

            # Project Details
            body_style = ParagraphStyle(
                name='BodyText',
                parent=self.styles['BodyText'],
                fontSize=12,
                leading=14
            )
            elements.append(Paragraph("Category: Semi-Detached Software Project", body_style))
            elements.append(Paragraph(f"Efforts Adjustment Factor (EAF): {self.data.get('eaf', 1.0)}", body_style))
            elements.append(Spacer(1, 12))

            # LOC and KLOC
            elements.append(Paragraph(f"Lines of Code (LOC): {self.data['loc']}", body_style))
            elements.append(Paragraph(f"KLOC: {self.data['kloc']}", body_style))
            elements.append(Spacer(1, 12))

            # COCOMO Calculations
            elements.append(Paragraph(f"Effort (E): {self.data['effort']} Person-Months", body_style))
            elements.append(Paragraph(f"Time (T): {self.data['time']} Months", body_style))
            elements.append(Paragraph(f"People (P): {self.data['people']} Persons", body_style))
            elements.append(Spacer(1, 12))

            # Cost Breakdown
            elements.append(Paragraph("Cost Estimation:", self.styles['Heading2']))
            cost_data = [
                ["Description", "Amount (Rs.)"],
                ["Developer Cost", f"{self.data['developer_cost']}"],
                ["Final System Cost", f"{self.data['final_system_cost']}"],
                ["Paid Software Cost", f"{self.data['paid_sw_cost']}"],
                ["Miscellaneous Cost", f"{self.data['misc_cost']}"],
                ["Total Cost", f"{self.data['total_cost']}"]
            ]
            table = Table(cost_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(table)

            # Build PDF
            doc.build(elements)
            return self.output_file
        except Exception as e:
            raise ValueError(f"Error generating PDF report: {e}")

    def generate_text(self):
        """Generate a text report."""
        try:
            template = """
Project Cost Estimation Report
==============================
Category: Semi-Detached Software Project
Efforts Adjustment Factor (EAF): {eaf}

Lines of Code (LOC): {loc}
KLOC: {kloc}

COCOMO Calculations:
- Effort (E): {effort} Person-Months
- Time (T): {time} Months
- People (P): {people} Persons

Cost Estimation:
1. Developer Cost: Rs. {developer_cost}
2. Final System Cost: Rs. {final_system_cost}
3. Paid Software Cost: Rs. {paid_sw_cost}
4. Miscellaneous Cost: Rs. {misc_cost}
5. Total Cost: Rs. {total_cost}
==============================
"""
            output = template.format(**self.data)
            text_file = "project_cost_report.txt"
            with open(text_file, 'w') as f:
                f.write(output)
            return text_file
        except Exception as e:
            raise ValueError(f"Error generating text report: {e}")