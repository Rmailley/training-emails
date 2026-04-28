"""Tests for schedule.py — the most critical module."""
import os
os.environ.setdefault("PROGRAM_START_DATE", "2025-04-28")

from datetime import date
import pytest
from program.schedule import (
    get_week_number, get_phase, get_day_type, get_vacation, get_reentry_day,
    DayType, PHASE_NAMES,
)


# ── Week number ────────────────────────────────────────────────────────────

def test_week_1_start():
    assert get_week_number(date(2025, 4, 28)) == 1

def test_week_1_end():
    assert get_week_number(date(2025, 5, 4)) == 1

def test_week_2_start():
    assert get_week_number(date(2025, 5, 5)) == 2

def test_week_8_end():
    # Week 8: day 49-55, starts 2025-06-16
    assert get_week_number(date(2025, 6, 16)) == 8

def test_week_52_includes_final_days():
    # Week 52 starts day 357 = 2026-04-20
    assert get_week_number(date(2026, 4, 20)) == 52

def test_before_start_raises():
    with pytest.raises(ValueError):
        get_week_number(date(2025, 4, 27))


# ── Phase ──────────────────────────────────────────────────────────────────

def test_phase_1_week_1():
    assert get_phase(date(2025, 4, 28)) == 1

def test_phase_1_week_8():
    assert get_phase(date(2025, 6, 16)) == 1

def test_phase_2_week_9():
    # Week 9 starts 2025-06-23
    assert get_phase(date(2025, 6, 23)) == 2

def test_phase_2_week_20():
    # Week 20 starts 2025-09-08 — but Iceland ends 2025-09-13...
    # Week 20 = day 133-139 = 2025-09-08
    assert get_phase(date(2025, 9, 8)) == 2

def test_phase_3_week_21():
    # Week 21 = day 140 = 2025-09-15
    assert get_phase(date(2025, 9, 15)) == 3

def test_phase_4_week_37():
    # Week 37 = day 252 = 2026-01-05
    assert get_phase(date(2026, 1, 5)) == 4

def test_phase_5_week_49():
    # Week 49 = day 336 = 2026-03-30
    assert get_phase(date(2026, 3, 30)) == 5


# ── Day type — vacation ────────────────────────────────────────────────────

def test_nicaragua_start_is_vacation():
    assert get_day_type(date(2025, 5, 1)) == DayType.VACATION

def test_nicaragua_end_is_vacation():
    assert get_day_type(date(2025, 5, 5)) == DayType.VACATION

def test_day_before_nicaragua_is_normal():
    assert get_day_type(date(2025, 4, 30)) == DayType.NORMAL

def test_japan_start_is_vacation():
    assert get_day_type(date(2025, 7, 11)) == DayType.VACATION

def test_japan_end_is_vacation():
    assert get_day_type(date(2025, 7, 21)) == DayType.VACATION

def test_iceland_start_is_vacation():
    assert get_day_type(date(2025, 9, 4)) == DayType.VACATION

def test_iceland_end_is_vacation():
    assert get_day_type(date(2025, 9, 13)) == DayType.VACATION


# ── Reentry ────────────────────────────────────────────────────────────────

def test_nicaragua_reentry_day_1():
    # Nicaragua ends 5/5, reentry_days=2 → 5/6 is reentry day 1
    assert get_day_type(date(2025, 5, 6)) == DayType.REENTRY_1

def test_nicaragua_reentry_day_2():
    assert get_day_type(date(2025, 5, 7)) == DayType.REENTRY_2

def test_nicaragua_no_reentry_day_3():
    # Nicaragua has reentry_days=2, so day 3 should be NORMAL
    d = date(2025, 5, 8)
    assert get_day_type(d) == DayType.NORMAL

def test_japan_reentry_day_1():
    # Japan ends 7/21, reentry 7/22
    assert get_day_type(date(2025, 7, 22)) == DayType.REENTRY_1

def test_japan_reentry_day_3():
    assert get_day_type(date(2025, 7, 24)) == DayType.REENTRY_3

def test_japan_after_reentry_is_normal():
    assert get_day_type(date(2025, 7, 25)) == DayType.NORMAL

def test_iceland_reentry_day_3():
    # Iceland ends 9/13, reentry 9/14, 9/15, 9/16
    assert get_day_type(date(2025, 9, 16)) == DayType.REENTRY_3


# ── Rest / Sunday ──────────────────────────────────────────────────────────

def test_sunday_is_rest():
    # 2025-04-27 is a Sunday (before start, but day_type handles it differently)
    # Use a Sunday during the program
    # 2025-05-11 is a Sunday
    assert get_day_type(date(2025, 5, 11)) == DayType.REST

def test_vacation_sunday_is_vacation():
    # Japan 7/11 is a Friday. 7/13 is a Sunday → vacation
    assert get_day_type(date(2025, 7, 13)) == DayType.VACATION


# ── get_reentry_day returns correct vacation and number ────────────────────

def test_get_reentry_day_returns_vacation_and_number():
    result = get_reentry_day(date(2025, 7, 22))
    assert result is not None
    vac, day_num = result
    assert vac.name == "Japan"
    assert day_num == 1

def test_get_reentry_day_none_for_normal_day():
    assert get_reentry_day(date(2025, 5, 20)) is None


# ── get_vacation ───────────────────────────────────────────────────────────

def test_get_vacation_during_trip():
    vac = get_vacation(date(2025, 9, 10))
    assert vac is not None
    assert vac.name == "Iceland"

def test_get_vacation_outside_trip():
    assert get_vacation(date(2025, 6, 1)) is None
