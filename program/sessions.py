from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

from program.schedule import (
    get_week_number, get_phase, get_day_type, get_vacation, get_reentry_day,
    DayType, get_vacation_day_number, get_vacation_total_days,
)
from program.dynamic import (
    get_friday_run_distance, get_thursday_underwater_count,
    get_saturday_run_distance_p3, get_saturday_taper_distance_p4,
    is_extended_hard_day, get_wednesday_run_type, get_saturday_type_p2,
    get_saturday_long_swim_distance, get_friday_run_type_p3,
    get_p2_saturday_long_run_distance,
)
from program.vacations import Vacation


@dataclass
class Exercise:
    description: str
    sets: Optional[int] = None
    reps: Optional[str] = None
    load: Optional[str] = None
    note: Optional[str] = None


@dataclass
class SessionBlock:
    name: str
    session_type: str
    duration_min: int
    exercises: List[Exercise] = field(default_factory=list)
    coaching_note: Optional[str] = None


@dataclass
class DaySession:
    morning: List[SessionBlock]
    evening: List[SessionBlock]
    bjj_available: bool
    total_duration_min: int
    day_type: str


def _bjj_block(style: str) -> SessionBlock:
    return SessionBlock(
        name=f"{style} BJJ",
        session_type="bjj",
        duration_min=90,
        coaching_note="Optional — train if you have the energy.",
    )


# ── Phase 1 ─────────────────────────────────────────────────────────────────

def _p1_monday() -> DaySession:
    swim = SessionBlock(
        name="Swim",
        session_type="swim",
        duration_min=45,
        exercises=[
            Exercise("500m continuous freestyle"),
            Exercise("8×50m", sets=8, reps="50m", load="30s rest"),
            Exercise("2×25m underwater", sets=2, reps="25m", note="Buddy required — noted every time"),
            Exercise("500m easy cool-down"),
        ],
    )
    strength = SessionBlock(
        name="Home Strength",
        session_type="strength_home",
        duration_min=45,
        exercises=[
            Exercise("Cable pull-down", sets=4, reps="12", load="60–70 lb"),
            Exercise("DB RDL", sets=4, reps="10", load="35–45 lb each"),
            Exercise("DB shoulder press", sets=3, reps="10", load="30–40 lb"),
            Exercise("DB farmer carry", sets=3, reps="30m", load="45–50 lb each"),
            Exercise("Pull-ups", sets=3, reps="max dead hang"),
            Exercise("Plank", sets=3, reps="30s"),
            Exercise("Flutter kicks", sets=3, reps="20"),
        ],
    )
    return DaySession(
        morning=[swim, strength],
        evening=[_bjj_block("No-gi")],
        bjj_available=True,
        total_duration_min=90,
        day_type="normal",
    )


def _p1_tuesday() -> DaySession:
    swim = SessionBlock(
        name="Pool",
        session_type="swim",
        duration_min=75,
        exercises=[
            Exercise("500m easy freestyle"),
            Exercise("6×100m", sets=6, reps="100m", load="45s rest"),
            Exercise("2×25m underwater", sets=2, reps="25m", note="Buddy required"),
            Exercise("400m cool-down"),
        ],
        coaching_note="Pool before 9am. Office day.",
    )
    return DaySession(
        morning=[swim],
        evening=[_bjj_block("Gi")],
        bjj_available=True,
        total_duration_min=75,
        day_type="normal",
    )


def _p1_wednesday(d: date) -> DaySession:
    week = get_week_number(d)
    interval_sets = min(4 + (week - 1), 6)  # build 4→6 by Week 8
    run = SessionBlock(
        name="Run",
        session_type="run",
        duration_min=40,
        exercises=[
            Exercise("10 min easy warm-up"),
            Exercise(f"{interval_sets}×800m comfortably hard", sets=interval_sets, reps="800m", load="2 min rest"),
        ],
    )
    strength_exercises = [
        Exercise("DB goblet squat", sets=4, reps="12"),
        Exercise("DB bent-over row", sets=4, reps="10", load="40–50 lb"),
        Exercise("Push-ups", sets=4, reps="20"),
        Exercise("Cable woodchop", sets=3, reps="15 each side", load="30–40 lb"),
        Exercise("Hanging knee raises", sets=3, reps="15"),
    ]
    if week >= 3:
        strength_exercises.insert(1, Exercise("Single-leg DB RDL", sets=3, reps="10 each", note="Introduced Week 3"))
    strength = SessionBlock(
        name="Home Strength",
        session_type="strength_home",
        duration_min=45,
        exercises=strength_exercises,
    )
    return DaySession(
        morning=[run, strength],
        evening=[_bjj_block("No-gi")],
        bjj_available=True,
        total_duration_min=85,
        day_type="normal",
    )


