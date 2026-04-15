"""Main CMake parser — orchestrates lexing, variable resolution, and command handling."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Set

from .lexer import CMakeLexer
from .models import CMakeInfo, ExecutableInfo, LibraryInfo
from .resolver import VariableResolver


class CMakeParser:
    """Parse CMakeLists.txt files and extract build information."""

    LIB_TYPE_KEYWORDS = {
        "SHARED",
        "STATIC",
        "MODULE",
        "INTERFACE",
        "OBJECT",
        "ALIAS",
        "IMPORTED",
    }

    INCLUDE_SKIP_KEYWORDS = {
        "BEFORE",
        "AFTER",
        "SYSTEM",
        "INTERFACE",
        "PUBLIC",
        "PRIVATE",
    }

    def __init__(self, cmake_file: Path):
        """Initialize parser for a specific CMakeLists.txt file."""
        self.cmake_file = cmake_file.resolve()
        self.source_dir = self.cmake_file.parent
        self.info = CMakeInfo(source_dir=self.source_dir)

        # Initialize variable resolver with common CMake variables
        self.resolver = VariableResolver(
            {
                "CMAKE_SOURCE_DIR": str(self.source_dir),
                "CMAKE_CURRENT_SOURCE_DIR": str(self.source_dir),
                "PROJECT_SOURCE_DIR": str(self.source_dir),
                "CMAKE_BINARY_DIR": "<build>",
                "CMAKE_CURRENT_BINARY_DIR": "<build>",
                "PROJECT_BINARY_DIR": "<build>",
            }
        )

        # Track target properties: target name -> {property: value}
        self.target_props: Dict[str, Dict[str, str]] = {}

    def parse(self) -> CMakeInfo:
        """Parse the CMakeLists.txt file."""
        if not self.cmake_file.exists():
            return self.info

        content = self.cmake_file.read_text(encoding="utf-8", errors="replace")
        lexer = CMakeLexer(content)

        for cmd_name, raw_args in lexer.extract_commands():
            args = lexer.parse_args(raw_args)
            self._handle_command(cmd_name.upper(), args)

        # Apply target-specific properties
        self._apply_target_properties()
        self.info.deduplicate()
        return self.info

    def _handle_command(self, cmd: str, args: list[str]) -> None:
        """Dispatch command to appropriate handler."""
        handlers = {
            "SET": self._handle_set,
            "INCLUDE_DIRECTORIES": self._handle_include_directories,
            "TARGET_INCLUDE_DIRECTORIES": self._handle_target_include_directories,
            "ADD_LIBRARY": self._handle_add_library,
            "ADD_EXECUTABLE": self._handle_add_executable,
            "SET_TARGET_PROPERTIES": self._handle_set_target_properties,
            "ADD_SUBDIRECTORY": self._handle_add_subdirectory,
        }

        handler = handlers.get(cmd)
        if handler:
            handler(args)

    def _handle_set(self, args: list[str]) -> None:
        """Handle SET() command."""
        if len(args) >= 2:
            val_parts: list[str] = []
            for a in args[1:]:
                if a == "CACHE":
                    break
                val_parts.append(a)
            value = (
                ";".join(val_parts)
                if len(val_parts) > 1
                else (val_parts[0] if val_parts else "")
            )
            self.resolver.set(args[0], self.resolver.resolve(value))
        elif len(args) == 1:
            self.resolver.unset(args[0])

    def _handle_include_directories(self, args: list[str]) -> None:
        """Handle INCLUDE_DIRECTORIES() command."""
        for arg in args:
            if arg not in self.INCLUDE_SKIP_KEYWORDS and arg:
                self.info.include_dirs.append(self.resolver.resolve(arg))

    def _handle_target_include_directories(self, args: list[str]) -> None:
        """Handle TARGET_INCLUDE_DIRECTORIES() command."""
        if len(args) >= 2:
            for arg in args[1:]:
                if arg not in self.INCLUDE_SKIP_KEYWORDS and arg:
                    self.info.include_dirs.append(self.resolver.resolve(arg))

    def _handle_add_library(self, args: list[str]) -> None:
        """Handle ADD_LIBRARY() command."""
        if not args:
            return

        lib_name = args[0]
        lib_type = "STATIC"  # CMake default when BUILD_SHARED_LIBS is OFF

        for a in args[1:]:
            if a in self.LIB_TYPE_KEYWORDS:
                lib_type = a
                break

        if lib_type in ("ALIAS", "IMPORTED"):
            return

        lib = LibraryInfo(name=lib_name, lib_type=lib_type, source_dir=self.source_dir)

        # Set default output directory from CMAKE_* variables
        out_var = (
            "CMAKE_LIBRARY_OUTPUT_DIRECTORY"
            if lib_type in ("SHARED", "MODULE")
            else "CMAKE_ARCHIVE_OUTPUT_DIRECTORY"
        )
        lib.output_dir = self.resolver.get(out_var)

        self.target_props.setdefault(lib_name, {})
        self.info.libraries.append(lib)

    def _handle_add_executable(self, args: list[str]) -> None:
        """Handle ADD_EXECUTABLE() command."""
        if not args:
            return

        exe_name = args[0]
        if len(args) > 1 and args[1] in ("IMPORTED", "ALIAS"):
            return

        exe = ExecutableInfo(name=exe_name, source_dir=self.source_dir)
        exe.output_dir = self.resolver.get("CMAKE_RUNTIME_OUTPUT_DIRECTORY")

        self.target_props.setdefault(exe_name, {})
        self.info.executables.append(exe)

    def _handle_set_target_properties(self, args: list[str]) -> None:
        """Handle SET_TARGET_PROPERTIES() command."""
        if "PROPERTIES" not in args:
            return

        sep = args.index("PROPERTIES")
        targets = args[:sep]
        pairs = args[sep + 1 :]

        props: Dict[str, str] = {}
        for i in range(0, len(pairs) - 1, 2):
            props[pairs[i]] = self.resolver.resolve(pairs[i + 1])

        for t in targets:
            self.target_props.setdefault(t, {}).update(props)

    def _handle_add_subdirectory(self, args: list[str]) -> None:
        """Handle ADD_SUBDIRECTORY() command — recursively parse subdirectory."""
        if args:
            sub_path = self.source_dir / self.resolver.resolve(args[0])
            sub_cmake = sub_path / "CMakeLists.txt"
            if sub_cmake.exists():
                sub_info = parse_cmake_file(sub_cmake, self._visited)
                self.info.include_dirs.extend(sub_info.include_dirs)
                self.info.libraries.extend(sub_info.libraries)
                self.info.executables.extend(sub_info.executables)

    def _apply_target_properties(self) -> None:
        """Apply set_target_properties() to library and executable targets."""
        for lib in self.info.libraries:
            props = self.target_props.get(lib.name, {})
            if "OUTPUT_NAME" in props:
                lib.output_name = props["OUTPUT_NAME"]

            dir_key = (
                "LIBRARY_OUTPUT_DIRECTORY"
                if lib.lib_type in ("SHARED", "MODULE")
                else "ARCHIVE_OUTPUT_DIRECTORY"
            )
            if dir_key in props:
                lib.output_dir = props[dir_key]

        for exe in self.info.executables:
            props = self.target_props.get(exe.name, {})
            if "OUTPUT_NAME" in props:
                exe.output_name = props["OUTPUT_NAME"]
            if "RUNTIME_OUTPUT_DIRECTORY" in props:
                exe.output_dir = props["RUNTIME_OUTPUT_DIRECTORY"]


def parse_cmake_file(
    cmake_file: Path,
    _visited: Optional[Set[Path]] = None,
) -> CMakeInfo:
    """Parse *cmake_file* (and add_subdirectory() children) and return CMakeInfo.

    This is the main entry point for parsing CMake files.
    """
    cmake_file = cmake_file.resolve()

    if _visited is None:
        _visited = set()

    if cmake_file in _visited or not cmake_file.exists():
        return CMakeInfo(source_dir=cmake_file.parent)

    _visited.add(cmake_file)

    parser = CMakeParser(cmake_file)
    parser._visited = _visited  # Pass visited set to handle recursion
    return parser.parse()
