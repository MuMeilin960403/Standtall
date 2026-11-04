from __future__ import annotations

import os
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("STANDTALL_DATA_DIR", tempfile.mkdtemp(prefix="standtall-tests-"))
