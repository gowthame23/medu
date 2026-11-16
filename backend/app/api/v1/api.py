from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.families import router as families_router
from app.api.v1.family_bills import router as family_bills_router
from app.api.v1.personal_bills import router as personal_bills_router
from app.api.v1.daily_logs import router as daily_logs_router
from app.api.v1.loans import router as loans_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.payments import router as payments_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(families_router)
api_router.include_router(family_bills_router)
api_router.include_router(personal_bills_router)
api_router.include_router(daily_logs_router)
api_router.include_router(loans_router)
api_router.include_router(notifications_router)
api_router.include_router(payments_router)
