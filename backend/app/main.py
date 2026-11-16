"""Entrada de la API. El interprete se agregara en las siguientes etapas."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes.health import router as health_router
from app.api.routes.devices import router as devices_router
from app.api.routes.semantic import router as semantic_router
from app.api.routes.intermediate import router as intermediate_router
from app.api.routes.runtime import router as runtime_router
from app.core.config import CORS_ORIGINS

app = FastAPI(title="SmartHome API", version="0.1.0", description="Infraestructura inicial del proyecto integrador")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(health_router)
app.include_router(devices_router)
app.include_router(semantic_router)
app.include_router(intermediate_router)
app.include_router(runtime_router)
