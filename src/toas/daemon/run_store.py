from __future__ import annotations

# Compatibility adapter: async activity store ownership moved to runtime.
# Keep daemon import path as an alias to preserve monkeypatch/test behavior.
import sys
from ..runtime import async_activity_store_impl as _impl

sys.modules[__name__] = _impl
