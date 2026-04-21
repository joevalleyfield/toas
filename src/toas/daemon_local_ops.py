import sys
from .daemon import local_ops as _impl

sys.modules[__name__] = _impl
