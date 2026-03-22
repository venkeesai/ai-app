from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer

from app.models import ArticleResult


class PDFExportService:
    def export(self, articles: Iterable[ArticleResult], destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        articles = list(articles)
        styles = getSampleStyleSheet()
        headline_style = ParagraphStyle(
            "Headline",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#8B0000"),
            spaceAfter=10,
        )
        subheading_style = ParagraphStyle(
            "Subheading",
            parent=styles["Heading2"],
            fontName="Helvetica",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#333333"),
            spaceAfter=10,
        )
        body_style = ParagraphStyle(
            "Body",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            spaceAfter=8,
        )

        story = []
        for index, article in enumerate(articles):
            if article.metadata.get("image_path"):
                image_path = Path(article.metadata["image_path"])
                if image_path.exists():
                    story.append(Image(str(image_path), width=6.6 * inch, height=3.8 * inch, kind="proportional"))
                    story.append(Spacer(1, 0.2 * inch))
            story.append(Paragraph(article.headline, headline_style))
            if article.subheading:
                story.append(Paragraph(article.subheading, subheading_style))
            for paragraph in article.body_paragraphs:
                story.append(Paragraph(paragraph, body_style))
            if article.captions:
                story.append(Spacer(1, 0.1 * inch))
                story.append(Paragraph(f"Caption: {article.captions[0]}", subheading_style))
            if index < len(articles) - 1:
                story.append(PageBreak())

        doc = SimpleDocTemplate(str(destination), pagesize=A4, rightMargin=48, leftMargin=48, topMargin=48, bottomMargin=48)
        doc.build(story)
        return destination

    @staticmethod
    def bytes_for_download(path: Path) -> bytes:
        return path.read_bytes()
