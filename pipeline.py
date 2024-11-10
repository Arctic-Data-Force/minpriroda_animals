# pipeline.py

import os
import json
import random
import plotly.graph_objects as go
import pandas as pd
from pathlib import Path


def process_images_pipeline(params):
    BASE_DIR = Path(__file__).parent
    UPLOAD_DIR = BASE_DIR / "uploaded_images"
    image_files = [
        f
        for f in UPLOAD_DIR.rglob("*")
        if f.is_file() and f.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif"}
    ]

    results = []

    for image_file in image_files:
        is_empty = random.choice([0, 1])  # 0 - пустое, 1 - непустое (содержит животное)
        bbox = None
        if is_empty == 1:
            image_width, image_height = (
                800,
                600,
            )  # Замените на реальные размеры изображения
            bbox_width = params["bbox_width"]
            bbox_height = params["bbox_height"]
            x = random.randint(0, image_width - bbox_width)
            y = random.randint(0, image_height - bbox_height)
            bbox = {"x": x, "y": y, "width": bbox_width, "height": bbox_height}

        # Добавляем запись с ключами 'filename', 'is_empty', и 'bbox' в results
        results.append(
            {
                "filename": str(image_file.relative_to(UPLOAD_DIR)),
                "is_empty": is_empty,
                "bbox": bbox,
            }
        )

    # Проверка: убедитесь, что каждый элемент в results имеет ключ 'is_empty'
    for result in results:
        if "is_empty" not in result:
            raise ValueError("Error: Missing 'is_empty' field in results")

    # Сохраняем результаты в JSON
    with open(UPLOAD_DIR / "results.json", "w") as f:
        json.dump(results, f)

    # Возвращаем results для дальнейшего использования
    return results


def create_plots(results, output_dir=None):
    # Преобразуем результаты в DataFrame
    df = pd.DataFrame(results)

    # Логируем содержимое DataFrame
    print("DataFrame Contents:")
    print(df)

    # Проверяем содержимое df и наличие 'is_empty'
    if "is_empty" not in df.columns:
        raise ValueError("Error: 'is_empty' column missing in DataFrame")
    # Проверка и замена None на 0 или 1 для 'is_empty'
    df["is_empty"] = (
        df["is_empty"].fillna(0).astype(int)
    )  # Заполняем None значением 0 и приводим к целочисленному типу

    # Теперь выполняем статистику
    empty_vs_nonempty = df["is_empty"].value_counts()

    fig1 = go.Figure(
        data=[
            go.Pie(
                labels=empty_vs_nonempty.index,
                values=empty_vs_nonempty.values,
                hole=0.3,
            )
        ]
    )
    fig1.update_layout(title="Соотношение пустых и непустых изображений")

    # Соотношение качественных и некачественных изображений
    quality_distribution = (
        df["is_empty"].value_counts().rename({0: "Не качественные", 1: "Качественные"})
    )
    fig2 = go.Figure(
        data=[go.Bar(x=quality_distribution.index, y=quality_distribution.values)]
    )
    fig2.update_layout(
        title="Соотношение качественных и некачественных изображений",
        xaxis_title="Тип",
        yaxis_title="Количество",
    )

    # Если указан output_dir, сохраняем графики
    if output_dir:
        save_plots(fig1, fig2, output_dir)

    return fig1, fig2


def save_plots(fig1, fig2, output_dir):
    try:
        # Создаем папку для сохранения графиков, если ее нет
        output_dir.mkdir(parents=True, exist_ok=True)

        # Сохраняем графики как HTML
        fig1.write_html(output_dir / "empty_vs_nonempty.html")
        fig2.write_html(output_dir / "quality_distribution.html")
        print(
            f"Saved 'empty_vs_nonempty.html' and 'quality_distribution.html' to {output_dir}"
        )

        # Проверяем, что файлы действительно были созданы
        if os.path.exists(output_dir / "empty_vs_nonempty.html") and os.path.exists(
            output_dir / "quality_distribution.html"
        ):
            print("Both files are successfully saved.")
        else:
            print("One or both files failed to save.")

    except Exception as e:
        print(f"Error during saving plots: {e}")
        raise
