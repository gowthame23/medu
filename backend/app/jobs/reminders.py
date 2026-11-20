from datetime import datetime, time, timezone, date
from typing import Optional
import uuid
import zoneinfo
import logging
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.notification import Notification
from app.models.expense import DailyLog
from app.models.outbox import OutboxEvent

logger = logging.getLogger(__name__)

MORNING_MESSAGE = "Plan your day: check Tomorrow's Radar and list what is due."
MORNING_TITLE = "Plan Your Day"

EVENING_MESSAGE = "Time for your 30-second check-in: log today's spending."
EVENING_TITLE = "30-Second Check-in"

MORNING_TIME = time(10, 0)
EVENING_TIME = time(18, 0)


def resolve_user_timezone(tz_name: Optional[str]) -> zoneinfo.ZoneInfo:
    """
    Resolves IANA timezone string to a zoneinfo.ZoneInfo object.
    Falls back to 'Asia/Kolkata' if tz_name is invalid or None.
    """
    if not tz_name:
        return zoneinfo.ZoneInfo("Asia/Kolkata")
    try:
        return zoneinfo.ZoneInfo(tz_name)
    except Exception:
        return zoneinfo.ZoneInfo("Asia/Kolkata")


async def is_daily_log_submitted(session: AsyncSession, user_id: uuid.UUID, log_date: date) -> bool:
    """
    Checks if user has already submitted a daily log for the given local date.
    A log is considered submitted if it has category entries or notes.
    """
    query = (
        select(DailyLog)
        .options(selectinload(DailyLog.entries))
        .where(DailyLog.user_id == user_id, DailyLog.log_date == log_date)
    )
    res = await session.execute(query)
    log = res.scalar_one_or_none()
    if not log:
        return False
    return len(log.entries) > 0 or (log.notes is not None and log.notes.strip() != "")


async def process_daily_reminders(
    session: AsyncSession,
    now_utc: Optional[datetime] = None
) -> int:
    """
    Scans active users and generates in-app daily reminders (10:00 and 18:00)
    in each user's local timezone.
    Idempotent via dedupe_key and unique database constraints.
    Returns the count of new reminder notifications created.
    """
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
    elif now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)

    users_query = select(User).where(User.is_active == True)
    users_result = await session.execute(users_query)
    users = users_result.scalars().all()

    created_count = 0

    for user in users:
        user_tz = resolve_user_timezone(user.timezone)
        local_dt = now_utc.astimezone(user_tz)
        local_date = local_dt.date()
        local_time = local_dt.time()

        # Morning Slot: 10:00
        if local_time >= MORNING_TIME and user.reminder_morning_enabled:
            morning_dedupe = f"reminder:morning:{local_date.isoformat()}"
            # Check existing notification
            existing_morning = await session.execute(
                select(Notification.id).where(
                    Notification.user_id == user.id,
                    Notification.dedupe_key == morning_dedupe
                )
            )
            if existing_morning.scalar_one_or_none() is None:
                try:
                    async with session.begin_nested():
                        notif = Notification(
                            user_id=user.id,
                            type="REMINDER",
                            title=MORNING_TITLE,
                            message=MORNING_MESSAGE,
                            dedupe_key=morning_dedupe,
                            is_read=False
                        )
                        session.add(notif)
                        outbox = OutboxEvent(
                            event_type="DAILY_REMINDER",
                            aggregate_type="User",
                            aggregate_id=str(user.id),
                            payload={"slot": "morning", "local_date": local_date.isoformat()},
                            dedupe_key=f"outbox:{user.id}:{morning_dedupe}",
                            status="DELIVERED"
                        )
                        session.add(outbox)
                        await session.flush()
                        created_count += 1
                except IntegrityError:
                    # Idempotency safety: another worker or concurrent execution committed first
                    logger.debug(f"Duplicate morning reminder skipped for user {user.id}")

        # Evening Slot: 18:00
        if local_time >= EVENING_TIME and user.reminder_evening_enabled:
            evening_dedupe = f"reminder:evening:{local_date.isoformat()}"
            existing_evening = await session.execute(
                select(Notification.id).where(
                    Notification.user_id == user.id,
                    Notification.dedupe_key == evening_dedupe
                )
            )
            if existing_evening.scalar_one_or_none() is None:
                # Rule 3: Skip evening reminder if today's daily log was already submitted
                already_logged = await is_daily_log_submitted(session, user.id, local_date)
                if not already_logged:
                    try:
                        async with session.begin_nested():
                            notif = Notification(
                                user_id=user.id,
                                type="REMINDER",
                                title=EVENING_TITLE,
                                message=EVENING_MESSAGE,
                                dedupe_key=evening_dedupe,
                                is_read=False
                            )
                            session.add(notif)
                            outbox = OutboxEvent(
                                event_type="DAILY_REMINDER",
                                aggregate_type="User",
                                aggregate_id=str(user.id),
                                payload={"slot": "evening", "local_date": local_date.isoformat()},
                                dedupe_key=f"outbox:{user.id}:{evening_dedupe}",
                                status="DELIVERED"
                            )
                            session.add(outbox)
                            await session.flush()
                            created_count += 1
                    except IntegrityError:
                        logger.debug(f"Duplicate evening reminder skipped for user {user.id}")

    if created_count > 0:
        await session.commit()

    return created_count
