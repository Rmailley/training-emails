import logging
import os
from datetime import date, timedelta
from typing import Optional

import requests

from log.models import WhoopData

logger = logging.getLogger(__name__)

WHOOP_API_BASE = "https://api.prod.whoop.com/developer/v1"


def _get_access_token() -> Optional[str]:
    client_id = os.getenv("WHOOP_CLIENT_ID")
    client_secret = os.getenv("WHOOP_CLIENT_SECRET")
    refresh_token = os.getenv("WHOOP_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        logger.warning("Whoop credentials not fully configured.")
        return None

    resp = requests.post(
        "https://api.prod.whoop.com/oauth/oauth2/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("access_token")


def get_whoop_data(d: date) -> Optional[WhoopData]:
    """Fetch Whoop recovery and sleep data for the given date. Returns None on any failure."""
    try:
        token = _get_access_token()
        if not token:
            return None

        headers = {"Authorization": f"Bearer {token}"}

        # Recovery covers the sleep period ending on date d
        start = (d - timedelta(days=1)).isoformat() + "T00:00:00.000Z"
        end = d.isoformat() + "T23:59:59.000Z"

        recovery_resp = requests.get(
            f"{WHOOP_API_BASE}/recovery",
            headers=headers,
            params={"start": start, "end": end},
            timeout=10,
        )
        recovery_resp.raise_for_status()
        recovery_records = recovery_resp.json().get("records", [])

        sleep_resp = requests.get(
            f"{WHOOP_API_BASE}/sleep",
            headers=headers,
            params={"start": start, "end": end},
            timeout=10,
        )
        sleep_resp.raise_for_status()
        sleep_records = sleep_resp.json().get("records", [])

        # Yesterday's strain
        yesterday = d - timedelta(days=1)
        strain_start = (yesterday - timedelta(days=1)).isoformat() + "T00:00:00.000Z"
        strain_end = yesterday.isoformat() + "T23:59:59.000Z"
        strain_resp = requests.get(
            f"{WHOOP_API_BASE}/cycle",
            headers=headers,
            params={"start": strain_start, "end": strain_end},
            timeout=10,
        )
        strain_resp.raise_for_status()
        strain_records = strain_resp.json().get("records", [])

        recovery_score = None
        hrv_ms = None
        resting_hr = None
        sleep_performance = None
        yesterday_strain = None

        if recovery_records:
            rec = recovery_records[-1]
            score = rec.get("score", {})
            recovery_score = score.get("recovery_score")
            hrv_ms = score.get("hrv_rmssd_milli")
            resting_hr = score.get("resting_heart_rate")

        if sleep_records:
            slp = sleep_records[-1]
            sleep_performance = slp.get("score", {}).get("sleep_performance_percentage")

        if strain_records:
            yesterday_strain = strain_records[-1].get("score", {}).get("strain")

        return WhoopData(
            date=d,
            recovery_score=int(recovery_score) if recovery_score is not None else None,
            hrv_ms=float(hrv_ms) if hrv_ms is not None else None,
            resting_hr=int(resting_hr) if resting_hr is not None else None,
            sleep_performance=int(sleep_performance) if sleep_performance is not None else None,
            yesterday_strain=float(yesterday_strain) if yesterday_strain is not None else None,
        )

    except Exception as e:
        logger.warning(f"Whoop data unavailable for {d}: {e}")
        return None
