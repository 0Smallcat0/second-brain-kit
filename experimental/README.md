# Experimental

Things that are not part of the default install, because they are not proven. One line each on why.

| Item | Why it is here |
|---|---|
| [`wake_session.py`](wake_session.py) | Sends a message to a *stopped* topic session through `claude --resume`; written from the documented flags but not run by the kit's tests (it needs a real session id and spends quota). Pushing text into a session that is currently open is not possible this way; the supported route is the inbox + `inbox_notice` hook. |
| [`completion_gate.md`](completion_gate.md) | Design notes for an independent "verifier" check before a deliverable is closed. A heavier version of this got stuck in real use (it kept failing and nothing could finish), so it ships as a design only, with the one rule that makes it safe to try. |

To try something here, copy it out of this folder, run it by hand first, and put any hook it needs in `log` mode before letting it block.
