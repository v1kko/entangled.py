from entangled.config import read_config, read_config_from_toml, Config
from entangled.config.version import Version
from entangled.errors.user import UserError

from pathlib import Path
from contextlib import chdir

import pytest
import logging

from entangled.io import FileCache


pyproject_toml = """
[tool.entangled]
version = "100"
style = "basic"
""".lstrip()


def test_pyproject_toml(tmp_path: Path, caplog):
    with chdir(tmp_path):
        fs = FileCache()
        assert read_config(fs) is None

        filename = Path("pyproject.toml")
        filename.write_text(pyproject_toml, encoding="utf-8")

        config = Config() | read_config_from_toml(fs, filename, "tool.entangled")
        assert config.version == Version((100,))

        with caplog.at_level(logging.DEBUG):
            _ = read_config_from_toml(fs, filename, "tool.not-entangled")
            assert "tool.not-entangled" in caplog.text

        with pytest.raises(UserError):
            _ = read_config_from_toml(fs, filename, None)

        assert read_config_from_toml(fs, tmp_path / "entangled.toml") is None

    with chdir(tmp_path):
        fs = FileCache()
        cfg = Config() | read_config(fs)
        assert cfg.version == Version((100,))


entangled_toml = """
version = "42"
annotation = "naked"

[[languages]]
name = "Kernel"
identifiers = ["kernel"]
comment = {"open" = ";"}
""".lstrip()


def test_entangled_toml(tmp_path: Path, caplog):
    with chdir(tmp_path):
        fs = FileCache()
        assert read_config(fs) is None

    (tmp_path / "entangled.toml").write_text(entangled_toml, encoding="utf-8")

    with chdir(tmp_path):
        fs = FileCache()
        cfg = Config() | read_config(fs)
        assert cfg.version == Version((42,))
        lang = cfg.get_language("kernel")
        assert lang
        assert lang.name == "Kernel"


entangled_toml_error = """
no_version_given = ""
""".lstrip()


def test_entangled_toml_error(tmp_path: Path, caplog):
    (tmp_path / "entangled.toml").write_text(entangled_toml_error, encoding="utf-8")
    with chdir(tmp_path):
        with pytest.raises(UserError):
            fs = FileCache()
            _ = Config() | read_config(fs)
