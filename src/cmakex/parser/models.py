"""Data models for CMake project information."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set


@dataclass
class LibraryInfo:
    """A library target defined with add_library()."""

    name: str
    lib_type: str  # SHARED | STATIC | MODULE | INTERFACE | OBJECT
    output_dir: Optional[str] = None
    output_name: Optional[str] = None
    source_dir: Optional[Path] = None  # Directory where this library was defined

    def filename(self) -> str:
        """Best-effort output filename for this library."""
        base = self.output_name or self.name
        if self.lib_type == "SHARED":
            return f"lib{base}.so"
        if self.lib_type == "STATIC":
            return f"lib{base}.a"
        if self.lib_type == "MODULE":
            return f"lib{base}.so"
        return base


@dataclass
class ExecutableInfo:
    """An executable target defined with add_executable()."""

    name: str
    output_dir: Optional[str] = None
    output_name: Optional[str] = None
    source_dir: Optional[Path] = None  # Directory where this executable was defined

    def filename(self) -> str:
        return self.output_name or self.name


@dataclass
class CMakeInfo:
    """Aggregated information parsed from one or more CMakeLists.txt files."""

    source_dir: Path = field(default_factory=Path)
    include_dirs: List[str] = field(default_factory=list)
    libraries: List[LibraryInfo] = field(default_factory=list)
    executables: List[ExecutableInfo] = field(default_factory=list)

    @property
    def shared_libs(self) -> List[LibraryInfo]:
        """Get list of shared and module libraries."""
        return [lib for lib in self.libraries if lib.lib_type in ("SHARED", "MODULE")]

    @property
    def static_libs(self) -> List[LibraryInfo]:
        """Get list of static libraries."""
        return [lib for lib in self.libraries if lib.lib_type == "STATIC"]

    def deduplicate(self) -> None:
        """Remove duplicate include directories while preserving order."""
        seen: Set[str] = set()
        unique: List[str] = []
        for d in self.include_dirs:
            if d not in seen:
                seen.add(d)
                unique.append(d)
        self.include_dirs = unique
