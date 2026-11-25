# Alarms

Read by `alarm.py --tick` (run every 5 minutes by the OS scheduler). Firing writes to the ledger
(`entry`) or to a manager's inbox; it never interrupts a running session.

`when` is one of:
- `daily 21:00`
- `weekly mon 09:00`   (mon tue wed thu fri sat sun)
- `once 2030-01-31 18:00`

Keep this short. Every row must lead to an action somebody takes; delete rows nobody acts on.
No polling alarms ("check every 10 minutes"): ask for a one-time or daily check instead.

| id | when | to | text |
|---|---|---|---|
| A01 | weekly sun 20:00 | entry | Weekly review: close or drop ledger items older than 14 days, read every task.md |
