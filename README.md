# Tamil Newsroom Translator

A Python-first mobile and web application for journalist-grade Tamil-to-English newspaper translation. The app is built around a local-first FastAPI stack and is designed to turn Tamil newspaper images or PDFs into publication-ready English copy with newsroom formatting, headline suggestions, fact checks and PDF export.

## What this delivers

- **Multi-image upload** for JPG, PNG and PDF newspaper pages.
- **OCR and layout detection** to separate headlines, subheadings, body text and captions.
- **Context-aware editorial translation pipeline** with two formatting modes:
  - `standard` for neutral English newspaper copy
  - `indian_express` for sharper, concise editorial phrasing inspired by Indian daily newsrooms
- **Editing and review UI** with raw OCR, raw translation, refined translation and HTML diff view.
- **Headline generator** that proposes multiple news-ready headline variants.
- **Fact consistency checker** that tracks number/date preservation.
- **Smart PDF export** that places the original image on top and the polished English article below.
- **Offline-friendly architecture** that prefers local OCR and open-source NLP components. If transformer models are unavailable, the app gracefully falls back to a heuristic translation layer so the workflow still runs.

## Tech stack

- **Backend/UI host:** FastAPI + Jinja templates
- **OCR:** `pytesseract` with Tamil + English language packs
- **Document parsing:** `pypdf`
- **Translation:** Hugging Face `transformers` (`Helsinki-NLP/opus-mt-ta-en`) when available, with a heuristic fallback for offline/demo usage
- **PDF export:** `reportlab`
- **Testing:** `pytest`

## Project structure

```text
app/
  config.py               # environment-backed settings
  main.py                 # FastAPI routes and static mounts
  models.py               # API and article response models
  services/
    ocr.py                # OCR extraction + layout heuristics
    pipeline.py           # end-to-end upload processing
    pdf.py                # newsroom PDF generation
    translation.py        # translation, rewriting, fact checks, headline suggestions
static/
  styles.css              # newsroom-inspired responsive UI
templates/
  index.html              # upload/review/export interface
tests/
  test_translation_service.py
requirements.txt
```

## Run locally

### 1) Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Install OCR prerequisites

Install Tesseract and the Tamil language pack on the host system.

Example Ubuntu packages:

```bash
sudo apt-get install tesseract-ocr tesseract-ocr-tam
```

If Tesseract is not on your PATH, set:

```bash
export NEWSROOM_TESSERACT_CMD=/usr/bin/tesseract
```

### 3) Start the app

```bash
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## API endpoints

- `GET /` — responsive newsroom web app
- `GET /api/health` — service health check
- `POST /api/process` — upload one or more images/PDFs with `mode=standard|indian_express`
- `GET /exports/{filename}` — download merged PDF output

## Notes on production hardening

For a production newsroom deployment, the next steps would be:

1. Swap the heuristic fallback with a fully packaged Indic translation model stored locally.
2. Add Celery/RQ workers for large batch processing and mobile push notifications.
3. Persist jobs, drafts and article edits in PostgreSQL.
4. Add user authentication and role-based review workflows for editors/reporters.
5. Improve layout understanding with OCR bounding boxes and region segmentation.
6. Add named-entity verification against election, district and public records datasets.

## Product fit against your brief

This implementation is intentionally newsroom-oriented:

- It does **not** stop at literal OCR output.
- It rewrites the article into readable English copy.
- It supports editorial mode switching.
- It preserves article hierarchy and export formatting.
- It is built using **Python and open-source components**, with no paid API dependency.
