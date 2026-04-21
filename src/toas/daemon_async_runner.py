import sys
from .daemon import async_runner as _impl

sys.modules[__name__] = _impl
