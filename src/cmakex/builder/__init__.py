"""CMake build operations package."""

from .cleaner import CleanInfo, Cleaner
from .operations import build, clean, configure, install, purge

__all__ = [
    "build",
    "clean",
    "configure",
    "install",
    "purge",
    "Cleaner",
    "CleanInfo",
]