def _p1_thursday(d: date) -> DaySession:
    uw_count = get_thursday_underwater_count(d)
    swim = SessionBlock(
        name="Pool",
        session_type="swim",
        duration_min=75,
        exercises=[
            Exercise("800m continuous easy"),
            Exercise("6×100m", sets=6, reps="100m", load="45s rest"),
            Exercise(f"{uw_count}×25m underwater", sets=uw_count, reps="25m", note="Add one length per week, target 4 by Week 8"),
            Exercise("5 min tread (last 1 min arms-only)"),
        ],
        coaching_note="Pool before 9am. Office day.",
    )
    smith = SessionBlock(
        name="Smith Machine",
        session_type="strength_smith",
        duration_min=60,
        exercises=[
            Exercise("Smith RDL", sets=4, reps="8"),
            Exercise("Smith bent-over row", sets=3, reps="10"),
            Exercise("Smith overhead press", sets=3, reps="10"),
            Exercise("DB curl", sets=3, reps="12"),
            Exercise("Cable face pull", sets=3, reps="15"),
            Exercise("Pull-ups", sets=4, reps="8"),
        ],
        coaching_note="After work.",
    )
    return DaySession(
        morning=[swim],
        evening=[smith, _bjj_block("Gi")],
        bjj_available=True,
        total_duration_min=135,
        day_type="normal",
    )


def _p1_friday(d: date) -> DaySession:
    dist = get_friday_run_distance(d)
    run = SessionBlock(
        name="Long Run",
        session_type="run",
        duration_min=60,
        exercises=[
            Exercise(f"{dist:.2f} mi easy-moderate pace"),
            Exercise("20 min foam roll after"),
        ],
    )
    return DaySession(
        morning=[run],
        evening=[],
        bjj_available=False,
        total_duration_min=80,
        day_type="normal",
    )


def _p1_saturday(d: date) -> DaySession:
    week = get_week_number(d)
    swim_dist = get_saturday_long_swim_distance(d)
    swim = SessionBlock(
        name="Long Swim",
        session_type="swim",
        duration_min=60,
        exercises=[
            Exercise(f"{swim_dist}m continuous (build 1000→1500m by Week 8)"),
            Exercise("4×25m underwater", sets=4, reps="25m", load="3 min rest"),
            Exercise("400m cool-down"),
        ],
    )
    if week <= 2:
        calisthenics_exercises = [Exercise("Pull-ups", sets=5, reps="8")]
    else:
        calisthenics_exercises = [
            Exercise("Pull-up pyramid: 1-2-3-4-3-2-1"),
            Exercise("Push-up pyramid: 5-10-15-10-5"),
            Exercise("Sit-up pyramid: 10-20-30-20-10"),
            Exercise("Hollow body rocks", sets=3, reps="20"),
            Exercise("L-sit", sets=3, reps="20s"),
        ]
    calisthenics = SessionBlock(
        name="Calisthenics",
        session_type="calisthenics",
        duration_min=30,
        exercises=calisthenics_exercises,
    )
    return DaySession(
        morning=[swim, calisthenics],
        evening=[],
        bjj_available=False,
        total_duration_min=90,
        day_type="normal",
    )


# ── Phase 2 ─────────────────────────────────────────────────────────────────

