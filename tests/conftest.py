from pathlib import Path
from uuid import uuid4

import pytest


@pytest.fixture
def tmp_path():
    # Default pytest temp directories use mode=0700, which removes inherited
    # Windows sandbox ACLs on this host. Preserve inheritance for test scratch.
    root = Path(__file__).resolve().parents[1] / "data" / "test-work" / uuid4().hex
    root.mkdir(parents=True)
    return root
