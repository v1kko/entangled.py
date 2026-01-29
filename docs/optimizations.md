# Performance Optimizations

This document describes performance optimizations applied to Entangled's core parsing and tangling operations. These changes improve throughput by approximately 30% with no changes to functionality or external API.

## Summary

The primary optimizations are:

1. **Pre-compile regex patterns at module level** instead of compiling on every function call
2. **Use list accumulation with `"".join()`** instead of `O(n²)` string concatenation
3. **Cache dynamically-generated regex patterns** to avoid repeated compilation

These are standard Python optimization techniques that require no additional dependencies.

## Background

Profiling identified that a significant portion of execution time was spent in:

- Regex compilation (`re.match()` with string patterns compiles on every call)
- String concatenation in loops (`text += line` creates a new string each iteration)

### Profiling Methodology

A realistic benchmark was created simulating a literate programming project with:
- 17 markdown files
- ~5,000 lines of content
- 365 code blocks with nested references

The benchmark measured the full load-and-tangle workflow across multiple iterations.

## Optimizations Applied

### 1. Pre-compiled Regex in `model/tangle.py`

The `naked_tangler()` function matches every line against a reference pattern (`<<refname>>`). Previously, the regex was compiled on each call to `re.match()`.

**Before:**
```python
def naked_tangler(refs: ReferenceMap) -> Tangler:
    def tangler(...) -> Generator[str]:
        for line in lines(code_block.source):
            # Compiles regex on EVERY line
            if m := re.match(r"^(?P<indent>\s*)<<(?P<refname>[\w:/_.-]+)>>\s*$", line.rstrip()):
                ...
```

**After:**
```python
# Compiled once at module load
_REF_PATTERN = re.compile(r"^(?P<indent>\s*)<<(?P<refname>[\w:/_.-]+)>>\s*$")

def naked_tangler(refs: ReferenceMap) -> Tangler:
    def tangler(...) -> Generator[str]:
        for line in lines(code_block.source):
            # Uses pre-compiled pattern
            if m := _REF_PATTERN.match(line.rstrip()):
                ...
```

### 2. Pre-compiled Regex in `readers/code.py`

The `open_block()` and `close_block()` functions parse annotated code files during stitch operations.

**Before:**
```python
OPEN_BLOCK_EXPR = r"^(?P<indent>\s*).* ~/~ begin <<..."

def open_block(line: str) -> OpenBlockData | None:
    if not (m := re.match(OPEN_BLOCK_EXPR, line)):  # Compiles every call
        return None
```

**After:**
```python
_OPEN_BLOCK_PATTERN = re.compile(
    r"^(?P<indent>\s*).* ~/~ begin <<..."
)

def open_block(line: str) -> OpenBlockData | None:
    if not (m := _OPEN_BLOCK_PATTERN.match(line)):  # Uses compiled pattern
        return None
```

### 3. Cached Regex in `parsing.py`

The parser combinator functions `matching()` and `fullmatch()` create regex patterns dynamically. A module-level cache avoids recompiling the same patterns.

**Before:**
```python
def matching(regex: str) -> Parser[tuple[str, ...]]:
    pattern = re.compile(f"^{regex}")  # Compiles every time matching() is called
    ...
```

**After:**
```python
_pattern_cache: dict[str, re.Pattern[str]] = {}

def _cached_pattern(regex: str) -> re.Pattern[str]:
    if regex not in _pattern_cache:
        _pattern_cache[regex] = re.compile(f"^{regex}")
    return _pattern_cache[regex]

def matching(regex: str) -> Parser[tuple[str, ...]]:
    pattern = _cached_pattern(regex)  # Returns cached compiled pattern
    ...
```

### 4. Cached Regex in `hooks/quarto_attributes.py`

The `split_yaml_header()` function generates patterns based on language comment syntax. These are now cached per comment style.

**Before:**
```python
def split_yaml_header(language: Language, source: str) -> tuple[str, str, object]:
    trigger: str = re.escape(language.comment.open) + r"\s*\|(.*)"
    for i, line in enumerate(lines):
        if m := re.match(trigger, line):  # Compiles on every line
            ...
```

