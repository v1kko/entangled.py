import rich_click as click

from .main import main

from ..config import AnnotationMethod, Config
from ..io import AbstractFileCache, FileCache, transaction, TransactionMode
from ..errors.user import UserError
from ..interface import Context, Document


@main.command()
@click.option("-a", "--annotate", type=click.Choice(AnnotationMethod, case_sensitive=False),
              help="annotation method")
@click.option("-f", "--force", is_flag=True, help="force overwriting existing files")
@click.option("-s", "--show", is_flag=True, help="only show what would happen")
def tangle(*, annotate: AnnotationMethod | None = None, force: bool = False, show: bool = False):
    if show:
        mode = TransactionMode.SHOW
    elif force:
        mode = TransactionMode.FORCE
    else:
        mode = TransactionMode.FAIL

    do_tangle(annotate=annotate, mode=mode, skip_post_tangle=False)


def do_tangle(*,
    annotate: AnnotationMethod | None = None,
    mode: TransactionMode = TransactionMode.FAIL,
    fs: AbstractFileCache | None = None,
    skip_post_tangle: bool = True):
    """Tangle codes from the documentation."""

    if fs is None:
        fs = FileCache()

    doc = Document(context=Context(fs=fs))

    with transaction(mode, fs=fs) as t:
        doc.load(t)
        doc.tangle(t, annotate)
        t.clear_orphans()

    if skip_post_tangle:
        return

    for h in doc.context.all_hooks:
        h.post_tangle(doc.reference_map)
