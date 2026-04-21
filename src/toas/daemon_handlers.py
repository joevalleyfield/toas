import sys
from .daemon import handlers as _impl

sys.modules[__name__] = _impl
