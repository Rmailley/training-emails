import os
from datetime import date, timedelta
from typing import Optional

from jinja2 import Environment, FileSystemLoader

from program.schedule import (
    get_week_number, get_phase, get_day_type, get_vacation, get_reentry_day,
    DayType, PHASE_NAMES, PHASE_COLORS, get_vacation_day_number, get_vacation_total_days,
)
from program.sessions import DaySession, get_session
from program.vacations import Vacation
from log.models import WhoopData
from log import db

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")


def _env() -> Environment:
    return Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)


def _week_at_a_glance(d: date) -> list:
    """Returns 7 rows for the week containing d."""
    monday = d - timedelta(days=d.weekday())
    rows = []
    for i in range(7):
        day = monday + timedelta(days=i)
        row_log = db.get_day_log(day)
        compliance = row_log["compliance"] if row_log else None
        rows.append({
            "date": day,
            "weekday": day.strftime("%a"),
            "is_today": day == d,
            "compliance": compliance,
            "day_type": get_day_type(day).value,
        })
    return rows


def _whoop_color(score: Optional[int]) -> str:
    if score is None:
        return "#888888"
    if score >= 67:
        return "#4a9e4a"
    if score >= 34:
        return "#c8860a"
    return "#c85a0a"


def _compliance_banner(consecutive_missed: int) -> Optional[dict]:
    if consecutive_missed == 0:
        return None
    if consecutive_missed == 1:
        return {"level": "amber", "message": "No log received for yesterday."}
    if consecutive_missed == 2:
        return {"level": "amber-strong", "message": "2 days without a log."}
    return {
        "level": "red",
        "message": f"{consecutive_missed} days without a log. Adjustments based on assumed moderate load.",
    }


def build_daily_email(d: date, session: DaySession, whoop: Optional[WhoopData],
                       coaching_note: Optional[str]) -> tuple[str, str, str]:
    """Returns (subject, html_body, text_body)."""
    week = get_week_number(d)
    phase = get_phase(d)
    phase_name = PHASE_NAMES[phase]
    phase_color = PHASE_COLORS[phase]
    consecutive_missed = db.get_consecutive_missed_logs(d)
    banner = _compliance_banner(consecutive_missed)
    week_rows = _week_at_a_glance(d)

    subject = f"[Week {week} · Phase {phase}] {d.strftime('%A')} Training — {d.strftime('%B %-d')}"

    env = _env()
    tmpl = env.get_template("daily.html")
    html = tmpl.render(
        date=d,
        week=week,
        phase=phase,
        phase_name=phase_name,
        phase_color=phase_color,
        session=session,
        whoop=whoop,
        whoop_color=_whoop_color(whoop.recovery_score if whoop else None),
        coaching_note=coaching_note,
        banner=banner,
        week_rows=week_rows,
    )

    text = _daily_text(d, week, phase, phase_name, session, whoop, coaching_note, banner)
    return subject, html, text


def build_vacation_email(d: date, vac: Vacation, session: DaySession,
                          whoop: Optional[WhoopData], coaching_note: str) -> tuple[str, str, str]:
    day_num = (d - vac.start_date).days + 1
    total_days = (vac.end_date - vac.start_date).days + 1
    return_date = vac.end_date + timedelta(days=1)
    reentry_start = vac.end_date + timedelta(days=1)

    subject = f"[{vac.name} Day {day_num}] {d.strftime('%A')} — {d.strftime('%B %-d')}"

    env = _env()
    tmpl = env.get_template("vacation.html")
    html = tmpl.render(
        date=d,
        vac=vac,
        day_num=day_num,
        total_days=total_days,
        return_date=return_date,
        reentry_start=reentry_start,
        session=session,
        whoop=whoop,
        whoop_color=_whoop_color(whoop.recovery_score if whoop else None),
        coaching_note=coaching_note,
        week=get_week_number(d),
    )
    text = (
        f"{vac.name} Day {day_num} of {total_days} — {d.strftime('%A, %B %-d')}\n\n"
        f"{coaching_note}\n\n"
        f"{session.morning[0].exercises[0].description if session.morning else ''}\n\n"
        f"Back on {return_date.strftime('%B %-d')}. Reentry protocol starts then.\n\n"
        "Tell me what you did today — or just say 'rest day.' Either is fine."
    )
    return subject, html, text


def build_reentry_email(d: date, vac: Vacation, day_num: int, session: DaySession,
                         whoop: Optional[WhoopData]) -> tuple[str, str, str]:
    subject = f"[Back from {vac.name}] Reentry Day {day_num} of {vac.reentry_days}"

    env = _env()
    tmpl = env.get_template("reentry.html")
    full_resume = d + timedelta(days=(vac.reentry_days - day_num))

    coaching_note = session.morning[0].coaching_note if session.morning else ""

    html = tmpl.render(
        date=d,
        vac=vac,
        day_num=day_num,
        full_resume=full_resume,
        session=session,
        whoop=whoop,
        whoop_color=_whoop_color(whoop.recovery_score if whoop else None),
        coaching_note=coaching_note,
        week=get_week_number(d),
    )
    text = (
        f"Back from {vac.name} — Reentry Day {day_num} of {vac.reentry_days}\n\n"
        f"{coaching_note}\n\n"
        f"Full program resumes {full_resume.strftime('%A, %B %-d')}.\n\n"
        "Reply to log today's session."
    )
    return subject, html, text


