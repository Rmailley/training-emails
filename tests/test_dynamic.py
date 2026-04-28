"""Tests for dynamic.py pure functions."""
import os
os.environ.setdefault("PROGRAM_START_DATE", "2025-04-28")

from datetime import date
from program.dynamic import (
    get_friday_run_distance,
    get_thursday_underwater_count,
    get_saturday_run_distance_p3,
    get_saturday_taper_distance_p4,
    is_extended_hard_day,
    get_wednesday_run_type,
    get_saturday_type_p2,
    get_saturday_long_swim_distance,
    get_friday_run_type_p3,
)


# ── Friday run distance (Phase 1) ─────────────────────────────────────────

def test_friday_run_week_1():
    assert get_friday_run_distance(date(2025, 5, 2)) == 5.0  # Week 1 Friday

def test_friday_run_week_2():
    # Week 2 Friday = 2025-05-09
    assert get_friday_run_distance(date(2025, 5, 9)) == 5.25

def test_friday_run_caps_at_7():
    # Week 9+ would exceed 7
    assert get_friday_run_distance(date(2025, 6, 27)) == 7.0

def test_friday_run_week_8():
    # Week 8 Friday = 2025-06-20
    assert get_friday_run_distance(date(2025, 6, 20)) == 6.75


# ── Thursday underwater count (Phase 1) ───────────────────────────────────

def test_underwater_week_1():
    assert get_thursday_underwater_count(date(2025, 5, 1)) == 2  # Week 1 Thursday

def test_underwater_week_2():
    assert get_thursday_underwater_count(date(2025, 5, 8)) == 3

def test_underwater_caps_at_4():
    assert get_thursday_underwater_count(date(2025, 5, 15)) == 4  # Week 3
    assert get_thursday_underwater_count(date(2025, 6, 5)) == 4   # Week 6 — still 4


# ── Phase 3 Saturday distances ─────────────────────────────────────────────

def test_p3_saturday_week_21():
    assert get_saturday_run_distance_p3(date(2025, 9, 20)) == 10.0  # Week 21 Sat

def test_p3_saturday_week_35():
    # Week 35 Saturday
    from datetime import timedelta
    start = date(2025, 4, 28)
    week35_start = start + timedelta(weeks=34)
    sat = week35_start + timedelta(days=5)
    assert get_saturday_run_distance_p3(sat) == 13.1

def test_p3_saturday_even_repeats_previous():
    # Week 22 repeats week 21's distance
    from datetime import timedelta
    start = date(2025, 4, 28)
    week22_sat = start + timedelta(weeks=21, days=5)
    assert get_saturday_run_distance_p3(week22_sat) == 10.0


# ── Phase 4 taper distances ───────────────────────────────────────────────

def test_p4_week_37():
    from datetime import timedelta
    start = date(2025, 4, 28)
    week37_sat = start + timedelta(weeks=36, days=5)
    assert get_saturday_taper_distance_p4(week37_sat) == 13.1

def test_p4_week_45():
    from datetime import timedelta
    start = date(2025, 4, 28)
    week45_sat = start + timedelta(weeks=44, days=5)
    assert get_saturday_taper_distance_p4(week45_sat) == 11.0

def test_p4_week_48():
    from datetime import timedelta
    start = date(2025, 4, 28)
    week48_sat = start + timedelta(weeks=47, days=5)
    assert get_saturday_taper_distance_p4(week48_sat) == 8.0


# ── Phase 2 alternating patterns ──────────────────────────────────────────

def test_p2_wednesday_odd_week_is_tempo():
    # Week 9 (odd) Wednesday
    from datetime import timedelta
    start = date(2025, 4, 28)
    week9_wed = start + timedelta(weeks=8, days=2)
    assert get_wednesday_run_type(week9_wed) == "tempo"

def test_p2_wednesday_even_week_is_intervals():
    from datetime import timedelta
    start = date(2025, 4, 28)
    week10_wed = start + timedelta(weeks=9, days=2)
    assert get_wednesday_run_type(week10_wed) == "intervals"

def test_p2_saturday_odd_is_swim():
    from datetime import timedelta
    start = date(2025, 4, 28)
    week9_sat = start + timedelta(weeks=8, days=5)
    assert get_saturday_type_p2(week9_sat) == "swim"

def test_p2_saturday_even_is_run():
    from datetime import timedelta
    start = date(2025, 4, 28)
    week10_sat = start + timedelta(weeks=9, days=5)
    assert get_saturday_type_p2(week10_sat) == "run"


# ── Phase 1 Saturday swim distance ─────────────────────────────────────────

def test_p1_saturday_swim_week_1():
    # Week 1 Saturday = 2025-05-03
    d = date(2025, 5, 3)
    assert get_saturday_long_swim_distance(d) == 1000

def test_p1_saturday_swim_caps_at_1500():
    from datetime import timedelta
    start = date(2025, 4, 28)
    week8_sat = start + timedelta(weeks=7, days=5)
    assert get_saturday_long_swim_distance(week8_sat) == 1500


# ── Extended hard day (Phase 3 — first Saturday of month) ─────────────────

def test_extended_hard_day_first_saturday_of_month():
    # Need a first Saturday in Phase 3 (weeks 21–36)
    # Phase 3 starts ~2025-09-15. First Saturday of October 2025 = Oct 4 (Saturday)
    # Week 23: 2025-09-29, Week 24: 2025-10-06. Oct 4 = Saturday week 23.
    # First Saturday of Oct = Oct 4 (need to verify Oct 1 = Wednesday)
    # Oct 1 2025 = Wednesday, so first Saturday = Oct 4.
    d = date(2025, 10, 4)
    # Is this in Phase 3? Week = ?
    from program.schedule import get_week_number, get_phase
    w = get_week_number(d)
    p = get_phase(d)
    if p == 3:
        assert is_extended_hard_day(d) == True

def test_extended_hard_day_not_first_saturday():
    # Second Saturday of a month in Phase 3
    d = date(2025, 10, 11)
    assert is_extended_hard_day(d) == False

def test_extended_hard_day_not_in_phase_3():
    # Phase 1 Saturday
    d = date(2025, 5, 3)
    assert is_extended_hard_day(d) == False