def _p2_monday() -> DaySession:
    swim = SessionBlock(
        name="Swim",
        session_type="swim",
        duration_min=55,
        exercises=[
            Exercise("800m warm-up"),
            Exercise("10×100m", sets=10, reps="100m", load="2:30 rest"),
            Exercise("4×25m underwater", sets=4, reps="25m"),
            Exercise("400m fins cool-down (build to 800m by Week 20)"),
        ],
    )
    strength = SessionBlock(
        name="Home Strength",
        session_type="strength_home",
        duration_min=50,
        exercises=[
            Exercise("Cable pull-down", sets=4, reps="12", load="70–80 lb"),
            Exercise("DB RDL", sets=4, reps="10", load="45–50 lb each"),
            Exercise("DB shoulder press", sets=3, reps="12", load="35–45 lb"),
            Exercise("Farmer carry", sets=3, reps="40m", load="50 lb each"),
            Exercise("Pull-ups", sets=4, reps="max"),
            Exercise("Hollow body", sets=3, reps="20"),
            Exercise("Hanging leg raises", sets=3, reps="15"),
        ],
    )
    return DaySession(
        morning=[swim, strength],
        evening=[_bjj_block("No-gi")],
        bjj_available=True,
        total_duration_min=105,
        day_type="normal",
    )


def _p2_tuesday() -> DaySession:
    swim = SessionBlock(
        name="Pool",
        session_type="swim",
        duration_min=75,
        exercises=[
            Exercise("500m warm-up"),
            Exercise("8×100m", sets=8, reps="100m", load="2:00 rest"),
            Exercise("4×25m underwater", sets=4, reps="25m"),
            Exercise("8 min tread (last 2 min arms-only)"),
            Exercise("300m cool-down"),
        ],
        coaching_note="Pool before 9am.",
    )
    return DaySession(
        morning=[swim],
        evening=[_bjj_block("Gi")],
        bjj_available=True,
        total_duration_min=75,
        day_type="normal",
    )


def _p2_wednesday(d: date) -> DaySession:
    run_type = get_wednesday_run_type(d)
    if run_type == "tempo":
        run_desc = "2-mi tempo at goal 1.5-mi pace +30 sec/mi"
        run_dur = 30
    else:
        run_desc = "6×400m at goal pace / 90s rest"
        run_dur = 35
    run = SessionBlock(
        name="Run",
        session_type="run",
        duration_min=run_dur,
        exercises=[Exercise(run_desc)],
    )
    strength = SessionBlock(
        name="Home Strength",
        session_type="strength_home",
        duration_min=50,
        exercises=[
            Exercise("Goblet squat", sets=4, reps="12", load="45–50 lb"),
            Exercise("Single-leg RDL", sets=4, reps="10 each", load="30–40 lb"),
            Exercise("DB bent-over row", sets=4, reps="12", load="45–50 lb"),
            Exercise("Weighted push-ups", sets=4, reps="15–20"),
            Exercise("Cable woodchop", sets=3, reps="15", load="40–50 lb"),
            Exercise("Pull-up pyramid 1-2-3-4-5-4-3-2-1"),
        ],
    )
    return DaySession(
        morning=[run, strength],
        evening=[_bjj_block("No-gi")],
        bjj_available=True,
        total_duration_min=85,
        day_type="normal",
    )


def _p2_thursday() -> DaySession:
    swim = SessionBlock(
        name="Pool",
        session_type="swim",
        duration_min=75,
        exercises=[
            Exercise("500m warm-up"),
            Exercise("6×200m", sets=6, reps="200m", load="4:00 rest"),
            Exercise("4×25m underwater", sets=4, reps="25m"),
            Exercise("5 min tread"),
        ],
        coaching_note="Pool before 9am. Office day.",
    )
    smith = SessionBlock(
        name="Smith Machine",
        session_type="strength_smith",
        duration_min=60,
        exercises=[
            Exercise("Smith RDL", sets=4, reps="8", note="Progressive load"),
            Exercise("Smith bent-over row", sets=4, reps="10"),
            Exercise("Smith overhead press", sets=3, reps="12"),
            Exercise("DB incline curl", sets=3, reps="12"),
            Exercise("Cable face pull", sets=3, reps="15"),
            Exercise("Pull-ups", sets=5, reps="8"),
        ],
        coaching_note="After work.",
    )
    return DaySession(
        morning=[swim],
        evening=[smith, _bjj_block("Gi")],
        bjj_available=True,
        total_duration_min=135,
        day_type="normal",
    )


