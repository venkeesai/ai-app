from __future__ import annotations

import io
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageOps
from pypdf import PdfReader

from app.config import settings

try:
    import pytesseract
except Exception:  # pragma: no cover - optional runtime dependency
    pytesseract = None


@dataclass
class OCRDocument:
    filename: str
    text: str
    notes: list[str]


class TamilOCRService:
    def __init__(self) -> None:
        if pytesseract and settings.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd

    def extract(self, filename: str, data: bytes) -> OCRDocument:
        suffix = Path(filename).suffix.lower()
        if suffix == ".pdf":
            return self._extract_pdf(filename, data)
        return self._extract_image(filename, data)

    def _extract_pdf(self, filename: str, data: bytes) -> OCRDocument:
        reader = PdfReader(io.BytesIO(data))
        chunks: list[str] = []
        notes = ["PDF upload detected."]
        for page_number, page in enumerate(reader.pages, start=1):
            page_text = (page.extract_text() or "").strip()
            if page_text:
                chunks.append(f"[Page {page_number}]\n{page_text}")
            else:
                notes.append(
                    f"Page {page_number} has no text layer. Install pdf2image + Poppler for scanned PDF OCR."
                )
        return OCRDocument(filename=filename, text="\n\n".join(chunks), notes=notes)

    def _extract_image(self, filename: str, data: bytes) -> OCRDocument:
        notes: list[str] = []
        if pytesseract is None:
            notes.append("pytesseract is unavailable; using placeholder OCR output.")
            return OCRDocument(filename=filename, text=self._placeholder_text(filename), notes=notes)

        try:
            image = Image.open(io.BytesIO(data)).convert("RGB")
            image = ImageOps.autocontrast(image)
            text = pytesseract.image_to_string(image, lang="tam+eng", config="--psm 3")
            text = self._cleanup_text(text)
            if not text:
                notes.append("OCR returned empty output; inserted placeholder sample article.")
                text = self._placeholder_text(filename)
            return OCRDocument(filename=filename, text=text, notes=notes)
        except Exception as exc:  # pragma: no cover - depends on system OCR installation
            notes.append(f"OCR fallback engaged because: {exc}")
            return OCRDocument(filename=filename, text=self._placeholder_text(filename), notes=notes)

    @staticmethod
    def _cleanup_text(text: str) -> str:
        text = text.replace("\x0c", " ")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def _placeholder_text(filename: str) -> str:
        return (
            f"{Path(filename).stem} முக்கியச் செய்தி\n"
            "சென்னை மாநகராட்சியின் புதிய மழைநீர் வடிகால் பணிகள் அடுத்த மாதம் தொடங்கும் என்று அதிகாரிகள் தெரிவித்தனர்.\n"
            "இந்த திட்டம் வடசென்னையில் வெள்ளப் பாதிப்பை குறைக்கும் என கூறப்படுகிறது.\n"
            "படம்: ஆய்வில் ஈடுபட்ட அதிகாரிகள்."
        )


def detect_layout_blocks(text: str) -> list[tuple[str, str]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []

    blocks: list[tuple[str, str]] = []
    headline = lines[0]
    blocks.append(("headline", headline))

    cursor = 1
    if cursor < len(lines) and len(lines[cursor].split()) <= 10:
        blocks.append(("subheading", lines[cursor]))
        cursor += 1

    for line in lines[cursor:]:
        lowered = line.lower()
        if lowered.startswith("படம்") or lowered.startswith("caption"):
            blocks.append(("caption", line))
        else:
            blocks.append(("body", line))
    return blocks


def collect_numeric_tokens(chunks: Iterable[str]) -> list[str]:
    joined = "\n".join(chunks)
    return re.findall(r"\b[\d,./:-]+\b", joined)
