# src/periodic_control.py
"""
Thread-safe control for the periodic capture loop.

`periodic_enabled` is a `threading.Event` that is **set** by default
(i.e. periodic capture runs normally).  The Flask routes will clear/set
this flag to pause/resume the loop.
"""

from threading import Event

# Initially enabled – captures run when the app starts.
periodic_enabled = Event()
periodic_enabled.set()
