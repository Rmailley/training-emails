"""Job functions called by the scheduler. Each is independently callable for testing."""
import json
import logging
from datetime import date, datetime

from program.schedule import (
    get_week_number, get_phase, get_day_type, get_vacation, get_reentry_day,
    DayType, PHASE_NAMES,
)
from program.sessions import get_session
from program.dynamic import get_upcoming_vacation
from program.vacations import VACATIONS

from integrations.whoop import get_whoop_data
from integrations.smtp2go import send_email
from integrations import claude as claude_api

from mailer.builder import (
    build_daily_email, build_vacation_email, build_reentry_email,
    build_sunday_summary, build_followup_email,
)

from log import db

logger = logging.getLogger(__name__)


def _session_to_dict(session) -> dict:
    import dataclasses
    return dataclasses.asdict(session)


def run_morning_job(d: date = None) -> None:
    d = d or date.today()
    day_type = get_day_type(d)
    week = get_week_number(d)
    phase = get_phase(d)

    if day_type == DayType.REST:
        logger.info(f"{d}: rest day — skipping morning job.")
        return

    # Check yesterday's compliance
    consecutive_missed = db.get_consecutive_missed_logs(d)

    # Pull Whoop data
    whoop = get_whoop_data(d)

    # Load last 7 days of training log for Claude context
    recent_rows = db.get_recent_logs(d, days=7)
    recent_logs = [dict(row) for row in recent_rows]

    # Get planned session
    session = get_session(d)
    session_dict = _session_to_dict(session)

    if day_type == DayType.VACATION:
        vac = get_vacation(d)
        coaching_note = claude_api.vacation_coaching_note(
            location=vac.location,
            mode=vac.mode,
            available=vac.available,
            dropped=vac.dropped,
            day_num=(d - vac.start_date).days + 1,
            total_days=(vac.end_date - vac.start_date).days + 1,
            whoop=whoop,
        )
        subject, html, text = build_vacation_email(d, vac, session, whoop, coaching_note)
        adjusted_session = None
        modification_made = False

    elif day_type in (DayType.REENTRY_1, DayType.REENTRY_2, DayType.REENTRY_3):
        result = get_reentry_day(d)
        vac, day_num = result
        coaching_note = session.morning[0].coaching_note if session.morning else None
        subject, html, text = build_reentry_email(d, vac, day_num, session, whoop)
        adjusted_session = None
        modification_made = False

    else:
        # Normal training day — ask Claude to adjust
        adjustment = claude_api.adjust_session(session_dict, whoop, recent_logs)
        adjusted_session = adjustment.get("adjusted_session")
        modification_made = adjustment.get("modification_made", False)
        coaching_note = adjustment.get("coaching_note")

        # Rebuild session from adjusted if modified
        if modification_made and adjusted_session:
            display_session = session  # keep original dataclass for template
        else:
            display_session = session

        subject, html, text = build_daily_email(d, display_session, whoop, coaching_note)

    message_id = send_email(subject, html, text)

    # Write to DB
    vac_name = get_vacation(d).name if day_type == DayType.VACATION else None
    reentry_result = get_reentry_day(d)
    if reentry_result:
        vac_name = reentry_result[0].name

    db.upsert_day_log(
        d,
        week_number=week,
        phase=phase,
        day_type=day_type.value,
        vacation_name=vac_name,
        planned_session=json.dumps(session_dict),
        adjusted_session=json.dumps(adjusted_session) if adjusted_session else None,
        modification_made=int(modification_made),
        coaching_note=coaching_note,
        whoop_recovery=whoop.recovery_score if whoop else None,
        whoop_hrv=whoop.hrv_ms if whoop else None,
        whoop_resting_hr=whoop.resting_hr if whoop else None,
        whoop_sleep_perf=whoop.sleep_performance if whoop else None,
        whoop_yesterday_strain=whoop.yesterday_strain if whoop else None,
        email_sent_at=datetime.utcnow().isoformat(),
        email_message_id=message_id,
        compliance="vacation_exempt" if day_type == DayType.VACATION else None,
    )


def run_followup_job(d: date = None) -> None:
    d = d or date.today()
    day_type = get_day_type(d)

    if day_type in (DayType.VACATION, DayType.REST):
        return

    row = db.get_day_log(d)
    if row is None:
        logger.warning(f"No day log found for {d} during followup check.")
        return

    if row["reply_received_at"] or row["followup_sent_at"]:
        return

    subject, html, text = build_followup_email(d)
    send_email(subject, html, text)
    db.upsert_day_log(d, followup_sent_at=datetime.utcnow().isoformat())
    logger.info(f"Follow-up sent for {d}.")


def run_sunday_summary(d: date = None) -> None:
    d = d or date.today()
    from datetime import timedelta

    week = get_week_number(d)
    phase = get_phase(d)
    monday = d - timedelta(days=6)

    compliance_stats = db.get_weekly_compliance(monday)

    # Check if this was a vacation week
    from program.dynamic import get_upcoming_vacation
    vacation_context = None
    for v in VACATIONS:
        if v.start_date <= d <= v.end_date or any(
            v.start_date <= (monday + timedelta(days=i)) <= v.end_date for i in range(7)
        ):
            vac_logs = [db.get_day_log(monday + timedelta(days=i)) for i in range(7)]
            vac_days = sum(1 for r in vac_logs if r and r["day_type"] == "vacation")
            if vac_days:
                vacation_context = (
                    f"You're in {v.location} — Week {week} of 52. "
                    f"{compliance_stats['compliant_days']} of {compliance_stats['total_days']} "
                    f"available training days logged so far this trip."
                )
            break

    recent_rows = db.get_recent_logs(d, days=7)
    recent_logs = [dict(row) for row in recent_rows]

    summary_text = claude_api.weekly_summary(
        compliance_stats=compliance_stats,
        logs=recent_logs,
        week_number=week,
        vacation_context=vacation_context,
    )

    upcoming_vac = get_upcoming_vacation(d, within_days=14)

    subject, html, text = build_sunday_summary(
        d=d,
        compliance_stats=compliance_stats,
        summary_text=summary_text,
        upcoming_vacation=upcoming_vac,
        vacation_context=vacation_context,
    )
    send_email(subject, html, text)
    logger.info(f"Sunday summary sent for week {week}.")


def run_pre_vacation_email(vacation_name: str) -> None:
    from program.vacations import VACATIONS
    from mailer.builder import build_pre_vacation_email

    vac = next((v for v in VACATIONS if v.name == vacation_name), None)
    if vac is None:
        logger.error(f"Vacation '{vacation_name}' not found.")
        return

    d = vac.start_date
    from datetime import timedelta
    send_date = d - timedelta(days=1)

    subject, html, text = build_pre_vacation_email(send_date, vac)
    send_email(subject, html, text)
    logger.info(f"Pre-vacation email sent for {vacation_name}.")