def _p2_friday(d: date) -> DaySession:
    week = get_week_number(d)
    if week % 2 == 1:
        desc = "5-mi tempo (2 easy / 2 threshold / 1 easy)"
    else:
        desc = "6×400m at 1.5-mi goal pace / 60s rest"
    run = SessionBlock(
        name="Run",
        session_type="run",
        duration_min=50,
        exercises=[Exercise(desc)],
    )
    return DaySession(
        morning=[run],
        evening=[],
        bjj_available=False,
        total_duration_min=50,
        day_type="normal",
    )


def _p2_saturday(d: date) -> DaySession:
    sat_type = get_saturday_type_p2(d)
    if sat_type == "swim":
        swim_dist = 1500 + (get_week_number(d) - 9) // 2 * 100
        swim_dist = min(swim_dist, 2000)
        block = SessionBlock(
            name="Long Swim + Calisthenics",
            session_type="swim",
            duration_min=90,
            exercises=[
                Exercise(f"{swim_dist}m long swim"),
                Exercise("Calisthenics pyramids: pull-ups, push-ups, sit-ups"),
            ],
        )
    else:
        dist = get_p2_saturday_long_run_distance(d)
        block = SessionBlock(
            name="Long Run",
            session_type="run",
            duration_min=90,
            exercises=[Exercise(f"{dist} mi long run")],
        )
    return DaySession(
        morning=[block],
        evening=[],
        bjj_available=False,
        total_duration_min=90,
        day_type="normal",
    )


# ── Phase 3 ─────────────────────────────────────────────────────────────────

def _p3_monday() -> DaySession:
    swim = SessionBlock(
        name="Swim",
        session_type="swim",
        duration_min=60,
        exercises=[
            Exercise("2000m mixed freestyle/side stroke/fins"),
            Exercise("4×25m underwater", sets=4, reps="25m"),
            Exercise("10 min tread (2 min arms-only + 2 min legs-only)"),
        ],
    )
    strength = SessionBlock(
        name="Heavy Home Strength",
        session_type="strength_home",
        duration_min=55,
        exercises=[
            Exercise("Cable pull-down", sets=4, reps="10", load="75–80 lb"),
            Exercise("DB RDL", sets=4, reps="8", load="50 lb each"),
            Exercise("Weighted pull-ups", sets=3, reps="5", load="15–25 lb"),
            Exercise("DB shoulder press", sets=4, reps="10", load="40–50 lb"),
            Exercise("Farmer carry", sets=3, reps="40m", load="50 lb each"),
            Exercise("Core circuit"),
        ],
    )
    return DaySession(
        morning=[swim, strength],
        evening=[_bjj_block("No-gi")],
        bjj_available=True,
        total_duration_min=115,
        day_type="normal",
    )


def _p3_tuesday() -> DaySession:
    swim = SessionBlock(
        name="Pool",
        session_type="swim",
        duration_min=75,
        exercises=[
            Exercise("500m warm-up"),
            Exercise("10×100m", sets=10, reps="100m", load="1:50 rest"),
            Exercise("4×25m underwater", sets=4, reps="25m"),
            Exercise("600m fins"),
            Exercise("8 min tread"),
        ],
    )
    return DaySession(
        morning=[swim],
        evening=[_bjj_block("Gi")],
        bjj_available=True,
        total_duration_min=75,
        day_type="normal",
    )


def _p3_wednesday(d: date) -> DaySession:
    week = get_week_number(d)
    if week % 2 == 1:
        run_desc = "8×400m / 60s rest"
    else:
        run_desc = "4×800m / 90s rest"
    run = SessionBlock(
        name="Run",
        session_type="run",
        duration_min=40,
        exercises=[Exercise(run_desc)],
    )
    strength = SessionBlock(
        name="Home Strength",
        session_type="strength_home",
        duration_min=50,
        exercises=[
            Exercise("Goblet squat", sets=4, reps="10", load="50 lb"),
            Exercise("Single-leg RDL", sets=4, reps="10 each", load="40–50 lb"),
            Exercise("DB bent-over row", sets=4, reps="12", load="50 lb"),
            Exercise("Weighted push-ups", sets=4, reps="20"),
            Exercise("Pull-up pyramid 1-2-3-4-5-4-3-2-1"),
            Exercise("Cable woodchop", sets=3, reps="15", load="50 lb"),
        ],
    )
    return DaySession(
        morning=[run, strength],
        evening=[_bjj_block("No-gi")],
        bjj_available=True,
        total_duration_min=90,
        day_type="normal",
    )


