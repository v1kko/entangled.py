"""
The `reset` command resets the file database in `.entangled/filedb.json`.
This database gets updated every time you tangle or stitch, but sometimes
its contents may become invalid, for instance when switching branches.
This command will read the markdown sources, then pretend to be tangling
without actually writing out to source files.
"""

from ..io import TransactionMode
from .main import main
from .tangle import do_tangle


@main.command(short_help="Reset the file database.")
def reset():
    """
    Resets the file database. This performs a tangle without actually
    writing output to the files, but updating the database as if we were.
    """
    do_tangle(mode=TransactionMode.RESETDB)
