# Experimental

Things that are not part of the default install, because they are not proven. One line each on why.

| Item | Why it is here |
|---|---|
| [`wake_session.py`](wake_session.py) | Superseded by `entry/session.py` (0.2.5), which starts background sessions with `claude --bg` and passes messages into running ones with Claude Code's cross-session messaging. Kept only as the older `claude --resume` route for a *stopped* session; not run by the kit's tests. |
| [`completion_gate.md`](completion_gate.md) | Design notes for an independent "verifier" check before a deliverable is closed. A heavier version of this got stuck in real use (it kept failing and nothing could finish), so it ships as a design only, with the one rule that makes it safe to try. |

To try something here, copy it out of this folder, run it by hand first, and put any hook it needs in `log` mode before letting it block.