def _p3_thursday() -> DaySession:
    swim = SessionBlock(
        name="Pool",
        session_type="swim",
        duration_min=75,
        exercises=[
            Exercise("1500m continuous"),
            Exercise("4×25m underwater", sets=4, reps="25m"),
            Exercise("800m fins"),
        ],
    )
    smith = SessionBlock(
        name="Smith Machine",
        session_type="strength_smith",
        duration_min=60,
        exercises=[
            Exercise("Smith RDL", sets=4, reps="6", note="Heavy"),
            Exercise("Smith bent-over row", sets=4, reps="10"),
            Exercise("Smith overhead press", sets=4, reps="10"),
            Exercise("Pull-ups", sets=5, reps="10"),
            Exercise("DB curl", sets=3, reps="12"),
            Exercise("Cable face pull", sets=3, reps="15"),
        ],
    )
    return DaySession(
        morning=[swim],
        evening=[smith, _bjj_block("Gi")],
        bjj_available=True,
        total_duration_min=135,
        day_type="normal",
    )


def _p3_friday(d: date) -> DaySession:
    run_type = get_friday_run_type_p3(d)
    if run_type == "shakeout":
        run_desc, run_dur = "3-mi easy shakeout", 30
    else:
        run_desc, run_dur = "4–5 mi moderate run", 45
    run = SessionBlock(
        name="Friday Run",
        session_type="run",
        duration_min=run_dur,
        exercises=[Exercise(run_desc)],
    )
    return DaySession(
        morning=[run],
        evening=[],
        bjj_available=False,
        total_duration_min=run_dur,
        day_type="normal",
    )


def _p3_saturday(d: date) -> DaySession:
    if is_extended_hard_day(d):
        block = SessionBlock(
            name="Extended Hard Day",
            session_type="run",
            duration_min=240,
            exercises=[
                Exercise("Hour 1: 5-mi run"),
                Exercise("Hour 2: Pool — 1500m + underwaters + tread"),
                Exercise("Hour 3: Calisthenics circuits"),
                Exercise("Hour 4: 4-mi run"),
            ],
            coaching_note="Once-per-month extended session.",
        )
    else:
        dist = get_saturday_run_distance_p3(d)
        block = SessionBlock(
            name="Long Run",
            session_type="run",
            duration_min=120,
            exercises=[Exercise(f"{dist} mi long run")],
        )
    return DaySession(
        morning=[block],
        evening=[],
        bjj_available=False,
        total_duration_min=block.duration_min,
        day_type="normal",
    )


# ── Phase 4 ─────────────────────────────────────────────────────────────────

def _p4_monday() -> DaySession:
    swim = SessionBlock(
        name="Swim",
        session_type="swim",
        duration_min=50,
        exercises=[
            Exercise("1500m moderate"),
            Exercise("4×25m underwater", sets=4, reps="25m"),
            Exercise("400m fins"),
        ],
    )
    strength = SessionBlock(
        name="Home Strength (Reduced)",
        session_type="strength_home",
        duration_min=40,
        exercises=[
            Exercise("Weighted pull-ups", sets=4, reps="5", load="20–25 lb"),
            Exercise("Cable pull-down", sets=3, reps="10"),
            Exercise("DB RDL", sets=3, reps="8"),
            Exercise("DB shoulder press", sets=3, reps="10"),
            Exercise("Core circuit"),
        ],
    )
    return DaySession(
        morning=[swim, strength],
        evening=[_bjj_block("No-gi")],
        bjj_available=True,
        total_duration_min=90,
        day_type="normal",
    )


def _p4_tuesday() -> DaySession:
    swim = SessionBlock(
        name="Pool Race-Pace",
        session_type="swim",
        duration_min=60,
        exercises=[
            Exercise("500m warm-up"),
            Exercise("6×100m at goal race pace", sets=6, reps="100m", load="90s rest"),
            Exercise("4×25m underwater", sets=4, reps="25m"),
            Exercise("500m cool-down"),
        ],
    )
    return DaySession(
        morning=[swim],
        evening=[_bjj_block("Gi")],
        bjj_available=True,
        total_duration_min=60,
        day_type="normal",
    )


