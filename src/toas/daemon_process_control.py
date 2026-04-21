import sys
from .daemon import process_control as _impl

sys.modules[__name__] = _impl
