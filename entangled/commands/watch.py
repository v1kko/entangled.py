from pathlib import Path
from threading import Event
import subprocess

from ..status import find_watch_dirs

from .sync import run_sync
from .main import main


def _watch(_stop_event: Event | None = None, _start_event: Event | None = None):
    """Keep a loop running, watching for changes. This interface is separated
    from the CLI one, so that it can be tested using threading instead of
    subprocess."""

    def stop() -> bool:
        return _stop_event is not None and _stop_event.is_set()

    if _start_event:
        _start_event.set()

    while not stop():
        subprocess.run(["watchman-wait"] + list(find_watch_dirs()))
        run_sync()


@main.command()
def watch():
    """Keep a loop running, watching for changes."""
    _watch()
