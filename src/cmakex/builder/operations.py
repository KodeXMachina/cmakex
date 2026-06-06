"""Core build operations — interfaces to cmake commands."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import List, Optional


def _cmake() -> str:
    """Return path to cmake executable, or raise if not found."""
    exe = shutil.which("cmake")
    if exe is None:
        raise FileNotFoundError(
            "cmake not found in PATH. Please install CMake and add it to your PATH."
        )
    return exe


def configure(
    source_dir: Path,
    build_dir: Path,
    generator: Optional[str] = None,
    cmake_args: Optional[List[str]] = None,
    verbose: bool = False,
) -> int:
    """Create *build_dir* and run ``cmake -S source_dir -B build_dir [args]``.

    Returns the cmake process exit code.
    """
    build_dir.mkdir(parents=True, exist_ok=True)
    cmake = _cmake()

    cmd: List[str] = [cmake, "-S", str(source_dir), "-B", str(build_dir)]
    if generator:
        cmd += ["-G", generator]
    if cmake_args:
        cmd += cmake_args

    if verbose:
        print(f"$ {' '.join(cmd)}")

    return subprocess.run(cmd).returncode


def build(
    build_dir: Path,
    jobs: Optional[int] = None,
    target: Optional[str] = None,
    config: Optional[str] = None,
    extra_args: Optional[List[str]] = None,
    verbose: bool = False,
) -> int:
    """Run ``cmake --build build_dir [options]``.

    Returns the cmake process exit code.
    """
    cmake = _cmake()

    cmd: List[str] = [cmake, "--build", str(build_dir)]
    if config:
        cmd += ["--config", config]
    if jobs:
        cmd += ["--parallel", str(jobs)]
    if target:
        cmd += ["--target", target]
    if extra_args:
        cmd += ["--", *extra_args]

    if verbose:
        print(f"$ {' '.join(cmd)}")

    return subprocess.run(cmd).returncode


def clean(build_dir: Path, verbose: bool = False) -> int:
    """Run ``cmake --build build_dir --target clean``.

    Returns the cmake process exit code.
    """
    cmake = _cmake()
    cmd = [cmake, "--build", str(build_dir), "--target", "clean"]

    if verbose:
        print(f"$ {' '.join(cmd)}")

    return subprocess.run(cmd).returncode


def install(
    build_dir: Path,
    prefix: Optional[str] = None,
    config: Optional[str] = None,
    component: Optional[str] = None,
    strip: bool = False,
    verbose: bool = False,
) -> int:
    """Run ``cmake --install build_dir [options]``.

    Returns the cmake process exit code.
    """
    cmake = _cmake()

    cmd: List[str] = [cmake, "--install", str(build_dir)]
    if prefix:
        cmd += ["--prefix", prefix]
    if config:
        cmd += ["--config", config]
    if component:
        cmd += ["--component", component]
    if strip:
        cmd.append("--strip")

    if verbose:
        print(f"$ {' '.join(cmd)}")

    return subprocess.run(cmd).returncode


def uninstall(build_dir: Path, verbose: bool = False) -> int:
    """Remove files listed in *build_dir*/install_manifest.txt.

    CMake writes this manifest during ``cmake --install``.  Each line is an
    absolute path to an installed file.  Empty directories left behind after
    removal are pruned as well.

    Returns 0 on success, 1 if the manifest does not exist.
    """
    manifest = build_dir / "install_manifest.txt"
    if not manifest.exists():
        return 1

    installed: List[Path] = []
    with manifest.open() as fh:
        for line in fh:
            p = Path(line.strip())
            if p and p.is_file():
                installed.append(p)

    dirs_to_check: set[Path] = set()
    for path in installed:
        if verbose:
            print(f"Removing {path}")
        try:
            path.unlink()
            dirs_to_check.add(path.parent)
        except OSError as exc:
            print(f"Warning: could not remove {path}: {exc}")

    # Prune empty directories bottom-up
    for d in sorted(dirs_to_check, key=lambda p: len(p.parts), reverse=True):
        try:
            if d.is_dir() and not any(d.iterdir()):
                d.rmdir()
                if verbose:
                    print(f"Removing empty directory {d}")
        except OSError:
            pass

    return 0


def purge(build_dir: Path, verbose: bool = False) -> int:
    """Remove *build_dir* entirely.

    Returns 0 on success.
    """
    if verbose:
        print(f"Removing {build_dir}")
    shutil.rmtree(build_dir)
    return 0
