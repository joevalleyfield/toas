import sys
from .daemon import op_dispatch as _impl

sys.modules[__name__] = _impl
