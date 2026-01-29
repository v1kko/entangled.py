from collections.abc import Generator
from pathlib import PurePath

from ..text_location import TextLocation

from .peekable import peekable


type InputToken = tuple[TextLocation, str]


def lines(text: str) -> Generator[str]:
    """Iterate over lines in text, preserving newlines."""
    pos = 0
    while (next_pos := text.find("\n", pos)) != -1:
        yield text[pos:next_pos + 1]
        pos = next_pos + 1
    yield text[pos:]


@peekable
def numbered_lines(filename: PurePath, text: str) -> Generator[InputToken]:
    """Iterate the lines in a file. Doesn't strip newlines."""
    for n, line in enumerate(lines(text)):
        yield (TextLocation(filename, n+1), line)
