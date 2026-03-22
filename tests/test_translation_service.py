from app.models import FormattingMode
from app.services.translation import TranslationService


def test_translation_service_generates_editorial_bundle() -> None:
    service = TranslationService()
    bundle = service.translate_article(
        "சென்னை முக்கியச் செய்தி\nமாநகராட்சி புதிய மழைநீர் வடிகால் பணிகள் அடுத்த மாதம் தொடங்கும் என்று அதிகாரிகள் தெரிவித்தனர்.",
        FormattingMode.INDIAN_EXPRESS,
    )

    assert bundle.headline
    assert bundle.body_paragraphs
    assert bundle.headline_options
    assert bundle.fact_checks
