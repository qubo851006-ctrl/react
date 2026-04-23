import warnings
warnings.filterwarnings("ignore")

import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from routers import chat, training, ledger, auth_request, ledger_merge

app = FastAPI(title="Training Manager API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(training.router)
app.include_router(ledger.router)
app.include_router(auth_request.router)
app.include_router(ledger_merge.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# 托管前端静态文件（生产模式）
_FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
if _FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(_FRONTEND_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        return FileResponse(str(_FRONTEND_DIST / "index.html"))