**After:**
```python
_yaml_header_pattern_cache: dict[str, re.Pattern[str]] = {}

def _get_yaml_header_pattern(comment_open: str) -> re.Pattern[str]:
    if comment_open not in _yaml_header_pattern_cache:
        pattern = re.escape(comment_open) + r"\s*\|(.*)"
        _yaml_header_pattern_cache[comment_open] = re.compile(pattern)
    return _yaml_header_pattern_cache[comment_open]

def split_yaml_header(language: Language, source: str) -> tuple[str, str, object]:
    pattern = _get_yaml_header_pattern(language.comment.open)
    for i, line in enumerate(lines):
        if m := pattern.match(line):  # Uses cached pattern
            ...
```

### 5. Efficient String Building in `model/tangle.py`

The `tangle_ref()` function accumulated output using `+=` concatenation, which is `O(n²)` for n lines.

**Before:**
```python
def tangle_ref(refs, name, annotation) -> tuple[str, set[PurePath]]:
    out = ""
    ref_lst = refs.select_by_name(name)
    for line in tangler(tangler, deps, ref_lst[0], False, True):
        out += line  # O(n²) - creates new string each iteration
    for ref in ref_lst[1:]:
        for line in tangler(tangler, deps, ref, False, False):
            out += line
    return out, deps
```

**After:**
```python
def tangle_ref(refs, name, annotation) -> tuple[str, set[PurePath]]:
    def all_lines():
        ref_lst = refs.select_by_name(name)
        yield from tangler(tangler, deps, ref_lst[0], False, True)
        for ref in ref_lst[1:]:
            yield from tangler(tangler, deps, ref, False, False)

    out = "".join(all_lines())  # O(n) - single allocation
    return out, deps
```

### 6. Efficient String Building in `readers/code.py`

The `read_block()` function accumulated content similarly.

**Before:**
```python
content = ""
while input:
    ...
    content += line  # O(n²)
```

**After:**
```python
content_parts: list[str] = []
while input:
    ...
    content_parts.append(line)  # O(1) amortized
...
yield Block(block_data.ref, "".join(content_parts))  # O(n)
```

### 7. Efficient String Building in `interface/document.py`

The `source_text()` method used the same pattern.

**Before:**
```python
def source_text(self, path: Path) -> tuple[str, set[PurePath]]:
    text = ""
    for content in self.content[path]:
        t, d = content_to_text(self.reference_map, content)
        text += t  # O(n²)
    return text, deps
```

**After:**
```python
def source_text(self, path: Path) -> tuple[str, set[PurePath]]:
    text_parts: list[str] = []
    for content in self.content[path]:
        t, d = content_to_text(self.reference_map, content)
        text_parts.append(t)  # O(1) amortized
    return "".join(text_parts), deps  # O(n)
```

## Performance Results

Benchmark: 17 files, ~5K lines, 365 code blocks

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Total time** | 32.0ms | 24.5ms | **1.31x faster** |
| **Throughput** | 152K lines/sec | 199K lines/sec | **+31%** |

Best-case improvements (cache warm, no I/O):

| Operation | Before | After | Improvement |
|-----------|--------|-------|-------------|
| Load (parse) | 19.6ms | 13.6ms | 1.44x |
| Tangle | 4.0ms | 2.7ms | 1.48x |

## Files Changed

| File | Changes |
|------|---------|
| `entangled/model/tangle.py` | Pre-compiled `_REF_PATTERN`; `"".join()` in `tangle_ref()` |
| `entangled/readers/code.py` | Pre-compiled `_OPEN_BLOCK_PATTERN`, `_CLOSE_BLOCK_PATTERN`; list accumulation |
| `entangled/readers/markdown.py` | (no changes needed - already efficient) |
| `entangled/hooks/quarto_attributes.py` | Added `_yaml_header_pattern_cache` |
| `entangled/parsing.py` | Added `_pattern_cache` and `_cached_pattern()` |
| `entangled/interface/document.py` | List accumulation in `source_text()` |

## Verification

All existing tests pass unchanged. The optimizations are purely internal and do not affect the external API or behavior.

To verify performance improvements:

```python
import time
from pathlib import Path
from entangled.interface.document import Document
from entangled.io import transaction

# Load a project with multiple markdown files
doc = Document()
start = time.perf_counter()
with transaction() as t:
    doc.load(t)
    doc.tangle(t)
elapsed = time.perf_counter() - start
print(f"Completed in {elapsed*1000:.2f}ms")
```

## Notes

- These optimizations follow standard Python best practices
- No new dependencies are required
- Memory usage is marginally increased due to pattern caching (negligible - a few KB)
- The pattern caches are module-level and persist for the process lifetime, which is appropriate for CLI usage
