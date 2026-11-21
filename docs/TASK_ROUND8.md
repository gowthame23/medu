# Round 8 — Daily check-in reminders (10:00 and 18:00)

**Scope: the `mend/` folder ONLY.** Do not touch any other project in the parent folder.
Do not edit applied Alembic revisions. Add a NEW revision only if a schema change is needed.

## Goal
Each Mend user gets two in-app reminders per day, in THEIR OWN timezone:
- 10:00 morning: "Plan your day: check Tomorrow's Radar and list what is due."
- 18:00 evening: "Time for your 30-second check-in: log today's spending."

Reminders appear in the existing notifications list (`/api/v1/notifications`) and as a banner or toast in the UI. No email or SMS in this round.

## Rules
1. Reuse what exists: `backend/app/jobs/scheduler.py` (APScheduler), `models/notification.py`, the outbox pattern, and the user's stored timezone on `User`.
2. Idempotent: one reminder per user per slot per local date. A scheduler restart or double run must NOT create duplicates (use a unique key such as user_id + slot + local_date).
3. Skip the evening reminder if the user already submitted today's daily log. Skip the morning one if the user turned it off.
4. User control: add per-user settings `reminder_morning_enabled`, `reminder_evening_enabled` (default true). Expose them on the users endpoints with validation.
5. Privacy: the message text must contain NO amounts, loan or liability info (the notification model already forbids loan info).
6. Time handling: store UTC, compute local time with `zoneinfo`. Handle DST and an invalid timezone string by falling back to `Asia/Kolkata`.
7. Frontend: a settings toggle for each reminder, and the notification shown in the existing UI. Use `src/lib/api.ts` for typed calls. No secrets in localStorage.
8. Money rules stay unchanged. No floats.

## Items
1. **Model and migration**: settings fields, a unique constraint for dedupe, a new Alembic revision. Drift test green.
2. **Scheduler job**: runs every 15 minutes, finds users whose local time passed 10:00 or 18:00 today and have no reminder for that slot yet, and creates the notifications.
3. **Endpoints**: read and update reminder settings.
4. **Frontend**: toggles plus display.
5. **Tests**: both slots fire at the right local time; two timezones; DST day; duplicate run creates one row; evening skipped after a log; disabled setting skips; invalid timezone fallback; no amounts in message text.
6. **Docs**: README section and a `session.md` entry.
7. **Report**: write `REPORT.md` with the raw pytest output, the NOT RUN list, and any open questions. Commit it last.

## Stop condition
Tell the user "REPORT.md is ready."