def _p4_wednesday() -> DaySession:
    run = SessionBlock(
        name="Run",
        session_type="run",
        duration_min=30,
        exercises=[Exercise("6×400m at 6:00/mi / 90s rest", sets=6, reps="400m")],
    )
    strength = SessionBlock(
        name="Max Effort + Mobility",
        session_type="calisthenics",
        duration_min=40,
        exercises=[
            Exercise("Pull-ups", sets=3, reps="max"),
            Exercise("Push-ups", sets=3, reps="max"),
            Exercise("Sit-ups", sets=3, reps="max"),
            Exercise("DB bent-over row", sets=3, reps="10"),
            Exercise("Cable face pull", sets=3, reps="15"),
            Exercise("20 min mobility"),
        ],
    )
    return DaySession(
        morning=[run, strength],
        evening=[_bjj_block("No-gi")],
        bjj_available=True,
        total_duration_min=70,
        day_type="normal",
    )


def _p4_thursday() -> DaySession:
    swim = SessionBlock(
        name="Pool",
        session_type="swim",
        duration_min=75,
        exercises=[
            Exercise("1000m easy"),
            Exercise("4×25m underwater", sets=4, reps="25m"),
            Exercise("600m fins"),
        ],
    )
    benchmark = SessionBlock(
        name="Full Benchmark Sequence",
        session_type="calisthenics",
        duration_min=90,
        exercises=[
            Exercise("4×25m underwater"),
            Exercise("500m swim", note="30 min rest after"),
            Exercise("1.5-mi run", note="10 min rest after"),
            Exercise("Max pull-ups"),
            Exercise("Max push-ups", load="2 min"),
            Exercise("Max sit-ups", load="2 min"),
        ],
        coaching_note="Log all scores.",
    )
    return DaySession(
        morning=[swim],
        evening=[benchmark, _bjj_block("Gi")],
        bjj_available=True,
        total_duration_min=165,
        day_type="normal",
    )


def _p4_friday() -> DaySession:
    run = SessionBlock(
        name="Shakeout Run",
        session_type="run",
        duration_min=30,
        exercises=[
            Exercise("3-mi easy run"),
            Exercise("20 min foam roll"),
        ],
    )
    return DaySession(
        morning=[run],
        evening=[],
        bjj_available=False,
        total_duration_min=50,
        day_type="normal",
    )


def _p4_saturday(d: date) -> DaySession:
    dist = get_saturday_taper_distance_p4(d)
    run = SessionBlock(
        name="Long Run (Tapering)",
        session_type="run",
        duration_min=int(dist * 10),
        exercises=[Exercise(f"{dist} mi")],
    )
    return DaySession(
        morning=[run],
        evening=[],
        bjj_available=False,
        total_duration_min=run.duration_min,
        day_type="normal",
    )


# ── Phase 5 ─────────────────────────────────────────────────────────────────

def _p5_monday() -> DaySession:
    swim = SessionBlock(
        name="Easy Swim",
        session_type="swim",
        duration_min=30,
        exercises=[
            Exercise("500m easy"),
            Exercise("4×25m underwater", sets=4, reps="25m"),
        ],
    )
    pt = SessionBlock(
        name="Light PT",
        session_type="calisthenics",
        duration_min=20,
        exercises=[
            Exercise("Pull-ups", sets=3, reps="10"),
            Exercise("Push-ups", sets=3, reps="20"),
            Exercise("Sit-ups", sets=3, reps="25"),
        ],
    )
    run = SessionBlock(
        name="Easy Run",
        session_type="run",
        duration_min=20,
        exercises=[Exercise("2-mi easy run")],
    )
    return DaySession(
        morning=[swim, pt, run],
        evening=[],
        bjj_available=False,
        total_duration_min=70,
        day_type="normal",
    )


def _p5_tuesday() -> DaySession:
    swim = SessionBlock(
        name="Pool Technique",
        session_type="swim",
        duration_min=40,
        exercises=[
            Exercise("500m easy"),
            Exercise("4×25m underwater", sets=4, reps="25m"),
            Exercise("10 min tread"),
        ],
    )
    return DaySession(
        morning=[swim],
        evening=[],
        bjj_available=False,
        total_duration_min=40,
        day_type="normal",
    )


