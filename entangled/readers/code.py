from collections.abc import Generator
from dataclasses import dataclass
from pathlib import PurePath

import re

from .types import InputStream
from ..model import ReferenceId, ReferenceName
from ..errors.user import ParseError, IndentationError
from ..logging import logger

log = logger()

@dataclass
class Block:
    reference_id: ReferenceId
    content: str


# Pre-compile regex patterns at module level (avoid re-compilation on every call)
_OPEN_BLOCK_PATTERN = re.compile(
    r"^(?P<indent>\s*).* ~/~ begin <<(?P<source>[^#<>]+)#(?P<ref_name>[^#<>]+)>>\[(?P<ref_count>\d+|init)\]"
)
_CLOSE_BLOCK_PATTERN = re.compile(r"^(?P<indent>\s*).* ~/~ end")


@dataclass
class OpenBlockData:
    ref: ReferenceId
    is_init: bool
    indent: str


def open_block(line: str) -> OpenBlockData | None:
    if not (m := _OPEN_BLOCK_PATTERN.match(line)):
        return None

    ref_name = ReferenceName.from_str(m["ref_name"])
    md_source = PurePath(m["source"])
    is_init = m["ref_count"] == "init"
    ref_count = 0 if is_init else int(m["ref_count"])
    return OpenBlockData(ReferenceId(ref_name, md_source, ref_count), is_init, m["indent"])


@dataclass
class CloseBlockData:
    indent: str


def close_block(line: str) -> CloseBlockData | None:
    if not (m := _CLOSE_BLOCK_PATTERN.match(line)):
        return None
    return CloseBlockData(m["indent"])


def read_top_level(input: InputStream) -> Generator[Block]:
    if not input:
        return

    while input:
        r = yield from read_block((), "", input)
        if r is None:
            _ = next(input)


def read_block(namespace: tuple[str, ...], indent: str, input: InputStream) -> Generator[Block, None, str | None]:
    if not input:
        return None

    pos, line1 = input.peek()
    if (block_data := open_block(line1)) is None:
        return None
    _ = next(input)

    log.debug(f"reading code block {block_data}")

    if block_data.indent < indent:
        raise IndentationError(pos)

    # Use list for O(n) instead of O(n²) string concatenation
    content_parts: list[str] = []
    while input:
        line = yield from read_block(block_data.ref.name.namespace, block_data.indent, input)
        if line is not None:
            content_parts.append(line)
            continue

        pos, line = next(input)
        if (close_block_data := close_block(line)) is None:
            if not line.strip():
                content_parts.append(line.lstrip(" \t"))
            elif not line.startswith(block_data.indent):
                raise IndentationError(pos)
            else:
                content_parts.append(line.removeprefix(block_data.indent))
        else:
            if close_block_data.indent != block_data.indent:
                raise IndentationError(pos)
            yield Block(block_data.ref, "".join(content_parts))

            if block_data.is_init:
                extra_indent = block_data.indent.removeprefix(indent)
                ref = block_data.ref
                ref_str = ref.name.name if ref.name.namespace == namespace else str(ref.name)
                return f"{extra_indent}<<{ref_str}>>\n"
            else:
                return ""

    raise ParseError(pos, "unexpected end of file")
