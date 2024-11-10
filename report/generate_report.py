import os
import json
from pathlib import Path
import matplotlib.pyplot as plt

def generate_report():
    BASE_DIR = Path(__file__).parent.parent  # Возможно, нужно скорректировать путь
    UPLOAD_DIR = BASE_DIR / "uploaded_images"
    STATIC_DIR = BASE_DIR / "static"

    with open(UPLOAD_DIR / "results.json", "r") as f:
        results = json.load(f)

    # Соотношение пустых и непустых изображений
    empty_counts = {
        'Пустые': sum(1 for r in results if r['is_empty'] == 0),
        'Непустые': sum(1 for r in results if r['is_empty'] == 1)
    }

    plt.figure(figsize=(6,6))
    plt.pie(empty_counts.values(), labels=empty_counts.keys(), autopct='%1.1f%%')
    plt.title('Соотношение пустых и непустых изображений')
    plt.savefig(STATIC_DIR / 'empty_vs_nonempty.png')
    plt.close()

    # Соотношение качественных и некачественных изображений
    quality_counts = {
        'Класс 0 (Некачественные)': sum(1 for r in results if r['is_empty'] == 0),
        'Класс 1 (Качественные)': sum(1 for r in results if r['is_empty'] == 1)
    }

    plt.figure(figsize=(6,6))
    plt.pie(quality_counts.values(), labels=quality_counts.keys(), autopct='%1.1f%%')
    plt.title('Соотношение качественных и некачественных изображений')
    plt.savefig(STATIC_DIR / 'quality_distribution.png')
    plt.close()
