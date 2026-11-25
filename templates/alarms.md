# Alarms

Read by `alarm.py --tick` (run every 5 minutes by the OS scheduler). The tick reads local files and
uses no Claude quota. Firing writes first: a tracker item (ledger.md) for `entry`, or a line in a
session's inbox (`maintenance`, a topic). With live routing (config.json `"routing": "live"`) the
work then goes straight into the running session, or the session is started in the background;
that uses quota, so it is capped by config.json `wake_limits` (per day, and minutes between two for
one session). Over the cap the line waits in the inbox. `handover` replaces long background
conversations with fresh ones (handover.py).

Computer off or asleep: nothing fires then. At the next tick a missed row fires once, marked (late).

`when` is one of:
- `daily 21:00`
- `weekly mon 09:00`   (mon tue wed thu fri sat sun)
- `monthly 1 10:00`   (day 1-31; a short month uses its last day)
- `once 2030-01-31 18:00`

Keep this short. Every row must lead to an action somebody takes; delete rows nobody acts on.
No polling alarms ("check every 10 minutes"): ask for a one-time or daily check instead.
Plan defaults (set at install): Pro, API or not sure: M01 only. Max and higher: M01 and M02.

| id | when | to | text |
|---|---|---|---|
| M01 | weekly sun 20:00 | maintenance | Weekly review (learning loop): learn.py trend; group the week's corrections and confirmations by kind into preferences, skills and hook proposals; find missed items and "done" without evidence; clean old lines |
| T01 | monthly 1 10:00 | maintenance | Re-check the outside resources table (channels.md): only what the user has |
| H01 | daily 21:30 | handover | Long background conversations hand over to fresh ones |
