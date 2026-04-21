import sys
from .daemon import request_contract as _impl

sys.modules[__name__] = _impl