def build_pre_vacation_email(d: date, vac: Vacation) -> tuple[str, str, str]:
    week = get_week_number(d)
    subject = f"[{vac.name} starts tomorrow] What to expect"

    is_iceland = vac.name == "Iceland"
    benchmark_flag = (
        "Before you leave tomorrow: Week 16 benchmark test should be done this week if you haven't already. "
        "This is your Phase 2 checkpoint — pull-ups, push-ups, sit-ups, 1.5-mile run, 500m swim in sequence. "
        "Log it before you go."
        if is_iceland else None
    )

    reentry_start = vac.end_date + timedelta(days=1)

    env = _env()
    tmpl = env.get_template("pre_vacation.html")
    html = tmpl.render(
        date=d,
        vac=vac,
        week=week,
        benchmark_flag=benchmark_flag,
        reentry_start=reentry_start,
    )
    text = (
        f"{vac.name} starts tomorrow — Week {week}\n\n"
        f"Mode: {vac.mode}. Available: {', '.join(vac.available)}.\n"
        f"Dropped: {', '.join(vac.dropped)}.\n\n"
        f"{vac.notes}\n\n"
        + (f"{benchmark_flag}\n\n" if benchmark_flag else "")
        + f"Reentry protocol starts {reentry_start.strftime('%B %-d')} — {vac.reentry_days} easy days before full program.\n\n"
        "You don't need to feel guilty about anything you miss on this trip."
    )
    return subject, html, text


def build_sunday_summary(d: date, compliance_stats: dict, summary_text: str,
                          upcoming_vacation: Optional[Vacation] = None,
                          vacation_context: Optional[str] = None) -> tuple[str, str, str]:
    week = get_week_number(d)
    phase = get_phase(d)
    subject = f"[Week {week} recap + Week {week + 1} preview] Sunday"

    # Build week-ahead rows
    next_monday = d + timedelta(days=1)
    week_ahead = []
    for i in range(7):
        day = next_monday + timedelta(days=i)
        week_ahead.append({
            "date": day,
            "weekday": day.strftime("%a"),
            "day_type": get_day_type(day).value,
        })

    env = _env()
    tmpl = env.get_template("sunday.html")
    html = tmpl.render(
        date=d,
        week=week,
        phase=phase,
        phase_name=PHASE_NAMES[phase],
        phase_color=PHASE_COLORS[phase],
        compliance_stats=compliance_stats,
        summary_text=summary_text,
        week_ahead=week_ahead,
        upcoming_vacation=upcoming_vacation,
        vacation_context=vacation_context,
    )
    rate = compliance_stats.get("rate")
    rate_str = f"{rate:.0f}%" if rate is not None else "N/A"
    text = (
        f"Week {week} recap — {d.strftime('%B %-d')}\n\n"
        f"Compliance: {rate_str} ({compliance_stats.get('compliant_days', 0)}/{compliance_stats.get('total_days', 0)} days)\n\n"
        f"{summary_text}"
    )
    return subject, html, text


def build_followup_email(d: date) -> tuple[str, str, str]:
    week = get_week_number(d)
    subject = f"Log today's session — Week {week} {d.strftime('%A')}"
    html = (
        f"<p>No log received for today's session.</p>"
        f"<p>Reply to this morning's email — even one word is enough.</p>"
    )
    text = "No log received. Reply to this morning's email — even one word is enough."
    return subject, html, text


# ── Plain-text fallback ───────────────────────────────────────────────────────

def _daily_text(d, week, phase, phase_name, session, whoop, coaching_note, banner) -> str:
    lines = [
        f"Week {week} · Phase {phase}: {phase_name} — {d.strftime('%A, %B %-d')}",
        "",
    ]
    if banner:
        lines += [f"⚠ {banner['message']}", ""]
    if whoop:
        lines += [
            f"Recovery: {whoop.recovery_score}% · HRV: {whoop.hrv_ms}ms · Sleep: {whoop.sleep_performance}%",
            "",
        ]
    if coaching_note:
        lines += [coaching_note, ""]
    lines.append("── MORNING ──")
    for block in session.morning:
        lines.append(f"\n{block.name} ({block.duration_min} min)")
        for ex in block.exercises:
            note = f" [{ex.note}]" if ex.note else ""
            load = f" @ {ex.load}" if ex.load else ""
            reps = f" × {ex.reps}" if ex.reps else ""
            sets = f"{ex.sets}×" if ex.sets else ""
            lines.append(f"  • {sets}{ex.description}{reps}{load}{note}")
    if session.evening:
        lines.append("\n── EVENING ──")
        for block in session.evening:
            lines.append(f"\n{block.name} ({block.duration_min} min)")
            if block.coaching_note:
                lines.append(f"  {block.coaching_note}")
    lines += [
        "",
        "─────────────────────────────────",
        "Log your session by replying to this email. Any format works.",
        f"Week {week} of 52 · Phase {phase}: {phase_name}",
    ]
    return "\n".join(lines)
