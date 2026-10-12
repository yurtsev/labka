from fastapi import APIRouter

from src.api.announcements.router import router as announcements_router
from src.api.assignments.router import router as assignments_router
from src.api.auth.router import router as auth_router
from src.api.calendar.router import router as calendar_router
from src.api.courses.router import router as courses_router
from src.api.exams.router import router as exams_router
from src.api.feed.router import router as feed_router
from src.api.final_grades.router import router as final_grades_router
from src.api.home.router import router as home_router
from src.api.materials.router import router as materials_router
from src.api.notifications.router import router as notifications_router
from src.api.personal_tasks.router import router as personal_tasks_router
from src.api.profile.router import router as profile_router
from src.api.realtime.router import router as realtime_router
from src.api.reviews.router import router as reviews_router
from src.api.schedule.router import router as schedule_router
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
router.include_router(schedule_router)
router.include_router(personal_tasks_router)
router.include_router(calendar_router)
router.include_router(exams_router)
router.include_router(final_grades_router)
router.include_router(notifications_router)
router.include_router(realtime_router)
router.include_router(home_router)
