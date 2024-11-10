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
app.mount("/uploaded_images", StaticFiles(directory="uploaded_images"), name="uploaded_images")

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
        if image_path.is_file() and image_path.suffix.lower() in {'.png', '.jpg', '.jpeg', '.gif'}:
            relative_path = image_path.relative_to(UPLOAD_DIR).as_posix()
            images.append(relative_path)
    return templates.TemplateResponse("index.html", {"request": request, "images": images})


# Endpoint to handle the uploaded ZIP archive or folder
@app.post("/upload/")
async def upload_archive_or_folder(
        archive: UploadFile = File(None),
        images: list[UploadFile] = File(None)
):
    if archive and archive.filename.endswith('.zip'):
        # Handle ZIP archive upload
        try:
            temp_archive_path = TEMP_DIR / archive.filename
            async with aiofiles.open(temp_archive_path, 'wb') as out_file:
                content = await archive.read()
                await out_file.write(content)

            # Extract the archive to the UPLOAD_DIR
            with zipfile.ZipFile(temp_archive_path, 'r') as zip_ref:
                zip_ref.extractall(UPLOAD_DIR)

            # Clean up the temporary archive
            temp_archive_path.unlink()

            # Redirect to the settings page after successful upload
            return RedirectResponse(url="/settings/", status_code=303)

        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="Invalid ZIP file")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    elif images:
        # Handle folder upload (multiple image files with potential subdirectories)
        try:
            for image in images:
                if image.content_type.startswith('image/'):
                    # Extract the relative path
                    relative_path = Path(image.filename)
                    # Prevent directory traversal attacks
                    if ".." in relative_path.parts:
                        continue  # Skip invalid paths

                    image_path = UPLOAD_DIR / relative_path

                    # Create necessary subdirectories
                    image_path.parent.mkdir(parents=True, exist_ok=True)

                    # Prevent overwriting existing files by appending a counter
                    final_path = image_path
                    counter = 1
                    while final_path.exists():
                        final_path = image_path.with_name(f"{image_path.stem}_{counter}{image_path.suffix}")
                        counter += 1

                    # Save the uploaded image
                    async with aiofiles.open(final_path, 'wb') as out_file:
                        content = await image.read()
                        await out_file.write(content)
                else:
                    # Skip non-image files
                    continue

            # Redirect to the settings page after successful upload
            return RedirectResponse(url="/settings/", status_code=303)

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    else:
        raise HTTPException(status_code=400, detail="No valid files uploaded")


# Endpoint to display the settings page
@app.get("/settings/", response_class=HTMLResponse)
async def settings(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})


# Endpoint to process the images based on user input
@app.post("/process/")
async def process_images(
        body_percentage: int = Form(...),
        bbox_width: int = Form(...),
        bbox_height: int = Form(...),
        limb_points: int = Form(...)
):
    params = {
        "body_percentage": body_percentage,
        "bbox_width": bbox_width,
        "bbox_height": bbox_height,
        "limb_points": limb_points
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
    return templates.TemplateResponse("results.html", {"request": request, "results": results})


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