def _p5_wednesday() -> DaySession:
    run = SessionBlock(
        name="Easy Run + Mobility",
        session_type="run",
        duration_min=50,
        exercises=[
            Exercise("3-mi easy run"),
            Exercise("30 min mobility"),
        ],
    )
    return DaySession(
        morning=[run],
        evening=[],
        bjj_available=False,
        total_duration_min=50,
        day_type="normal",
    )


def _p5_thursday() -> DaySession:
    benchmark = SessionBlock(
        name="Final Benchmark Sequence",
        session_type="calisthenics",
        duration_min=90,
        exercises=[
            Exercise("4×25m underwater"),
            Exercise("500m swim", note="30 min rest after"),
            Exercise("1.5-mi run", note="10 min rest after"),
            Exercise("Max pull-ups"),
            Exercise("Max push-ups", load="2 min"),
            Exercise("Max sit-ups", load="2 min"),
        ],
        coaching_note="Final benchmark. Log all scores.",
    )
    return DaySession(
        morning=[benchmark],
        evening=[],
        bjj_available=False,
        total_duration_min=90,
        day_type="normal",
    )


def _p5_friday() -> DaySession:
    swim = SessionBlock(
        name="Easy Swim",
        session_type="swim",
        duration_min=30,
        exercises=[Exercise("30 min easy swim, no effort")],
    )
    return DaySession(
        morning=[swim],
        evening=[],
        bjj_available=False,
        total_duration_min=30,
        day_type="normal",
    )


def _p5_saturday() -> DaySession:
    run = SessionBlock(
        name="Long Run",
        session_type="run",
        duration_min=75,
        exercises=[Exercise("6–8 mi easy run")],
    )
    return DaySession(
        morning=[run],
        evening=[],
        bjj_available=False,
        total_duration_min=75,
        day_type="normal",
    )


# ── Vacation sessions ────────────────────────────────────────────────────────

def _vacation_session(d: date, vac: Vacation) -> DaySession:
    day_num = (d - vac.start_date).days + 1
    total_days = (vac.end_date - vac.start_date).days + 1

    if vac.mode == "active_recovery":
        block = SessionBlock(
            name="Vacation — Active Recovery",
            session_type="bodyweight",
            duration_min=30,
            exercises=[
                Exercise("Surf when the waves are good."),
                Exercise("If not surfing: 20–30 min easy beach run (optional)"),
                Exercise("Bodyweight PT if you feel like it — push-ups, sit-ups, pull-ups on anything you can hang from"),
            ],
            coaching_note=f"Day {day_num} of {total_days}. {vac.notes}",
        )

    elif vac.mode == "maintain":
        if day_num % 2 == 1:
            block = SessionBlock(
                name="Morning Run",
                session_type="run",
                duration_min=40,
                exercises=[
                    Exercise("30–45 min easy run, no intervals — explore the city"),
                ],
                coaching_note=f"Day {day_num} of {total_days}. Target 4–5 runs this trip.",
            )
        else:
            block = SessionBlock(
                name="Bodyweight PT",
                session_type="bodyweight",
                duration_min=20,
                exercises=[
                    Exercise("Pull-ups", sets=3, reps="max"),
                    Exercise("Push-ups", sets=3, reps="20"),
                    Exercise("Sit-ups", sets=3, reps="25"),
                ],
                coaching_note=f"Day {day_num} of {total_days}. Target 3–4 PT sessions this trip.",
            )

    else:  # running_only
        from program.schedule import get_week_number as gwn
        from program.dynamic import get_saturday_run_distance_p3
        # Find next Saturday's long run distance for context
        from datetime import timedelta as td
        days_ahead = (5 - d.weekday()) % 7
        next_sat = d + td(days=days_ahead) if days_ahead > 0 else d + td(days=7)
        try:
            sat_dist = get_saturday_run_distance_p3(next_sat)
            sat_note = f"Building toward {sat_dist} mi — these highland runs count."
        except Exception:
            sat_note = "These highland runs count toward your long run goal."

        block = SessionBlock(
            name="Highland Run",
            session_type="run",
            duration_min=55,
            exercises=[
                Exercise("45–60 min run in highland terrain — easy to moderate, no pace targets"),
                Exercise("Bodyweight PT if accommodation allows: pull-ups, push-ups, sit-ups"),
            ],
            coaching_note=f"Day {day_num} of {total_days}. {sat_note}",
        )

    return DaySession(
        morning=[block],
        evening=[],
        bjj_available=False,
        total_duration_min=block.duration_min,
        day_type="vacation",
    )


