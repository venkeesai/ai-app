from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.config import settings
from app.models import ArticleResult, BatchResponse, FormattingMode
from app.services.ocr import TamilOCRService
from app.services.pdf import PDFExportService
from app.services.translation import TranslationService


class NewsroomPipeline:
    def __init__(self) -> None:
        self.ocr = TamilOCRService()
        self.translation = TranslationService()
        self.pdf = PDFExportService()

    async def process_uploads(self, files: list[UploadFile], mode: FormattingMode) -> BatchResponse:
        articles: list[ArticleResult] = []
        for upload in files:
            data = await upload.read()
            article = self._process_single(upload.filename or "upload", data, mode)
            articles.append(article)

        pdf_name = f"newsroom_export_{uuid4().hex[:8]}.pdf"
        pdf_path = settings.export_dir / pdf_name
        self.pdf.export(articles, pdf_path)
        return BatchResponse(articles=articles, mode=mode, generated_pdf=f"/exports/{pdf_name}")

    def _process_single(self, filename: str, data: bytes, mode: FormattingMode) -> ArticleResult:
        ocr_document = self.ocr.extract(filename, data)
        translation = self.translation.translate_article(ocr_document.text, mode)
        image_path = self._store_asset(filename, data)
        return ArticleResult(
            filename=filename,
            mode=mode,
            raw_ocr_text=ocr_document.text,
            raw_translation=translation.raw_translation,
            refined_translation=translation.refined_translation,
            headline=translation.headline,
            subheading=translation.subheading,
            body_paragraphs=translation.body_paragraphs,
            captions=translation.captions,
            headline_options=translation.headline_options,
            fact_checks=translation.fact_checks,
            layout_blocks=translation.layout_blocks,
            diff_html=translation.diff_html,
            processing_notes=ocr_document.notes + translation.notes,
            metadata={"image_path": str(image_path) if image_path else None, "asset_url": f"/assets/{image_path.name}" if image_path else None},
        )

    def _store_asset(self, filename: str, data: bytes) -> Path | None:
        suffix = Path(filename).suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
            return None
        asset_name = f"{uuid4().hex[:10]}{suffix}"
        destination = settings.asset_dir / asset_name
        destination.write_bytes(data)
        return destination
