import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))


@pytest.fixture(autouse=True)
def _chdir_tmp(tmp_path, monkeypatch):
    # Журнал подій і файли виводу за замовчуванням пишуться у ./output.
    monkeypatch.chdir(tmp_path)
