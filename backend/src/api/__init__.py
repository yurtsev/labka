from fastapi import APIRouter

from src.api.announcements.router import router as announcements_router
from src.api.assignments.router import router as assignments_router
from src.api.auth.router import router as auth_router
from src.api.courses.router import router as courses_router
from src.api.feed.router import router as feed_router
from src.api.materials.router import router as materials_router
from src.api.profile.router import router as profile_router
from src.api.reviews.router import router as reviews_router
from src.api.submissions.router import router as submissions_router

router = APIRouter(prefix="/api")
router.include_router(auth_router)
router.include_router(courses_router)
router.include_router(materials_router)
router.include_router(profile_router)
router.include_router(feed_router)
router.include_router(announcements_router)
router.include_router(assignments_router)
router.include_router(submissions_router)
router.include_router(reviews_router)
