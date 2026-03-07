from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import settings, hardware, models, chat, scraping, preprocessing, colab, training

app = FastAPI(title="Modelo SLM Local", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(hardware.router, prefix="/api/hardware", tags=["hardware"])
app.include_router(models.router, prefix="/api/models", tags=["models"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(scraping.router, prefix="/api/scraping", tags=["scraping"])
app.include_router(preprocessing.router, prefix="/api/preprocessing", tags=["preprocessing"])
app.include_router(colab.router, prefix="/api/colab", tags=["colab"])
app.include_router(training.router, prefix="/api/training", tags=["training"])


@app.get("/api/health")
async def health():
    return {"status": "ok"}
