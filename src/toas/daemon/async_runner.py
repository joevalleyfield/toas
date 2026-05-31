from __future__ import annotations

# Compatibility adapter: async step worker ownership moved to runtime.
# Keep daemon import path as module alias for existing callers/tests.
import sys
from ..runtime import async_step_runtime_worker as _impl

sys.modules[__name__] = _impl
