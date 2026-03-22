from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.models import FormattingMode, HealthResponse
from app.services.pipeline import NewsroomPipeline

app = FastAPI(title=settings.app_name)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/exports", StaticFiles(directory=str(settings.export_dir)), name="exports")
app.mount("/assets", StaticFiles(directory=str(settings.asset_dir)), name="assets")
templates = Jinja2Templates(directory="templates")
pipeline = NewsroomPipeline()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        name="index.html",
        request=request,
        context={
            "request": request,
            "app_name": settings.app_name,
            "default_mode": FormattingMode.STANDARD.value,
            "modes": [mode.value for mode in FormattingMode],
        },
    )


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        ocr_engine="pytesseract / placeholder fallback",
        translation_engine=settings.translation_model if settings.use_transformers else "heuristic",
    )


@app.post("/api/process")
async def process_articles(
    files: list[UploadFile] = File(...),
    mode: FormattingMode = Form(default=FormattingMode.STANDARD),
) -> JSONResponse:
    response = await pipeline.process_uploads(files, mode)
    return JSONResponse(response.model_dump())


@app.get("/exports/{filename}")
async def download_export(filename: str) -> FileResponse:
    file_path = settings.export_dir / Path(filename).name
    return FileResponse(file_path, media_type="application/pdf", filename=file_path.name)
