from fastapi import APIRouter
from .endpoints import auth, patients, clinical, system

api_router = APIRouter()

# Keep /auth prefix for login
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# No prefix for these as they contain various top-level paths like /patients, /alerts, /health, /query
api_router.include_router(patients.router, tags=["Patients"])
api_router.include_router(clinical.router, tags=["Clinical Insights"])
api_router.include_router(system.router, tags=["System Infrastructure"])
