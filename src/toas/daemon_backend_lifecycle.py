import sys
from .daemon import backend_lifecycle as _impl

sys.modules[__name__] = _impl
