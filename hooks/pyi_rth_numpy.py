"""
Runtime hook para PyInstaller: precarga numpy para evitar
"ImportError: cannot load module more than once per process"
cuando pdf2docx -> algorithm.py -> numpy._core.multiarray.pyd.

Este bug ocurre porque el loader de PyInstaller intenta recargar
el modulo numpy._core.multiarray multiples veces desde distintos
puntos de importacion. Precargandolo al inicio del proceso lo
resolvemos.
"""
import os
import sys

# Forzar carga temprana de numpy antes que nada
try:
    import numpy  # noqa: F401
    import numpy.core  # noqa: F401
    import numpy._core  # noqa: F401
    import numpy._core.multiarray  # noqa: F401
except Exception:
    pass
