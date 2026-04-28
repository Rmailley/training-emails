from datetime import date, timedelta
from enum import Enum
from typing import Optional
import os

from program.vacations import VACATIONS, Vacation

PROGRAM_START_DATE = date.fromisoformat(os.getenv("PROGRAM_START_DATE", "2025-04-28"))


class DayType(str, Enum):
    NORMAL = "normal"
    VACATION = "vacation"
    REENTRY_1 = "reentry_1"
    REENTRY_2 = "reentry_2"
    REENTRY_3 = "reentry_3"
    REST = "rest"


def get_week_number(d: date) -> int:
    """Week 1 = days 0-6 after program start. Returns 1-indexed."""
    delta = (d - PROGRAM_START_DATE).days
    if delta < 0:
        raise ValueError(f"{d} is before program start {PROGRAM_START_DATE}")
    return delta // 7 + 1


def get_phase(d: date) -> int:
    week = get_week_number(d)
    if week <= 8:
        return 1
    elif week <= 20:
        return 2
    elif week <= 36:
        return 3
    elif week <= 48:
        return 4
    else:
        return 5


PHASE_NAMES = {
    1: "Base Building",
    2: "Volume & Intensity",
    3: "High Performance",
    4: "Peak & Taper",
    5: "Final Week",
}

PHASE_COLORS = {
    1: "#4a9e4a",
    2: "#c8860a",
    3: "#c85a0a",
    4: "#b01a1a",
    5: "#8b0000",
}


def get_vacation(d: date) -> Optional[Vacation]:
    for v in VACATIONS:
        if v.start_date <= d <= v.end_date:
            return v
    return None


def get_reentry_day(d: date) -> Optional[tuple[Vacation, int]]:
    for v in VACATIONS:
        for i in range(1, v.reentry_days + 1):
            reentry_date = v.end_date + timedelta(days=i)
            if d == reentry_date:
                return (v, i)
    return None


def get_day_type(d: date) -> DayType:
    if d.weekday() == 6:  # Sunday
        # Sunday is rest unless it's a vacation or reentry day
        vac = get_vacation(d)
        if vac:
            return DayType.VACATION
        reentry = get_reentry_day(d)
        if reentry:
            _, day_num = reentry
            return DayType(f"reentry_{day_num}")
        return DayType.REST

    vac = get_vacation(d)
    if vac:
        return DayType.VACATION

    reentry = get_reentry_day(d)
    if reentry:
        _, day_num = reentry
        return DayType(f"reentry_{day_num}")

    return DayType.NORMAL


def is_vacation_day(d: date) -> bool:
    return get_day_type(d) == DayType.VACATION


def is_reentry_day(d: date) -> bool:
    return get_day_type(d) in (DayType.REENTRY_1, DayType.REENTRY_2, DayType.REENTRY_3)


def get_program_day(d: date) -> int:
    """0-indexed days since program start."""
    return (d - PROGRAM_START_DATE).days


def get_vacation_day_number(d: date) -> Optional[int]:
    """Returns 1-indexed day number within the vacation, or None."""
    vac = get_vacation(d)
    if vac:
        return (d - vac.start_date).days + 1
    return None


def get_vacation_total_days(vac: Vacation) -> int:
    return (vac.end_date - vac.start_date).days + 1
