from pathlib import Path
from entangled.commands.tangle import do_tangle
from entangled.io import TransactionMode
from entangled.io.virtual import VirtualFS
import pprint
import json

fs = VirtualFS.from_dict({
    "test.md": """
    ``` {.python file=test.py}
    print("Hello, World!")
    ```
    """
})


def test_issue_83():
    do_tangle(fs=fs)
    assert Path(".entangled/filedb.json") in fs
    assert Path("test.py") in fs
    assert "print(\"Hello, World!\")" in fs[Path("test.py")].content
    del fs[Path("test.py")]
    do_tangle(fs=fs, mode=TransactionMode.RESETDB)
    assert Path("test.py") not in fs
    do_tangle(fs=fs)
    assert Path("test.py") in fs
