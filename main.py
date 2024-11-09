from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import os
from typing import List
from starlette.requests import Request

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploaded_images", StaticFiles(directory="uploaded_images"), name="uploaded_images")

UPLOAD_DIR = "uploaded_images"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    files = os.listdir(UPLOAD_DIR)
    images = [file for file in files if file.lower().endswith(('png', 'jpg', 'jpeg', 'gif'))]
    return templates.TemplateResponse("index.html", {"request": request, "images": images})

@app.post("/upload/")
async def upload_images(request: Request, files: List[UploadFile] = File(...)):
    for file in files:
        unique_filename = os.path.basename(file.filename)
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        os.makedirs(UPLOAD_DIR, exist_ok=True)  # Создаём директорию, если её нет
        
        # Сохраняем файл
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())

@app.get("/complete/", response_class=HTMLResponse)
async def complete(request: Request):
    return templates.TemplateResponse(request=request, name="upload_complete.html")


@app.post("/delete_all/")
async def delete_all_images():
    for filename in os.listdir(UPLOAD_DIR):
        file_path = os.path.join(UPLOAD_DIR, filename)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(f"Error: {e}")
    return {"detail": "All images deleted"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)