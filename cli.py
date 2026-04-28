"""CLI for testing and manual operations."""
import json
from datetime import date, datetime
from typing import Optional

import click
from dotenv import load_dotenv

load_dotenv()

from log import db as logdb
from program.schedule import get_week_number, get_phase, get_day_type, DayType, PHASE_NAMES
from program.sessions import get_session
from program.vacations import VACATIONS
from program.dynamic import get_pre_vacation_alert_date


def _parse_date(date_str: str) -> date:
    return date.fromisoformat(date_str)


@click.group()
def cli():
    """Training email system — manual operations and testing."""
    logdb.init_db()


@cli.command()
@click.option("--date", "date_str", required=True, help="Date in YYYY-MM-DD format.")
def preview(date_str: str):
    """Preview any day's email without sending."""
    d = _parse_date(date_str)
    day_type = get_day_type(d)
    week = get_week_number(d)
    phase = get_phase(d)
    session = get_session(d)

    click.echo(f"\n{'='*60}")
    click.echo(f"Date: {d.strftime('%A, %B %-d, %Y')}")
    click.echo(f"Week {week} · Phase {phase}: {PHASE_NAMES[phase]}")
    click.echo(f"Day type: {day_type.value}")
    click.echo(f"{'='*60}\n")

    for block in session.morning:
        click.echo(f"[Morning] {block.name} — {block.duration_min} min")
        for ex in block.exercises:
            parts = [f"  • {ex.description}"]
            if ex.sets:
                parts = [f"  • {ex.sets}× {ex.description}"]
            if ex.reps:
                parts[0] += f" × {ex.reps}"
            if ex.load:
                parts[0] += f" @ {ex.load}"
            if ex.note:
                parts[0] += f" [{ex.note}]"
            click.echo(parts[0])
        if block.coaching_note:
            click.echo(f"  → {block.coaching_note}")
        click.echo()

    if session.evening:
        for block in session.evening:
            click.echo(f"[Evening] {block.name} — {block.duration_min} min")
            if block.coaching_note:
                click.echo(f"  → {block.coaching_note}")
        click.echo()


@cli.group()
def send():
    """Send email commands."""
    pass


@send.command("now")
def send_now():
    """Send today's email immediately."""
    from jobs import run_morning_job
    run_morning_job()
    click.echo("Morning email sent.")


@send.command("date")
@click.option("--date", "date_str", required=True, help="Date in YYYY-MM-DD format.")
def send_date(date_str: str):
    """Send email for a specific date."""
    from jobs import run_morning_job
    d = _parse_date(date_str)
    run_morning_job(d)
    click.echo(f"Email sent for {d}.")


@cli.group("log")
def log_group():
    """Logging commands."""
    pass


@log_group.command("add")
@click.option("--date", "date_str", required=True)
@click.option("--reply", required=True, help="Reply text to parse and log.")
def log_add(date_str: str, reply: str):
    """Manually log a session reply for a date."""
    from integrations import claude as claude_api
    d = _parse_date(date_str)
    parsed = claude_api.parse_reply(reply)
    logdb.upsert_day_log(
        d,
        reply_received_at=datetime.utcnow().isoformat(),
        reply_raw=reply,
        reply_parsed=json.dumps(parsed),
        compliance=parsed.get("compliance"),
    )
    click.echo(f"Logged for {d}: compliance={parsed.get('compliance')}")
    click.echo(json.dumps(parsed, indent=2))


@log_group.command("show")
@click.option("--from", "from_str", required=True, help="Start date YYYY-MM-DD.")
@click.option("--to", "to_str", required=True, help="End date YYYY-MM-DD.")
def log_show(from_str: str, to_str: str):
    """Show training log for a date range."""
    from datetime import timedelta
    start = _parse_date(from_str)
    end = _parse_date(to_str)
    d = start
    while d <= end:
        row = logdb.get_day_log(d)
        if row:
            compliance = row["compliance"] or "—"
            reply_snippet = (row["reply_raw"] or "")[:60].replace("\n", " ")
            click.echo(f"{d}  [{row['day_type']:12}]  compliance={compliance:12}  {reply_snippet}")
        else:
            click.echo(f"{d}  [no record]")
        d += timedelta(days=1)


