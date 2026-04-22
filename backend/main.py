import warnings
warnings.filterwarnings("ignore")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import chat, training, ledger, auth_request

app = FastAPI(title="Training Manager API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(training.router)
app.include_router(ledger.router)
app.include_router(auth_request.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
