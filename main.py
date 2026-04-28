"""Entry point: starts APScheduler + FastAPI webhook server on the same event loop."""
import asyncio
import json
import logging
import os
from datetime import datetime

import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request

load_dotenv()

from log import db as logdb
from integrations.smtp2go import verify_webhook_secret
from integrations import claude as claude_api
from program.vacations import VACATIONS
from program.dynamic import get_pre_vacation_alert_date
from jobs import run_morning_job, run_followup_job, run_sunday_summary, run_pre_vacation_email

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

TZ = os.getenv("TZ", "America/New_York")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8080"))

app = FastAPI()


@app.post("/inbound/{secret}")
async def inbound_webhook(secret: str, request: Request):
    if not verify_webhook_secret(secret):
        raise HTTPException(status_code=403, detail="Unauthorized")

    # SMTP2GO Inbound posts JSON
    body = await request.json()
    reply_text = body.get("text", "") or body.get("html", "")

    # headers is a dict: {"In-Reply-To": "<id@domain>", ...}
    headers = body.get("headers", {})
    raw_in_reply_to = headers.get("In-Reply-To", "") or headers.get("in-reply-to", "")
    message_id_header = raw_in_reply_to.strip().strip("<>")

    received_at = datetime.utcnow().isoformat()

    # Match to a day log by message ID
    matched_date = None
    if message_id_header:
        with logdb.get_conn() as conn:
            row = conn.execute(
                "SELECT date FROM day_log WHERE email_message_id=?",
                (message_id_header,),
            ).fetchone()
            if row:
                matched_date = row["date"]

    if not matched_date:
        # Fallback: most recent unlogged day
        with logdb.get_conn() as conn:
            row = conn.execute(
                "SELECT date FROM day_log WHERE reply_received_at IS NULL "
                "AND day_type != 'vacation' AND day_type != 'rest' "
                "ORDER BY date DESC LIMIT 1"
            ).fetchone()
            if row:
                matched_date = row["date"]
                logger.warning(f"Reply matched by recency fallback to {matched_date}.")

    if not matched_date:
        logger.warning("Could not match inbound reply to any day log.")
        return {"status": "unmatched"}

    from datetime import date as date_type
    d = date_type.fromisoformat(matched_date)

    parsed = claude_api.parse_reply(reply_text)

    logdb.upsert_day_log(
        d,
        reply_received_at=received_at,
        reply_raw=reply_text[:4000],
        reply_parsed=json.dumps(parsed),
        compliance=parsed.get("compliance"),
    )

    logger.info(f"Reply logged for {matched_date}: compliance={parsed.get('compliance')}")
    return {"status": "logged", "date": matched_date}


def _schedule_pre_vacation_emails(scheduler: AsyncIOScheduler) -> None:
    """Schedule pre-vacation emails dynamically at startup. Skip if date already passed."""
    from datetime import date
    today = date.today()
    for vac in VACATIONS:
        send_date = get_pre_vacation_alert_date(vac)
        if send_date < today:
            logger.info(f"Skipping pre-vacation email for {vac.name} — {send_date} already passed.")
            continue
        run_dt = datetime(send_date.year, send_date.month, send_date.day, 18, 0, 0)
        scheduler.add_job(
            run_pre_vacation_email,
            "date",
            run_date=run_dt,
            timezone=TZ,
            args=[vac.name],
            id=f"pre_vacation_{vac.name}",
            replace_existing=True,
        )
        logger.info(f"Scheduled pre-vacation email for {vac.name} on {send_date}.")


async def main():
    logdb.init_db()

    scheduler = AsyncIOScheduler(timezone=TZ)

    scheduler.add_job(run_morning_job, "cron", hour=6, minute=30, timezone=TZ, id="morning")
    scheduler.add_job(run_followup_job, "cron", hour=21, minute=0, timezone=TZ, id="followup")
    scheduler.add_job(
        run_sunday_summary, "cron", day_of_week="sun", hour=7, minute=0, timezone=TZ, id="sunday"
    )

    _schedule_pre_vacation_emails(scheduler)
    scheduler.start()

    config = uvicorn.Config(app, host="0.0.0.0", port=WEBHOOK_PORT, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
