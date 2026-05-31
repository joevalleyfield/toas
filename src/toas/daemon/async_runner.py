from __future__ import annotations

# Compatibility adapter: async step worker ownership moved to runtime.
# Keep daemon import path as module alias for existing callers/tests.
# Sunset criteria:
# - remove after runtime-owned worker imports are canonical across daemon facades/tests
# - keep until transport parity suites prove no daemon-path identity dependency remains
import sys
from ..runtime import async_step_runtime_worker as _impl

sys.modules[__name__] = _impl
