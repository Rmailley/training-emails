from dataclasses import dataclass, field
from datetime import date
from typing import List


@dataclass
class Vacation:
    name: str
    start_date: date
    end_date: date
    mode: str  # 'active_recovery' | 'maintain' | 'running_only'
    available: List[str]
    dropped: List[str]
    location: str
    notes: str
    reentry_days: int = 3


VACATIONS: List[Vacation] = [
    Vacation(
        name="Nicaragua",
        start_date=date(2025, 5, 1),
        end_date=date(2025, 5, 5),
        mode="active_recovery",
        available=["run", "bodyweight", "surf"],
        dropped=["swim", "strength_home", "strength_smith", "intervals"],
        location="San Juan del Sur, Nicaragua",
        notes="Surf camp at Playa Maderas. Week 1 — no pressure. Stay active when convenient.",
        reentry_days=2,
    ),
    Vacation(
        name="Japan",
        start_date=date(2025, 7, 11),
        end_date=date(2025, 7, 21),
        mode="maintain",
        available=["run", "bodyweight", "gym"],
        dropped=["swim", "strength_smith", "intervals"],
        location="Japan",
        notes="With family. Morning runs 4–5 days. Bodyweight PT 3–4 mornings. Eat and drink freely.",
        reentry_days=3,
    ),
    Vacation(
        name="Iceland",
        start_date=date(2025, 9, 4),
        end_date=date(2025, 9, 13),
        mode="running_only",
        available=["run", "bodyweight"],
        dropped=["swim", "strength_home", "strength_smith", "intervals"],
        location="Kerlingarfjöll highlands, Iceland",
        notes="Highland terrain running. No pool available. Bodyweight if accommodation allows.",
        reentry_days=3,
    ),
]
