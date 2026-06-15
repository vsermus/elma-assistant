from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
import os
import subprocess
from typing import List, Dict, Any

app = FastAPI()

# Allow CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Project paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_PATH = os.path.join(BASE_DIR, "config", "entities.json")
LOAD_SCRIPT = os.path.join(BASE_DIR, "scripts", "load", "load_data.py")

# Only these entities are allowed in the constructor
ALLOWED_ENTITIES = [
    "tender",
    "raboty_po_tenderu",
    "spravochnik_id",
    "_companies",
    "users",
    "statusy_rabot_po_tenderam"
]

# Basic translations for the constructor
# In a real scenario, these would be loaded from the shared translation utility
TRANSLATIONS = {
    "system": {
        "__id": "ID записи",
        "__createdBy": "Создано",
        "__updatedBy": "Обновлено",
    },
    "entities": {
        "tender": {
            "name": "Тендер",
            "zakazchik": "Заказчик",
            "id_proekta_1": "Объект",
        },
        "raboty_po_tenderu": {
            "name": "Работы по тендеру",
            "ploshad_m2": "Площадь, м²",
            "summa": "Сумма",
            "tender": "Тендер",
            "id_proekta_1": "Объект",
        },
        "spravochnik_id": {
            "name": "Объект строительства",
            "itogovyi_id": "Итоговый ID",
            "zakazchik": "Заказчик",
        },
        "users": {
            "name": "Пользователь",
            "fio": "ФИО",
        }
    }
}

@app.get("/api/entities")
async def get_entities():
    """Returns the list of allowed entities with descriptions from config/entities.json"""
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # Filter config to only include allowed entities
        filtered = [e for e in config if e['id'] in ALLOWED_ENTITIES]
        return filtered
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading config: {str(e)}")

@app.get("/api/data/{entity}")
async def get_data(entity: str):
    """Reads JSON data from data/ and strips API wrappers"""
    if entity not in ALLOWED_ENTITIES:
        raise HTTPException(status_code=403, detail="Entity not allowed in constructor")

    file_path = os.path.join(DATA_DIR, f"{entity}.json")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Data file for {entity} not found")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        # Strip wrappers
        # 1. result.result
        if isinstance(raw_data, dict) and "result" in raw_data:
            inner = raw_data["result"]
            if isinstance(inner, dict) and "result" in inner:
                return inner["result"]

        # 2. statusItems
        if isinstance(raw_data, dict) and "statusItems" in raw_data:
            return raw_data["statusItems"]

        # 3. items
        if isinstance(raw_data, dict) and "items" in raw_data:
            return raw_data["items"]

        # Fallback to raw data if it's already a list
        return raw_data if isinstance(raw_data, list) else []

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing data: {str(e)}")

@app.post("/api/update")
async def update_data():
    """Triggers the data loading script for all allowed entities"""
    try:
        # Run the load script for only allowed entities
        args = ["python", LOAD_SCRIPT] + ALLOWED_ENTITIES
        process = subprocess.run(args, capture_output=True, text=True, encoding='utf-8')

        if process.returncode != 0:
            return {"success": False, "error": process.stderr}

        return {"success": True, "message": "Data updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")

@app.get("/api/translations")
async def get_translations():
    """Returns the translation mappings"""
    return TRANSLATIONS

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