@cli.command()
@click.option("--weeks", default=4, help="Number of recent weeks to show.")
def stats(weeks: int):
    """Show compliance statistics for recent weeks."""
    from datetime import timedelta
    today = date.today()
    monday = today - timedelta(days=today.weekday())

    for i in range(weeks - 1, -1, -1):
        week_monday = monday - timedelta(weeks=i)
        week = get_week_number(week_monday)
        stats = logdb.get_weekly_compliance(week_monday)
        rate = stats["rate"]
        rate_str = f"{rate:.0f}%" if rate is not None else "N/A"
        vac_note = f"  ({stats['vacation_days']} vacation days excluded)" if stats["vacation_days"] else ""
        click.echo(
            f"Week {week:2d}  ({week_monday.strftime('%b %-d')})  "
            f"compliance={rate_str:5}  "
            f"{stats['compliant_days']}/{stats['total_days']} days{vac_note}"
        )


@cli.command()
@click.option("--date", "date_str", required=True)
@click.option("--pullups", type=int)
@click.option("--pushups", type=int)
@click.option("--situps", type=int)
@click.option("--run", "run_time", help="Time as MM:SS")
@click.option("--swim", "swim_time", help="Time as MM:SS")
@click.option("--notes", default="")
def benchmark(date_str: str, pullups: Optional[int], pushups: Optional[int],
               situps: Optional[int], run_time: Optional[str], swim_time: Optional[str], notes: str):
    """Log a benchmark session."""
    d = _parse_date(date_str)
    week = get_week_number(d)

    def time_to_seconds(t: Optional[str]) -> Optional[int]:
        if not t:
            return None
        parts = t.split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        return int(t)

    logdb.insert_benchmark(
        week_number=week,
        d=d,
        pullups=pullups,
        pushups_2min=pushups,
        situps_2min=situps,
        run_1_5mi_seconds=time_to_seconds(run_time),
        swim_500m_seconds=time_to_seconds(swim_time),
        notes=notes,
    )
    click.echo(f"Benchmark logged for {d} (Week {week}).")


@cli.command("benchmark-show")
def benchmark_show():
    """Show benchmark trend."""
    rows = logdb.get_benchmarks()
    if not rows:
        click.echo("No benchmarks logged yet.")
        return
    click.echo(f"\n{'Date':<12} {'Week':>4} {'Pull-ups':>8} {'Push-ups':>8} {'Sit-ups':>8} {'Run':>8} {'Swim':>8}")
    click.echo("─" * 60)
    for row in rows:
        def fmt_time(s):
            if s is None:
                return "—"
            return f"{s//60}:{s%60:02d}"
        click.echo(
            f"{row['date']:<12} {row['week_number']:>4} "
            f"{row['pullups'] or '—':>8} {row['pushups_2min'] or '—':>8} "
            f"{row['situps_2min'] or '—':>8} {fmt_time(row['run_1_5mi_seconds']):>8} "
            f"{fmt_time(row['swim_500m_seconds']):>8}"
        )


@cli.group()
def vacation():
    """Vacation management commands."""
    pass


@vacation.command("list")
def vacation_list():
    """List all vacations and reentry dates."""
    from datetime import timedelta
    for v in VACATIONS:
        reentry_start = v.end_date + timedelta(days=1)
        reentry_end = v.end_date + timedelta(days=v.reentry_days)
        click.echo(f"\n{v.name}")
        click.echo(f"  Location: {v.location}")
        click.echo(f"  Dates:    {v.start_date} → {v.end_date}  ({(v.end_date - v.start_date).days + 1} days)")
        click.echo(f"  Mode:     {v.mode}")
        click.echo(f"  Reentry:  {reentry_start} → {reentry_end}  ({v.reentry_days} days)")
        click.echo(f"  Pre-vac email: {get_pre_vacation_alert_date(v)}")


@vacation.command("preview")
@click.option("--name", required=True, help="Vacation name (e.g. Japan).")
def vacation_preview(name: str):
    """Preview vacation day email."""
    vac = next((v for v in VACATIONS if v.name.lower() == name.lower()), None)
    if not vac:
        click.echo(f"Vacation '{name}' not found.")
        return
    preview.callback(vac.start_date.isoformat())


if __name__ == "__main__":
    cli()
