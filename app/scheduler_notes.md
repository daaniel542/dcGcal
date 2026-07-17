# Scheduling Notes

## Option 1: macOS launchd (recommended)

This is the native macOS scheduler and works more reliably than cron on modern macOS.

### Install the schedule:

```bash
# Copy plist to LaunchAgents
cp com.aggiemeal.notifier.plist ~/Library/LaunchAgents/

# Load it (starts the schedule immediately)
launchctl load ~/Library/LaunchAgents/com.aggiemeal.notifier.plist
```

### Check if it's running:

```bash
launchctl list | grep aggiemeal
```

### Unload (stop the schedule):

```bash
launchctl unload ~/Library/LaunchAgents/com.aggiemeal.notifier.plist
```

### Run manually right now:

```bash
launchctl start com.aggiemeal.notifier
```

### Check logs:

```bash
cat logs/launchd_stdout.log
cat logs/launchd_stderr.log
cat logs/app.log
cat logs/cron.log
```

## Option 2: cron

### Add a cron entry:

```bash
crontab -e
```

Add this line to run daily at 6 AM:

```
0 6 * * * /Users/yangshuoning/Desktop/personal\ coding\ projects/aggie-meal-notifier/run_daily.sh >> /Users/yangshuoning/Desktop/personal\ coding\ projects/aggie-meal-notifier/logs/cron.log 2>&1
```

### Verify:

```bash
crontab -l
```

## Schedule timing

- **6:00 AM** — Primary run. Menus are usually posted the night before.
- **4:00 PM** (optional) — Fallback run to catch any mid-day menu updates.

To enable the 4 PM fallback with launchd, uncomment the array-based 
`StartCalendarInterval` section in the plist and remove the single-dict version.
