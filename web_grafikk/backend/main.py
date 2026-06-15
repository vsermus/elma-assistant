import os
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import DATA_DIR
from .core import ExcelGenerator
from .models import (
    LoginRequest, TokenResponse, UserInfo, ObjectInfo,
    ObjectSearchResult, CorpusList, GenerateRequest,
)
from .auth import create_token, get_current_user, require_admin
from .users import init_db, verify_user, add_user, list_users
from .scheduler import setup_scheduler, run_update

app = FastAPI(title="График витражей ELMA")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

generator = ExcelGenerator(str(DATA_DIR))


FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@app.on_event("startup")
async def startup():
    init_db()
    setup_scheduler(app)


# ---- Auth ----

@app.post("/api/auth/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    user = verify_user(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    token = create_token(user["username"], user["is_admin"])
    return TokenResponse(access_token=token)


@app.get("/api/me", response_model=UserInfo)
async def me(user: dict = Depends(get_current_user)):
    return UserInfo(username=user["username"], is_admin=user["is_admin"])


# ---- Objects ----

@app.get("/api/objects", response_model=ObjectSearchResult)
async def search_objects(q: str = Query("", min_length=0)):
    index = generator.build_object_index()
    items = list(index.values())
    q_lower = q.strip().lower()
    if q_lower:
        items = [
            o for o in items
            if q_lower in o["id"].lower() or q_lower in o["name"].lower()
        ]
    items.sort(key=lambda o: (o["name"], o["id"]))
    return ObjectSearchResult(
        objects=[ObjectInfo(id=o["id"], name=o["name"], address=o["address"]) for o in items]
    )


@app.get("/api/objects/{object_id}/korpuses", response_model=CorpusList)
async def get_korpuses(object_id: str):
    index = generator.build_object_index()
    obj = index.get(object_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Объект не найден")
    korps = sorted(k for k in obj["korpuses"] if k)
    return CorpusList(korpuses=korps)


# ---- Generate Excel ----

@app.post("/api/generate-excel")
async def generate_excel(req: GenerateRequest, user: dict = Depends(get_current_user)):
    try:
        buf, obj_name, obj_id, start, end, count = generator.generate(
            object_id=req.object_id,
            corpus_filter=req.korpuses,
            section_filter=req.section,
            start_date=req.start_date,
            end_date=req.end_date,
        )
        safe_id = obj_id.replace("/", "_").replace("\\", "_")
        filename = f"{safe_id}_Grafik_vitrazhey.xlsx"

        temp_dir = Path(__file__).resolve().parent / "temp"
        temp_dir.mkdir(exist_ok=True)
        temp_path = temp_dir / filename
        with open(temp_path, "wb") as f:
            f.write(buf.getvalue())

        return FileResponse(
            path=str(temp_path),
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---- Update data ----

@app.post("/api/update")
async def update_data(user: dict = Depends(require_admin)):
    success = run_update()
    if success:
        return {"success": True, "message": "Данные обновлены"}
    return JSONResponse(status_code=500, content={"success": False, "message": "Ошибка обновления данных"})


# ---- User management (admin) ----

@app.get("/api/users")
async def get_users(user: dict = Depends(require_admin)):
    return list_users()


@app.post("/api/users")
async def create_user(req: LoginRequest, user: dict = Depends(require_admin)):
    ok = add_user(req.username, req.password, is_admin=False)
    if not ok:
        raise HTTPException(status_code=409, detail="Пользователь уже существует")
    return {"success": True, "message": f"Пользователь {req.username} создан"}


# ---- Static frontend ----

if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
