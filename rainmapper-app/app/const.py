"""Compatibility wrapper for shared Rainmapper constants.

The implementation lives in `rainmapper_core.config.const`. This wrapper keeps
legacy imports such as `from const import _DATA_PATH` working while the core is
being reorganized. The constants intentionally use leading underscores, so the
wrapper re-exports them explicitly instead of relying on `import *` semantics.
"""

from rainmapper_core.config import const as _shared_const

for _name in dir(_shared_const):
    if not _name.startswith('__'):
        globals()[_name] = getattr(_shared_const, _name)

del _name
del _shared_const
