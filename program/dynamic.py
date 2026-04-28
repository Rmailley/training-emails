"""Pure functions — take a date, return a value. No side effects."""
from datetime import date, timedelta
from typing import Optional

from program.schedule import get_week_number, get_phase, PROGRAM_START_DATE
from program.vacations import VACATIONS, Vacation


def get_friday_run_distance(d: date) -> float:
    """Phase 1: 5.0 mi (Week 1) → 7.0 mi (Week 8), +0.25/week, cap at 7."""
    week = get_week_number(d)
    dist = 5.0 + (week - 1) * 0.25
    return min(dist, 7.0)


def get_thursday_underwater_count(d: date) -> int:
    """Phase 1: starts at 2×25m, +1 per week, caps at 4×25m."""
    week = get_week_number(d)
    return min(2 + (week - 1), 4)


_P3_SATURDAY_DISTANCES = {
    21: 10.0, 22: 10.0,
    23: 10.5, 24: 10.5,
    25: 11.0, 26: 11.0,
    27: 11.5, 28: 11.5,
    29: 12.0, 30: 12.0,
    31: 12.5, 32: 12.5,
    33: 13.0, 34: 13.0,
    35: 13.1, 36: 13.1,
}


def get_saturday_run_distance_p3(d: date) -> float:
    week = get_week_number(d)
    return _P3_SATURDAY_DISTANCES.get(week, 13.1)


_P4_TAPER_DISTANCES = {
    37: 13.1, 38: 13.1, 39: 13.1, 40: 13.1,
    41: 13.1, 42: 13.1, 43: 13.1, 44: 13.1,
    45: 11.0,
    46: 10.0,
    47: 8.0,
    48: 8.0,
}


def get_saturday_taper_distance_p4(d: date) -> float:
    week = get_week_number(d)
    return _P4_TAPER_DISTANCES.get(week, 8.0)


def is_extended_hard_day(d: date) -> bool:
    """Phase 3 Saturday: once per month — first Saturday of each month in Phase 3."""
    if get_phase(d) != 3 or d.weekday() != 5:
        return False
    # First Saturday of the month
    first_day = d.replace(day=1)
    days_until_saturday = (5 - first_day.weekday()) % 7
    first_saturday = first_day + timedelta(days=days_until_saturday)
    return d == first_saturday


def get_wednesday_run_type(d: date) -> str:
    """Phase 2: odd weeks = tempo, even weeks = intervals."""
    week = get_week_number(d)
    return "tempo" if week % 2 == 1 else "intervals"


def get_saturday_type_p2(d: date) -> str:
    """Phase 2: odd weeks = swim, even weeks = run."""
    week = get_week_number(d)
    return "swim" if week % 2 == 1 else "run"


def get_saturday_long_swim_distance(d: date) -> int:
    """Phase 1: 1000m (Week 1) → 1500m (Week 8)."""
    week = get_week_number(d)
    if week >= 8:
        return 1500
    # Linear: 1000 at week 1, 1500 at week 8 → +500/7 per week
    return round(1000 + (week - 1) * 500 / 7)


def get_friday_run_type_p3(d: date) -> str:
    """Phase 3: shakeout if Saturday is 10+ miles, otherwise moderate."""
    sat = d + timedelta(days=1)
    return "shakeout" if get_saturday_run_distance_p3(sat) >= 10.0 else "moderate"


def get_p2_saturday_long_run_distance(d: date) -> float:
    """Phase 2 even-week Saturday long run distances."""
    week = get_week_number(d)
    distances = {10: 8.0, 12: 8.5, 14: 9.0, 16: 9.5, 18: 10.0, 20: 10.0}
    # For odd weeks in Phase 2 that end up here, fall back to nearest even
    if week in distances:
        return distances[week]
    # Nearest lower even week
    for w in sorted(distances.keys(), reverse=True):
        if week > w:
            return distances[w]
    return 8.0


def get_pre_vacation_alert_date(vacation: Vacation) -> date:
    return vacation.start_date - timedelta(days=1)


def weeks_until_vacation(d: date, vacation: Vacation) -> int:
    delta = (vacation.start_date - d).days
    return max(0, delta // 7)


def get_upcoming_vacation(d: date, within_days: int = 14) -> Optional[Vacation]:
    """Returns the next vacation if it starts within `within_days`."""
    for v in VACATIONS:
        delta = (v.start_date - d).days
        if 0 < delta <= within_days:
            return v
    return None
