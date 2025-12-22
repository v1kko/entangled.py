from entangled.config import Config, get_input_files
from pathlib import Path
from contextlib import chdir

from entangled.io import FileCache


def test_input_files(tmpdir: Path):
    tmpdir = Path(tmpdir)
    (tmpdir / "a").mkdir()
    (tmpdir / "b").mkdir()
    (tmpdir / "a" / "x").touch()
    (tmpdir / "a" / "y").touch()
    (tmpdir / "b" / "x").touch()
    with chdir(tmpdir):
        fs = FileCache()
        assert get_input_files(fs, Config(watch_list=["**/x"])) == [Path("a/x"), Path("b/x")]
        assert get_input_files(fs, Config(watch_list=["a/*"])) == [Path("a/x"), Path("a/y")]
        assert get_input_files(fs, Config(watch_list=["**/*"], ignore_list=["**/y"])) == \
            [Path("a/x"), Path("b/x")]
