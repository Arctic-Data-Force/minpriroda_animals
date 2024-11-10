import os
import json
import random
from pathlib import Path
import pandas as pd


def process_images_pipeline(params):
    BASE_DIR = Path(__file__).parent
    UPLOAD_DIR = BASE_DIR / "uploaded_images"
    image_files = [f for f in UPLOAD_DIR.rglob("*") if
                   f.is_file() and f.suffix.lower() in {'.png', '.jpg', '.jpeg', '.gif'}]

    results = []

    for image_file in image_files:
        # Классификация на пустые и непустые
        is_empty = random.choice([0, 1])  # 0 - пустое, 1 - непустое (содержит животное)

        bbox = None
        if is_empty == 1:
            # Генерируем случайный BBOX на основе параметров
            image_width, image_height = 800, 600  # Замените на реальные размеры изображения
            bbox_width = params['bbox_width']
            bbox_height = params['bbox_height']
            x = random.randint(0, image_width - bbox_width)
            y = random.randint(0, image_height - bbox_height)
            bbox = {
                "x": x,
                "y": y,
                "width": bbox_width,
                "height": bbox_height
            }

        results.append({
            "filename": str(image_file.relative_to(UPLOAD_DIR)),
            "is_empty": is_empty,
            "bbox": bbox
        })

    # Сохраняем результаты в JSON
    with open(UPLOAD_DIR / "results.json", "w") as f:
        json.dump(results, f)

    # Сохраняем результаты в CSV для скачивания
    df = pd.DataFrame(results)
    df.to_csv(UPLOAD_DIR / "submission.csv", index=False)
