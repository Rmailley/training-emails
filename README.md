# training-emails

Daily training email system. Sends adjusted sessions each morning, receives
replies via Postmark inbound webhook, tracks compliance over 52 weeks.

Program start: **April 28, 2025**  
Email: **fitness@robmailley.com**

---

## 1. DNS Setup (Ionos)

Log into the Ionos DNS panel for `robmailley.com`. Add these four records:

| Type | Host | Value | TTL |
|------|------|-------|-----|
| MX | `@` | `inbound.postmarkapp.com` (priority 10) | 3600 |
| TXT | `@` | Postmark domain verification value (from dashboard) | 3600 |
| TXT | `pm._domainkey` | Postmark DKIM value (from dashboard) | 3600 |
| TXT | `@` | `v=spf1 include:spf.mtasv.net ~all` | 3600 |

**Note:** Ionos DNS propagation takes 30–60 minutes. Verify in the Postmark
dashboard before sending real mail.

---

## 2. Postmark Setup

1. Create a Postmark account and add a server.
2. Under **Sending**, add `robmailley.com` as a sender domain and grab the
   DKIM + verification TXT values for DNS above.
3. Under **Inbound**, enable inbound processing. Set the inbound webhook URL to
   `https://your-server:8080/inbound`.
4. Set a webhook token under **Settings → Webhooks** and put it in `.env` as
   `POSTMARK_WEBHOOK_TOKEN`.
5. Copy the server API token to `.env` as `POSTMARK_SERVER_TOKEN`.

---

## 3. Whoop OAuth Setup

Whoop uses OAuth2 client credentials.

1. Create an app at <https://developer.whoop.com/> and get a client ID + secret.
2. Authorize once with the OAuth flow to obtain a refresh token.
   A quick way: use the Whoop Developer Portal's "Try It" feature and copy the
   refresh token from the token response.
3. Add to `.env`:

```
WHOOP_CLIENT_ID=...
WHOOP_CLIENT_SECRET=...
WHOOP_REFRESH_TOKEN=...
```

The app refreshes the access token automatically before each API call.
If the refresh token ever expires, repeat step 2 and update `.env`.

---

## 4. Install & First Run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in all values

# Preview Week 1 Day 1 without sending anything
python cli.py preview --date 2025-04-28

# Send today's email immediately
python cli.py send now

# Start the full system (scheduler + webhook server)
python main.py
```

---

## 5. Vacation Configuration

All vacations are defined in `program/vacations.py` as the `VACATIONS` list.
To add or modify a trip:

1. Add a new `Vacation(...)` entry to the list.
2. The system automatically derives pre-vacation email dates, reentry days,
   and compliance exemption — nothing else needs updating.

Fields:

| Field | Description |
|-------|-------------|
| `name` | Display name used in email subjects |
| `start_date` / `end_date` | Inclusive dates |
| `mode` | `active_recovery`, `maintain`, or `running_only` |
| `available` | What equipment/activities are accessible |
| `dropped` | What's suspended for this trip |
| `location` | Shown in email headers |
| `notes` | Displayed in vacation and pre-vacation emails |
| `reentry_days` | How many days of reentry protocol on return (default 3) |

---

## 6. Cron Alternative

If you prefer cron over the built-in scheduler, stop `main.py` and use:

```crontab
30 6 * * * cd /path/to/training-emails && .venv/bin/python -c "from jobs import run_morning_job; run_morning_job()"
0 21 * * * cd /path/to/training-emails && .venv/bin/python -c "from jobs import run_followup_job; run_followup_job()"
0 7 * * 0 cd /path/to/training-emails && .venv/bin/python -c "from jobs import run_sunday_summary; run_sunday_summary()"
```

The webhook server still needs to run independently:
```bash
uvicorn main:app --host 0.0.0.0 --port 8080
```

---

## 7. Benchmark Logging

Log a benchmark session after completing the Phase 2/4/5 benchmark sequence:

```bash
python cli.py benchmark --date 2025-09-01 --pullups 14 --pushups 58 --situps 65 --run 9:52 --swim 11:20

# View trend
python cli.py benchmark-show
```

Times are in `MM:SS` format. Any field can be omitted if not completed.

---

## 8. Troubleshooting

**DNS not propagating:** Wait 60 min, then use `dig MX robmailley.com` to
confirm the MX record is live before testing inbound.

**Whoop token refresh failing:** The Whoop refresh token can expire after
extended inactivity. Re-authorize via the developer portal and update
`WHOOP_REFRESH_TOKEN` in `.env`.

**Webhook verification failing:** Check that `POSTMARK_WEBHOOK_TOKEN` in `.env`
matches exactly the token configured in the Postmark webhook settings.

**Claude API unavailable:** The system falls back gracefully — it sends the
unadjusted session with a note in the email that Claude was unavailable.

**Email not matched to day log:** If a reply can't be matched by `In-Reply-To`
header, it falls back to the most recent unlogged day and logs a warning:
`Reply matched by recency fallback`.
