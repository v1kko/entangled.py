from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Generator, Iterable

from ..io import AbstractFileCache, FileCache
from ..config import Config, ConfigUpdate
from ..hooks import HookBase, hooks, create_hook
from ..model import Content, ReferenceMap
from ..readers.yaml_header import get_config
from ..readers import read_yaml_header, process_token, collect_plain_text, raw_markdown, InputStream, run_reader

from functools import partial
from ..logging import logger

log = logger()

@dataclass
class Context:
    fs: AbstractFileCache = field(default_factory=FileCache)
    config: Config = Config()
    _hook_states: dict[str, HookBase.State] = field(default_factory=dict)
    _hooks: dict[str, HookBase] = field(default_factory=dict)

    def __post_init__(self):
        log.debug(f"context: hook config: {self.config.hook}")
        for h in self.config.hooks:
            if h not in self._hook_states:
                self._hook_states[h] = hooks[h].State()

            log.debug("context: loading hook %s", h)
            hook = create_hook(self.config, h, self._hook_states[h])
            if hook is None:
                continue
            self._hooks[h] = hook

    def __or__(self, update: ConfigUpdate | None) -> Context:
        return Context(self.fs, self.config | update, self._hook_states)

    @property
    def hooks(self) -> list[HookBase]:
        return sorted((self._hooks[h] for h in self.config.hooks),
                      key=lambda h: h.priority())

    @property
    def all_hooks(self) -> Iterable[HookBase]:
        return self._hooks.values()


def markdown(context: Context, refs: ReferenceMap, input: InputStream) -> Generator[Content, None, ConfigUpdate | None]:
    header = yield from read_yaml_header(input)
    update = get_config(header)
    context |= update

    yield from map(
        partial(process_token, context.hooks, refs),
        collect_plain_text(raw_markdown(context.config, input)))

    return update


def read_markdown(context: Context, refs: ReferenceMap, input: str) -> tuple[list[Content], ConfigUpdate | None]:
    return run_reader(partial(markdown, context, refs), input)
