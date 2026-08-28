from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router

app = FastAPI(
    title="MFOSIS — Maritime Forensic Oil-Spill Intelligence System",
    description=(
        "Forensic attribution API: SAR oil-type classification, a physics-gate "
        "reliability filter, Lagrangian drift back-tracking, and AIS truth-gap "
        "(dark ship / spoofing) detection. Running in SIMULATION_MODE — see /api/health."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root():
    return {"name": "MFOSIS API", "docs": "/docs", "health": "/api/health"}
