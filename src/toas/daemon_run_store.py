import sys
from .daemon import run_store as _impl

sys.modules[__name__] = _impl
