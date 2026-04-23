# Future Features & Known Issues

---

## 🐛 Known Issues / Edge Cases

### Deleted calendar events not re-created
**Problem:** If you manually delete an event from Google Calendar, the app still thinks it exists (the `calendar_events` table in SQLite still has the record). Re-running `main.py` will skip it as a "duplicate."

**Current workaround:**
```bash
# Clear today's event records so they get recreated
venv/bin/python -c "
from app.db import get_conn, init_db
init_db()
conn = get_conn()
conn.execute('DELETE FROM calendar_events WHERE date = \"YYYY-MM-DD\"')
conn.commit()
conn.close()
"
```

**Future fix:** Before creating events, verify each recorded event still exists on Google Calendar via the API. If the event was deleted, remove the DB record and recreate it.

---

## 🔮 Stretch Features

### Phase 11 — Better Matching
- [ ] Add **fuzzy matching** using `rapidfuzz` (e.g. "Chicken Tikka" matches "Chicken Tikka Masala Bowl")
- [ ] Support **aliases** in favorites (e.g. `"Mongolian BBQ": ["Mongolian Wok", "BYO Mongolian"]`)
- [ ] Add **keyword groups** (e.g. `"omelette"` matches all omelette variants)
- [ ] Configurable match threshold / confidence score

### Phase 12 — Multi-Location Support
- [ ] Add all UC Davis dining commons (Cuarto, Latitude)
- [ ] Support **preferred locations** (prioritize Tercero over Segundo)
- [ ] Per-location favorite lists
- [ ] Show which locations are serving the same favorite

### Phase 13 — History & Analytics
- [ ] Query **most frequent** favorite meals
- [ ] Count appearances **by weekday** (is Tri Tip always on Tuesdays?)
- [ ] Show **last seen date** for each favorite
- [ ] CSV/JSON export of historical data
- [ ] Weekly/monthly summary reports

### Phase 14 — Menu Prediction Model
- [ ] Collect enough historical data (4–8 weeks minimum)
- [ ] Analyze **weekday patterns** (many dining halls rotate on a weekly cycle)
- [ ] Score probability of a meal appearing by day of week
- [ ] Estimate **likely next appearance** for each favorite
- [ ] Compare predictions vs actual results to measure accuracy
- [ ] Send a "prediction digest" — "Tri Tip is likely tomorrow (85% confidence)"
- [ ] Explore simple ML models (logistic regression, decision trees) once enough data exists

### Phase 15 — Web Dashboard
- [ ] Simple web UI to **manage favorites** (add/remove without editing JSON)
- [ ] View **match history** and upcoming predictions
- [ ] Toggle reminders on/off per meal
- [ ] View menu for the current day
- [ ] Mobile-friendly design

---

## 🛠️ Infrastructure Improvements

### Calendar Sync
- [ ] On each run, verify recorded events still exist on Google Calendar
- [ ] Delete orphaned DB records for events that were manually removed
- [ ] Support **updating** existing events if meal details change

### Token Management
- [ ] Auto-detect expired OAuth tokens and prompt for re-auth
- [ ] Add a `--reauth` CLI flag to force re-authentication

### Multi-User Support
- [ ] Support multiple users with separate favorites and calendars
- [ ] Shared favorites list for groups (e.g. a friend group)

### Notification Options
- [ ] Slack webhook integration
- [ ] Discord webhook integration
- [ ] Email digest option
- [ ] Push notifications via Pushover/Ntfy

### Data Quality
- [ ] Detect when the HTML structure changes and alert the user
- [ ] Track parser success rate over time
- [ ] Fallback parser for alternative HTML layouts
