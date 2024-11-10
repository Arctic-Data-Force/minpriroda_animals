from fastapi import FastAPI, File, UploadFile, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import os
import zipfile
import shutil
import aiofiles
from pathlib import Path
import json
import matplotlib.pyplot as plt

from pipeline import process_images_pipeline
from report.generate_report import generate_report

app = FastAPI()

# Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust as needed for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Template and static files configuration
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount(
    "/uploaded_images", StaticFiles(directory="uploaded_images"), name="uploaded_images"
)

# Define directories using pathlib for better path handling
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploaded_images"
TEMP_DIR = BASE_DIR / "temp"

# Ensure the upload and temp directories exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)


# Root endpoint to display the index page
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    images = []
    for image_path in UPLOAD_DIR.rglob("*"):
        if image_path.is_file() and image_path.suffix.lower() in {
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
        }:
            relative_path = image_path.relative_to(UPLOAD_DIR).as_posix()
            images.append(relative_path)
    return templates.TemplateResponse(
        "index.html", {"request": request, "images": images}
    )


# Endpoint to handle the uploaded ZIP archive or folder
# Endpoint to handle the uploaded ZIP archive or folder
@app.post("/upload/")
async def upload_archive_or_folder(
    files: list[UploadFile] = File(...),  # Используем одно поле для всех файлов
):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    # Разделяем файлы на архивы и изображения
    zip_files = [file for file in files if file.filename.endswith(".zip")]
    image_files = [file for file in files if file.content_type.startswith("image/")]

    # Если загружены только не изображения (ни архивов, ни изображений), возвращаем ошибку
    if not zip_files and not image_files:
        raise HTTPException(
            status_code=400, detail="Uploaded files are not images or valid archives"
        )

    # Обработка архивов
    if zip_files:
        for archive in zip_files:
            try:
                temp_archive_path = TEMP_DIR / archive.filename
                async with aiofiles.open(temp_archive_path, "wb") as out_file:
                    content = await archive.read()
                    await out_file.write(content)

                # Извлечение содержимого архива в UPLOAD_DIR
                with zipfile.ZipFile(temp_archive_path, "r") as zip_ref:
                    extracted_files = [
                        file
                        for file in zip_ref.namelist()
                        if file.lower().endswith((".png", ".jpg", ".jpeg", ".gif"))
                    ]
                    if not extracted_files:
                        continue  # Если в архиве нет изображений, пропускаем его
                    for file_name in extracted_files:
                        extracted_path = UPLOAD_DIR / Path(file_name).name
                        with zip_ref.open(file_name) as extracted_file:
                            async with aiofiles.open(extracted_path, "wb") as out_file:
                                content = await extracted_file.read()
                                await out_file.write(content)

                # Удаление временного архива
                temp_archive_path.unlink()

            except zipfile.BadZipFile:
                raise HTTPException(status_code=400, detail="Invalid ZIP file")
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

    # Обработка изображений, если они загружены как отдельные файлы
    if image_files:
        for image in image_files:
            try:
                if image.content_type.startswith("image/"):
                    file_name = Path(image.filename).name
                    image_path = UPLOAD_DIR / file_name

                    # Сохранение изображения
                    async with aiofiles.open(image_path, "wb") as out_file:
                        content = await image.read()
                        await out_file.write(content)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error saving image: {e}")

    return RedirectResponse(url="/settings/", status_code=303)


# Endpoint to display the settings page
@app.get("/settings/", response_class=HTMLResponse)
async def settings(request: Request):
    # Получаем список изображений из папки uploaded_images
    images = []
    for image_path in UPLOAD_DIR.rglob("*"):
        if image_path.is_file() and image_path.suffix.lower() in {
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
        }:
            relative_path = image_path.relative_to(UPLOAD_DIR).as_posix()
            images.append(relative_path)

    return templates.TemplateResponse(
        "settings.html", {"request": request, "images": images}
    )


# Endpoint to process the images based on user input
@app.post("/process/")
async def process_images(
    body_percentage: int = Form(...),
    bbox_width: int = Form(...),
    bbox_height: int = Form(...),
    limb_points: int = Form(...),
):
    params = {
        "body_percentage": body_percentage,
        "bbox_width": bbox_width,
        "bbox_height": bbox_height,
        "limb_points": limb_points,
    }

    try:
        process_images_pipeline(params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

    return RedirectResponse(url="/results/", status_code=303)


# Endpoint to display results
@app.get("/results/", response_class=HTMLResponse)
async def show_results(request: Request):
    UPLOAD_DIR = BASE_DIR / "uploaded_images"
    try:
        with open(UPLOAD_DIR / "results.json", "r") as f:
            results = json.load(f)
    except FileNotFoundError:
        results = []
    return templates.TemplateResponse(
        "results.html", {"request": request, "results": results}
    )


# Endpoint to display report
@app.get("/report/", response_class=HTMLResponse)
async def report(request: Request):
    generate_report()
    return templates.TemplateResponse("report.html", {"request": request})


# Endpoint to delete all uploaded images
@app.post("/delete_all/")
async def delete_all_images():
    try:
        shutil.rmtree(UPLOAD_DIR)
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        return JSONResponse(content={"detail": "All images deleted"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Run the application
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