# ── Reentry sessions ─────────────────────────────────────────────────────────

def _reentry_session(d: date, vac: Vacation, day_num: int) -> DaySession:
    if day_num == 1:
        block = SessionBlock(
            name="Reentry Day 1 — Easy Run Only",
            session_type="run",
            duration_min=25,
            exercises=[Exercise("20–30 min genuinely easy run")],
            coaching_note=f"Welcome back from {vac.name}. Today is a reentry day — easy run only. The program resumes fully on Day 3.",
        )
        return DaySession(
            morning=[block],
            evening=[],
            bjj_available=False,
            total_duration_min=25,
            day_type="reentry_1",
        )
    elif day_num == 2:
        run = SessionBlock(
            name="Easy Run",
            session_type="run",
            duration_min=30,
            exercises=[Exercise("30 min easy run")],
        )
        pt = SessionBlock(
            name="Light PT (60% volume)",
            session_type="bodyweight",
            duration_min=20,
            exercises=[
                Exercise("Pull-ups", sets=3, reps="60% normal"),
                Exercise("Push-ups", sets=3, reps="60% normal"),
                Exercise("Sit-ups", sets=3, reps="60% normal"),
            ],
            coaching_note="Reentry Day 2 of 3. Adding light PT today.",
        )
        return DaySession(
            morning=[run, pt],
            evening=[],
            bjj_available=False,
            total_duration_min=50,
            day_type="reentry_2",
        )
    else:  # day 3
        # Resume normal program session
        full_session = get_session(d)
        full_session.day_type = "reentry_3"
        week = get_week_number(d)
        phase = get_phase(d)
        for block in full_session.morning:
            block.coaching_note = (
                f"Back to full program today. Week {week}, Phase {phase}. "
                f"Here's what's on for the rest of the week."
            )
            break  # only annotate first block
        return full_session


# ── Rest ─────────────────────────────────────────────────────────────────────

def _rest_session() -> DaySession:
    return DaySession(
        morning=[SessionBlock(name="Rest", session_type="rest", duration_min=0)],
        evening=[],
        bjj_available=False,
        total_duration_min=0,
        day_type="rest",
    )


# ── Public entry point ────────────────────────────────────────────────────────

def get_session(d: date) -> DaySession:
    """Returns the DaySession for the given date."""
    day_type = get_day_type(d)

    if day_type == DayType.VACATION:
        vac = get_vacation(d)
        return _vacation_session(d, vac)

    if day_type in (DayType.REENTRY_1, DayType.REENTRY_2, DayType.REENTRY_3):
        result = get_reentry_day(d)
        vac, num = result
        return _reentry_session(d, vac, num)

    if day_type == DayType.REST:
        return _rest_session()

    phase = get_phase(d)
    weekday = d.weekday()  # 0=Mon, 6=Sun

    dispatch = {
        1: {0: _p1_monday, 1: _p1_tuesday, 2: lambda: _p1_wednesday(d),
            3: lambda: _p1_thursday(d), 4: lambda: _p1_friday(d), 5: lambda: _p1_saturday(d)},
        2: {0: _p2_monday, 1: _p2_tuesday, 2: lambda: _p2_wednesday(d),
            3: _p2_thursday, 4: lambda: _p2_friday(d), 5: lambda: _p2_saturday(d)},
        3: {0: _p3_monday, 1: _p3_tuesday, 2: lambda: _p3_wednesday(d),
            3: _p3_thursday, 4: lambda: _p3_friday(d), 5: lambda: _p3_saturday(d)},
        4: {0: _p4_monday, 1: _p4_tuesday, 2: _p4_wednesday,
            3: _p4_thursday, 4: _p4_friday, 5: lambda: _p4_saturday(d)},
        5: {0: _p5_monday, 1: _p5_tuesday, 2: _p5_wednesday,
            3: _p5_thursday, 4: _p5_friday, 5: _p5_saturday},
    }

    phase_dispatch = dispatch.get(phase, {})
    fn = phase_dispatch.get(weekday)
    if fn is None:
        return _rest_session()
    return fn()
