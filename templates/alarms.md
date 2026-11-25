# Alarms

Read by `alarm.py --tick` (run every 5 minutes by the OS scheduler). Firing writes to the tracker
(ledger.md, for `entry`) or to a session's inbox (`supervisor`, `maintenance`, a topic); it never
interrupts a running session. A session starts by itself only if auto-wake is on for it
(config.json "wake"); otherwise the line waits until the user opens that session.

`when` is one of:
- `daily 21:00`
- `weekly mon 09:00`   (mon tue wed thu fri sat sun)
- `monthly 1 10:00`   (day 1-31; a short month uses its last day)
- `once 2030-01-31 18:00`

Keep this short. Every row must lead to an action somebody takes; delete rows nobody acts on.
No polling alarms ("check every 10 minutes"): ask for a one-time or daily check instead.

| id | when | to | text |
|---|---|---|---|
| A01 | weekly sun 20:00 | entry | Weekly review: close or drop tracker items older than 14 days, read every task.md |
