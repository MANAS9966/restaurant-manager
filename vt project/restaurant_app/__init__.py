
from __future__ import annotations

import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
PACKAGE_ROOT_STR = str(PACKAGE_ROOT)

if PACKAGE_ROOT_STR not in sys.path:
    sys.path.insert(0, PACKAGE_ROOT_STR)

__all__ = ["PACKAGE_ROOT"]
