import json
import logging
import os
import time
from typing import Optional

import anthropic

from log.models import WhoopData

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-20250514"
MAX_RETRIES = 2


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def _call_with_retry(system: str, user: str) -> Optional[str]:
    client = _client()
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return resp.content[0].text
        except anthropic.APIError as e:
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)
                logger.warning(f"Claude API retry {attempt + 1}: {e}")
            else:
                logger.error(f"Claude API failed after {MAX_RETRIES} retries: {e}")
                return None


def adjust_session(planned_session: dict, whoop: Optional[WhoopData], recent_logs: list) -> dict:
    """Adjust a normal training day session. Returns adjusted result or passthrough on failure."""
    system = (
        "You are a coaching assistant for a 52-week fitness program targeting pararescue-level fitness benchmarks.\n"
        "The athlete: former collegiate sailor, marathon runner, BJJ practitioner 3–4x/week, 193 lb on moderate "
        "body recomposition (full fuel on hard days, modest deficit on easy/rest days).\n"
        "Equipment: dumbbells to 50 lb, cable machine to 80 lb at home; Smith machine at work gym. Pool access most mornings.\n\n"
        "Review today's planned session with Whoop recovery data and recent training log.\n"
        'Return JSON:\n{\n  "adjusted_session": <session as written, modified only if genuinely warranted>,\n'
        '  "modification_made": bool,\n  "coaching_note": "1–3 sentences max",\n'
        '  "flag": null | "low_recovery" | "missed_log_streak" | "benchmark_check_due"\n}\n\n'
        "Only scale back if recovery < 40 or clear accumulated fatigue pattern.\n"
        "Do not modify for mild tiredness. If Whoop unavailable, proceed as planned."
    )

    whoop_str = (
        f"Recovery: {whoop.recovery_score}%, HRV: {whoop.hrv_ms}ms, "
        f"RHR: {whoop.resting_hr}bpm, Sleep: {whoop.sleep_performance}%, "
        f"Yesterday strain: {whoop.yesterday_strain}"
        if whoop else "Whoop data unavailable."
    )

    user = (
        f"Planned session:\n{json.dumps(planned_session, indent=2)}\n\n"
        f"Whoop: {whoop_str}\n\n"
        f"Recent logs (last 7 days):\n{json.dumps(recent_logs, indent=2)}"
    )

    result = _call_with_retry(system, user)
    if result is None:
        return {
            "adjusted_session": planned_session,
            "modification_made": False,
            "coaching_note": "Claude unavailable — sending planned session as-is.",
            "flag": None,
        }

    try:
        # Strip markdown code fences if present
        text = result.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning(f"Could not parse Claude session adjustment response: {result[:200]}")
        return {
            "adjusted_session": planned_session,
            "modification_made": False,
            "coaching_note": result[:300],
            "flag": None,
        }


def vacation_coaching_note(location: str, mode: str, available: list, dropped: list,
                            day_num: int, total_days: int, whoop: Optional[WhoopData]) -> str:
    system = (
        f"The athlete is currently on vacation in {location} — {mode} mode.\n"
        f"Available: {', '.join(available)}. Dropped: {', '.join(dropped)}.\n"
        f"Today is Day {day_num} of {total_days} of this trip.\n"
        f"Whoop recovery: {whoop.recovery_score if whoop else 'unavailable'}.\n\n"
        "Write a brief (2–3 sentence) coaching note appropriate for a vacation day.\n"
        "Tone: genuinely relaxed, no guilt, no 'you should be doing X.'\n"
        "If recovery is low, note it and suggest an easy day.\n"
        "If recovery is high and they're in maintain mode, suggest a morning run.\n"
        'Return JSON: {"coaching_note": "..."}'
    )
    result = _call_with_retry(system, "Write the coaching note.")
    if result is None:
        return "Enjoy the trip — move if it feels good, rest if it doesn't."
    try:
        text = result.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(text).get("coaching_note", result[:300])
    except Exception:
        return result[:300]


def parse_reply(reply_text: str) -> dict:
    """Parse a training log reply into structured data."""
    system = (
        "Parse this training log reply. Return JSON:\n"
        "{\n"
        '  "completed": ["swim", "strength_home", ...],\n'
        '  "skipped": [{"session": "bjj", "reason": "tired"}],\n'
        '  "feel": "great|good|okay|rough|terrible",\n'
        '  "injury_flags": [],\n'
        '  "notes": "any free text worth logging",\n'
        '  "compliance": "full|partial|none"\n'
        "}\n"
        'Be generous. "Did everything" = full. Vacation replies accepted freely.'
    )
    result = _call_with_retry(system, reply_text)
    if result is None:
        return {"completed": [], "skipped": [], "feel": None, "injury_flags": [],
                "notes": reply_text, "compliance": "partial"}
    try:
        text = result.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(text)
    except json.JSONDecodeError:
        return {"completed": [], "skipped": [], "feel": None, "injury_flags": [],
                "notes": reply_text, "compliance": "partial"}


def weekly_summary(compliance_stats: dict, logs: list, week_number: int,
                   vacation_context: Optional[str] = None) -> str:
    system = (
        "Write a brief weekly training summary (under 150 words).\n"
        "Include: what went well, what was missed and any pattern worth noting,\n"
        "one concrete focus for the coming week.\n"
        "If any days were vacation or reentry, acknowledge them without dwelling.\n"
        "Tone: direct and honest, not cheerleader-y. Plain paragraphs, no bullets, no headers."
    )
    vac_note = f"\nVacation context: {vacation_context}" if vacation_context else ""
    user = (
        f"Week {week_number} stats: {json.dumps(compliance_stats)}\n"
        f"Training logs: {json.dumps(logs, indent=2)}{vac_note}"
    )
    result = _call_with_retry(system, user)
    if result is None:
        rate = compliance_stats.get("rate")
        return f"Week {week_number} complete. Compliance: {rate:.0f}% — keep going." if rate else "Week complete."
    return result.strip()
