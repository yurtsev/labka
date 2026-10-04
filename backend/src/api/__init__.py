from fastapi import APIRouter

from src.api.auth.router import router as auth_router
from src.api.courses.router import router as courses_router
from src.api.materials.router import router as materials_router
from src.api.profile.router import router as profile_router

router = APIRouter(prefix="/api")
router.include_router(auth_router)
router.include_router(courses_router)
router.include_router(materials_router)
router.include_router(profile_router)
