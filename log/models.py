from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional, List


@dataclass
class WhoopData:
    date: date
    recovery_score: Optional[int] = None
    hrv_ms: Optional[float] = None
    resting_hr: Optional[int] = None
    sleep_performance: Optional[int] = None
    yesterday_strain: Optional[float] = None


@dataclass
class SessionResult:
    completed: List[str] = field(default_factory=list)
    skipped: List[dict] = field(default_factory=list)
    feel: Optional[str] = None
    injury_flags: List[str] = field(default_factory=list)
    notes: Optional[str] = None
    compliance: Optional[str] = None


@dataclass
class DayLog:
    date: date
    week_number: int
    phase: int
    day_type: str
    vacation_name: Optional[str]
    planned_session: dict
    adjusted_session: Optional[dict]
    modification_made: bool
    coaching_note: Optional[str]
    whoop_recovery: Optional[int]
    whoop_hrv: Optional[float]
    whoop_resting_hr: Optional[int]
    whoop_sleep_perf: Optional[int]
    whoop_yesterday_strain: Optional[float]
    email_sent_at: Optional[datetime]
    email_message_id: Optional[str]
    reply_received_at: Optional[datetime]
    reply_raw: Optional[str]
    reply_parsed: Optional[dict]
    compliance: Optional[str]
    followup_sent_at: Optional[datetime]
