from threading import Event

from ..status import find_watch_dirs

from .sync import run_sync
from .main import main

import watchfiles


def _watch(_stop_event: Event | None = None, _start_event: Event | None = None):
    """Keep a loop running, watching for changes. This interface is separated
    from the CLI one, so that it can be tested using threading instead of
    subprocess."""

    def stop() -> bool:
        return _stop_event is not None and _stop_event.is_set()

    run_sync()

    if _start_event:
        _start_event.set()

    dirs = "."  # find_watch_dirs()
    
    for changes in watchfiles.watch(dirs, stop_event=_stop_event):
        run_sync()


@main.command()
def watch():
    """Keep a loop running, watching for changes."""
    _watch()
