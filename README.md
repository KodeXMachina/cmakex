# cmakex

A lightweight CMake build eXtension for the command line.

Wraps common CMake workflows and provides project introspection by parsing `CMakeLists.txt`.

## Features

- **`info`** — Parse `CMakeLists.txt` and display include directories, shared/static library output paths, and executables.
- **`configure`** — Create the build directory and run `cmake -S . -B build`.
- **`build`** / **`compile`** — Run `cmake --build`.
- **`clean`** — Run the `clean` target, or `--purge` to delete the entire build directory.

## Installation

```bash
pip install cmakex
```

Or install from source:

```bash
git clone https://github.com/winterYANGWT/cmakex.git
cd cmakex
pip install -e .
```

## Quick Start

```bash
# Inspect the current project
cmakex info

# Configure (creates ./build, runs cmake)
cmakex configure -B build -G Ninja -D CMAKE_BUILD_TYPE=Release

# Build
cmakex build -B build -j8

# Or use the alias
cmakex compile -j$(nproc)

# Clean (runs make clean / ninja clean)
cmakex clean

# Remove the build directory entirely
cmakex clean --purge
```

## Commands

### `cmakex info`

```
cmakex info [-S SOURCE_DIR] [-B BUILD_DIR]
```

Parses `CMakeLists.txt` (and recursively any `add_subdirectory()` files) and prints:

- Include directories from `include_directories()` / `target_include_directories()`
- Shared libraries (`.so`) with output paths
- Static libraries (`.a`) with output paths
- Executables with output paths

Output paths are resolved from `CMAKE_LIBRARY_OUTPUT_DIRECTORY`,
`CMAKE_ARCHIVE_OUTPUT_DIRECTORY`, `CMAKE_RUNTIME_OUTPUT_DIRECTORY`, and
`set_target_properties(… PROPERTIES …_OUTPUT_DIRECTORY …)`.

### `cmakex configure`

```
cmakex configure [-S SOURCE_DIR] [-B BUILD_DIR] [-G GENERATOR] [-D KEY=VALUE ...] [-- EXTRA_CMAKE_ARGS]
```

Creates the build directory and runs:

```
cmake -S <source_dir> -B <build_dir> [-G <generator>] [-D <key=value>...] [extra...]
```

### `cmakex build` / `cmakex compile`

```
cmakex build [-B BUILD_DIR] [-j N] [-t TARGET] [--config CONFIG] [-- EXTRA_ARGS]
```

Runs `cmake --build <build_dir>`. `compile` is an alias for `build`.

### `cmakex clean`

```
cmakex clean [-B BUILD_DIR] [--purge]
```

- Default: runs `cmake --build <build_dir> --target clean`
- `--purge`: removes `<build_dir>` entirely (`shutil.rmtree`)

## Global options

| Flag | Description |
|------|-------------|
| `-h`, `--help` | Show help |
| `--version` | Show version |
| `-v`, `--verbose` | Print the cmake command before running |

## Requirements

- Python ≥ 3.8
- CMake ≥ 3.13 (for `-S`/`-B` flag support)
- [click](https://click.palletsprojects.com/) ≥ 8.0

## License

MIT
