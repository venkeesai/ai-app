from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class FormattingMode(str, Enum):
    STANDARD = "standard"
    INDIAN_EXPRESS = "indian_express"


class LayoutBlock(BaseModel):
    kind: str
    tamil_text: str
    english_text: str | None = None


class HeadlineOption(BaseModel):
    title: str
    angle: str


class FactCheckItem(BaseModel):
    label: str
    source_value: str
    translated_value: str
    status: str


class ArticleResult(BaseModel):
    filename: str
    source_language: str = "ta"
    mode: FormattingMode
    raw_ocr_text: str
    raw_translation: str
    refined_translation: str
    headline: str
    subheading: str
    body_paragraphs: list[str]
    captions: list[str] = Field(default_factory=list)
    headline_options: list[HeadlineOption] = Field(default_factory=list)
    fact_checks: list[FactCheckItem] = Field(default_factory=list)
    layout_blocks: list[LayoutBlock] = Field(default_factory=list)
    diff_html: str = ""
    processing_notes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BatchResponse(BaseModel):
    articles: list[ArticleResult]
    mode: FormattingMode
    generated_pdf: str | None = None


class HealthResponse(BaseModel):
    status: str
    app_name: str
    ocr_engine: str
    translation_engine: str
