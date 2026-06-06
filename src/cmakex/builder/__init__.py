"""CMake build operations package."""

from .cleaner import CleanInfo, Cleaner
from .operations import build, clean, configure, install, purge, uninstall

__all__ = [
    "build",
    "clean",
    "configure",
    "install",
    "purge",
    "uninstall",
    "Cleaner",
    "CleanInfo",
]
