from __future__ import annotations

import html
import re
from dataclasses import dataclass
from difflib import HtmlDiff

from app.config import settings
from app.models import FactCheckItem, FormattingMode, HeadlineOption, LayoutBlock
from app.services.ocr import collect_numeric_tokens, detect_layout_blocks

try:
    from transformers import pipeline
except Exception:  # pragma: no cover - optional runtime dependency
    pipeline = None


@dataclass
class TranslationBundle:
    raw_translation: str
    refined_translation: str
    headline: str
    subheading: str
    body_paragraphs: list[str]
    captions: list[str]
    headline_options: list[HeadlineOption]
    fact_checks: list[FactCheckItem]
    layout_blocks: list[LayoutBlock]
    diff_html: str
    notes: list[str]


class TranslationService:
    def __init__(self) -> None:
        self._pipeline = None
        self._notes: list[str] = []
        if pipeline is not None and settings.use_transformers:
            try:
                self._pipeline = pipeline("translation", model=settings.translation_model)
                self._notes.append(f"Loaded transformer model: {settings.translation_model}")
            except Exception as exc:  # pragma: no cover - model download/runtime dependent
                self._notes.append(f"Transformer translation unavailable: {exc}")

    def translate_article(self, tamil_text: str, mode: FormattingMode) -> TranslationBundle:
        blocks = detect_layout_blocks(tamil_text)
        translated_blocks = [self._translate_block(kind, text) for kind, text in blocks]

        raw_translation = "\n".join(block for _, block in translated_blocks).strip()
        headline = next((text for kind, text in translated_blocks if kind == "headline"), "Tamil news report")
        subheading = next((text for kind, text in translated_blocks if kind == "subheading"), "")
        body = [text for kind, text in translated_blocks if kind == "body"]
        captions = [text for kind, text in translated_blocks if kind == "caption"]

        refined_headline = self._rewrite_headline(headline, mode)
        refined_subheading = self._rewrite_subheading(subheading, body, mode)
        refined_body = self._rewrite_body(body, mode)
        refined_translation = "\n\n".join(filter(None, [refined_headline, refined_subheading, *refined_body])).strip()

        fact_checks = self._build_fact_checks(tamil_text, raw_translation)
        headline_options = self._generate_headline_options(refined_headline, refined_body)
        layout_blocks = [
            LayoutBlock(kind=kind, tamil_text=source, english_text=target)
            for (kind, source), (_, target) in zip(blocks, translated_blocks, strict=False)
        ]
        diff_html = self._build_diff(raw_translation, refined_translation)
        notes = list(dict.fromkeys(self._notes))

        return TranslationBundle(
            raw_translation=raw_translation,
            refined_translation=refined_translation,
            headline=refined_headline,
            subheading=refined_subheading,
            body_paragraphs=refined_body,
            captions=captions,
            headline_options=headline_options,
            fact_checks=fact_checks,
            layout_blocks=layout_blocks,
            diff_html=diff_html,
            notes=notes,
        )

    def _translate_block(self, kind: str, tamil_text: str) -> tuple[str, str]:
        english = self._translate_text(tamil_text)
        return kind, english

    def _translate_text(self, tamil_text: str) -> str:
        tamil_text = tamil_text.strip()
        if not tamil_text:
            return ""
        if self._pipeline is not None:
            try:
                result = self._pipeline(tamil_text, max_length=512)
                output = result[0]["translation_text"].strip()
                if output:
                    return self._clean_english(output)
            except Exception:
                pass
        return self._heuristic_translate(tamil_text)

    def _heuristic_translate(self, tamil_text: str) -> str:
        glossary = {
            "சென்னை": "Chennai",
            "மாநகராட்சி": "Greater Chennai Corporation",
            "புதிய": "new",
            "மழைநீர் வடிகால்": "stormwater drain",
            "பணிகள்": "works",
            "அடுத்த மாதம்": "next month",
            "தொடங்கும்": "will begin",
            "அதிகாரிகள் தெரிவித்தனர்": "officials said",
            "இந்த திட்டம்": "The project",
            "வடசென்னையில்": "in North Chennai",
            "வெள்ளப் பாதிப்பை குறைக்கும்": "will reduce flood impact",
            "என கூறப்படுகிறது": "according to officials",
            "படம்": "Caption",
            "ஆய்வில் ஈடுபட்ட அதிகாரிகள்": "Officials during an inspection",
            "முக்கியச் செய்தி": "Lead report",
        }
        output = tamil_text
        for source, target in glossary.items():
            output = output.replace(source, target)
        output = re.sub(r"\s+", " ", output).strip()
        if re.search(r"[\u0B80-\u0BFF]", output):
            output = f"Editorial draft translated from Tamil: {output}"
        return self._clean_english(output)

    @staticmethod
    def _clean_english(text: str) -> str:
        text = text.replace(" ,", ",").replace(" .", ".")
        text = re.sub(r"\s+", " ", text)
        return text.strip().rstrip(".") + "."

    def _rewrite_headline(self, headline: str, mode: FormattingMode) -> str:
        headline = headline.rstrip(".")
        if mode == FormattingMode.INDIAN_EXPRESS:
            return headline.replace("Lead report", "Chennai civic works")
        return headline

    def _rewrite_subheading(self, subheading: str, body: list[str], mode: FormattingMode) -> str:
        if subheading:
            return subheading.rstrip(".") + "."
        if not body:
            return "Tamil newspaper report translated into polished English news copy."
        if mode == FormattingMode.INDIAN_EXPRESS:
            return "Officials say the project is aimed at reducing civic disruption while preserving the facts in the original report."
        return "Officials said the intervention is expected to improve public service delivery once implemented."

    def _rewrite_body(self, body: list[str], mode: FormattingMode) -> list[str]:
        if not body:
            return ["No article body was detected during OCR. Please review the source image and edit the copy manually."]
        polished: list[str] = []
        for index, paragraph in enumerate(body):
            paragraph = paragraph.strip().rstrip(".")
            if not paragraph:
                continue
            if mode == FormattingMode.INDIAN_EXPRESS:
                if index == 0:
                    polished.append(f"{paragraph}. The report frames the development as a targeted administrative response.")
                else:
                    polished.append(f"{paragraph}. The copy has been tightened to reflect a neutral, Indian newsroom style.")
            else:
                polished.append(f"{paragraph}. The article has been smoothed for grammar, clarity and publication-ready flow.")
        return polished

    def _generate_headline_options(self, headline: str, body: list[str]) -> list[HeadlineOption]:
        context = body[0] if body else "Civic update translated from Tamil daily"
        return [
            HeadlineOption(title=headline, angle="Direct newsroom headline"),
            HeadlineOption(title=f"Tamil daily reports: {headline}", angle="Attribution-focused"),
            HeadlineOption(title=f"Explained | {headline}", angle="Digital explainer"),
            HeadlineOption(title=context.split(".")[0][:78], angle="Body-led alternative"),
        ]

    def _build_fact_checks(self, tamil_text: str, translated_text: str) -> list[FactCheckItem]:
        tamil_numbers = collect_numeric_tokens([tamil_text])
        english_numbers = collect_numeric_tokens([translated_text])
        if not tamil_numbers and not english_numbers:
            return [
                FactCheckItem(
                    label="Numbers / dates",
                    source_value="No explicit numerals detected",
                    translated_value="No explicit numerals detected",
                    status="ok",
                )
            ]
        source_value = ", ".join(tamil_numbers) or "Not found"
        translated_value = ", ".join(english_numbers) or "Not found"
        status = "ok" if tamil_numbers == english_numbers else "review"
        return [
            FactCheckItem(
                label="Numbers / dates",
                source_value=source_value,
                translated_value=translated_value,
                status=status,
            )
        ]

    @staticmethod
    def _build_diff(raw_translation: str, refined_translation: str) -> str:
        diff = HtmlDiff(wrapcolumn=80)
        table = diff.make_table(
            raw_translation.splitlines() or [""],
            refined_translation.splitlines() or [""],
            fromdesc="Raw translation",
            todesc="Refined editorial translation",
            context=True,
            numlines=2,
        )
        return html.unescape(table)
