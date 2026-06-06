"""cli.py — Click command-line interface for cmakex."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import click

from .builder import Cleaner, build, clean, configure, install, purge, uninstall
from .parser import parse_cmake_file

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


# ---------------------------------------------------------------------------
# Top-level group
# ---------------------------------------------------------------------------


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(package_name="cmakex")
def cli() -> None:
    """cmakex — CMake build eXtension.

    Wraps common CMake workflows and provides project introspection.

    \b
    Typical workflow:
      cmakex info
      cmakex configure -B build -D CMAKE_BUILD_TYPE=Release
      cmakex build -B build -j8
      cmakex clean -B build
    """


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_cmake_file(source_dir: str) -> Path:
    path = Path(source_dir) / "CMakeLists.txt"
    if not path.exists():
        click.echo(f"Error: CMakeLists.txt not found in '{source_dir}'", err=True)
        sys.exit(1)
    return path


# ---------------------------------------------------------------------------
# info
# ---------------------------------------------------------------------------


@cli.command("info")
@click.option(
    "-S",
    "--source-dir",
    default=".",
    show_default=True,
    help="Source directory containing CMakeLists.txt.",
)
@click.option(
    "-B",
    "--build-dir",
    default="build",
    show_default=True,
    help="Build directory (used for display when output dir is not set).",
)
def cmd_info(source_dir: str, build_dir: str) -> None:
    """Show include directories and library/executable output paths.

    Parses CMakeLists.txt in the source directory (and any subdirectories
    added via add_subdirectory) to extract:

    \b
      - Include directories
      - Shared libraries (.so)
      - Static libraries (.a)
      - Executables
    """
    cmake_file = _require_cmake_file(source_dir)
    info = parse_cmake_file(cmake_file)

    root_dir = cmake_file.parent.resolve()

    click.echo(f"Source : {root_dir}")
    click.echo()

    # Include directories
    click.echo(click.style("Include Directories:", bold=True))
    if info.include_dirs:
        for d in info.include_dirs:
            click.echo(f"  {d}")
    else:
        click.echo("  (none detected)")
    click.echo()

    # Shared libraries
    click.echo(click.style("Shared Libraries (.so):", bold=True))
    if info.shared_libs:
        for lib in info.shared_libs:
            out = lib.output_dir or f"{build_dir}"
            src_info = ""
            if lib.source_dir and lib.source_dir != root_dir:
                rel_path = (
                    lib.source_dir.relative_to(root_dir)
                    if lib.source_dir.is_relative_to(root_dir)
                    else lib.source_dir
                )
                src_info = f"  [{rel_path}]"
            click.echo(f"  {lib.name:<30}  {out}/{lib.filename()}{src_info}")
    else:
        click.echo("  (none detected)")
    click.echo()

    # Static libraries
    click.echo(click.style("Static Libraries (.a):", bold=True))
    if info.static_libs:
        for lib in info.static_libs:
            out = lib.output_dir or f"{build_dir}"
            src_info = ""
            if lib.source_dir and lib.source_dir != root_dir:
                rel_path = (
                    lib.source_dir.relative_to(root_dir)
                    if lib.source_dir.is_relative_to(root_dir)
                    else lib.source_dir
                )
                src_info = f"  [{rel_path}]"
            click.echo(f"  {lib.name:<30}  {out}/{lib.filename()}{src_info}")
    else:
        click.echo("  (none detected)")
    click.echo()

    # Executables
    click.echo(click.style("Executables:", bold=True))
    if info.executables:
        for exe in info.executables:
            out = exe.output_dir or f"{build_dir}"
            src_info = ""
            if exe.source_dir and exe.source_dir != root_dir:
                rel_path = (
                    exe.source_dir.relative_to(root_dir)
                    if exe.source_dir.is_relative_to(root_dir)
                    else exe.source_dir
                )
                src_info = f"  [{rel_path}]"
            click.echo(f"  {exe.name:<30}  {out}/{exe.filename()}{src_info}")
    else:
        click.echo("  (none detected)")


# ---------------------------------------------------------------------------
# configure
# ---------------------------------------------------------------------------


@cli.command("configure")
@click.option(
    "-S",
    "--source-dir",
    default=".",
    show_default=True,
    help="Source directory containing CMakeLists.txt.",
)
@click.option(
    "-B",
    "--build-dir",
    default="build",
    show_default=True,
    help="Build directory to create.",
)
@click.option(
    "-G",
    "--generator",
    default=None,
    metavar="GEN",
    help='CMake generator, e.g. "Ninja" or "Unix Makefiles".',
)
@click.option(
    "-D",
    "defines",
    multiple=True,
    metavar="KEY=VALUE",
    help="Set a CMake cache variable (repeatable).",
)
@click.option("-v", "--verbose", is_flag=True, help="Print the cmake command.")
@click.argument("extra", nargs=-1)
def cmd_configure(
    source_dir: str,
    build_dir: str,
    generator: Optional[str],
    defines: tuple,
    verbose: bool,
    extra: tuple,
) -> None:
    """Create build directory and run cmake configuration.

    Extra arguments after -- are forwarded verbatim to cmake.

    \b
    Examples:
      cmakex configure
      cmakex configure -B build -G Ninja -D CMAKE_BUILD_TYPE=Release
      cmakex configure -- -DCMAKE_VERBOSE_MAKEFILE=ON
    """
    source = Path(source_dir).resolve()
    if not (source / "CMakeLists.txt").exists():
        click.echo(f"Error: CMakeLists.txt not found in '{source}'", err=True)
        sys.exit(1)

    cmake_args = [f"-D{d}" for d in defines]
    cmake_args += list(extra)

    try:
        rc = configure(
            source_dir=source,
            build_dir=Path(build_dir),
            generator=generator,
            cmake_args=cmake_args or None,
            verbose=verbose,
        )
    except FileNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    sys.exit(rc)


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------


@cli.command("build")
@click.option(
    "-B",
    "--build-dir",
    default="build",
    show_default=True,
    help="Build directory.",
)
@click.option(
    "-j",
    "--jobs",
    default=None,
    type=int,
    metavar="N",
    help="Parallel jobs (default: auto).",
)
@click.option("-t", "--target", default=None, help="Build target.")
@click.option(
    "--config",
    default=None,
    help="Build configuration, e.g. Release or Debug.",
)
@click.option("-v", "--verbose", is_flag=True, help="Print the cmake command.")
@click.argument("extra", nargs=-1)
def cmd_build(
    build_dir: str,
    jobs: Optional[int],
    target: Optional[str],
    config: Optional[str],
    verbose: bool,
    extra: tuple,
) -> None:
    """Build the project.

    Extra arguments after -- are forwarded to the underlying build tool
    (make, ninja, …).

    \b
    Examples:
      cmakex build
      cmakex build -j8
      cmakex build -t my_library --config Release
      cmakex build -- VERBOSE=1
    """
    bd = Path(build_dir)
    if not bd.exists():
        click.echo(
            f"Error: build directory '{build_dir}' does not exist. "
            "Run 'cmakex configure' first.",
            err=True,
        )
        sys.exit(1)

    try:
        rc = build(
            build_dir=bd,
            jobs=jobs,
            target=target,
            config=config,
            extra_args=list(extra) or None,
            verbose=verbose,
        )
    except FileNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    sys.exit(rc)


# ---------------------------------------------------------------------------
# compile  (alias for build)
# ---------------------------------------------------------------------------


@cli.command("compile")
@click.option(
    "-B",
    "--build-dir",
    default="build",
    show_default=True,
    help="Build directory.",
)
@click.option(
    "-j",
    "--jobs",
    default=None,
    type=int,
    metavar="N",
    help="Parallel jobs (default: auto).",
)
@click.option("-t", "--target", default=None, help="Build target.")
@click.option(
    "--config",
    default=None,
    help="Build configuration, e.g. Release or Debug.",
)
@click.option("-v", "--verbose", is_flag=True, help="Print the cmake command.")
@click.argument("extra", nargs=-1)
def cmd_compile(
    build_dir: str,
    jobs: Optional[int],
    target: Optional[str],
    config: Optional[str],
    verbose: bool,
    extra: tuple,
) -> None:
    """Compile the project (alias for 'build').

    \b
    Examples:
      cmakex compile
      cmakex compile -j$(nproc)
    """
    bd = Path(build_dir)
    if not bd.exists():
        click.echo(
            f"Error: build directory '{build_dir}' does not exist. "
            "Run 'cmakex configure' first.",
            err=True,
        )
        sys.exit(1)

    try:
        rc = build(
            build_dir=bd,
            jobs=jobs,
            target=target,
            config=config,
            extra_args=list(extra) or None,
            verbose=verbose,
        )
    except FileNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    sys.exit(rc)


# ---------------------------------------------------------------------------
# clean
# ---------------------------------------------------------------------------


@cli.command("clean")
@click.option(
    "-B",
    "--build-dir",
    default="build",
    show_default=True,
    help="Build directory.",
)
@click.option(
    "--purge",
    "do_purge",
    is_flag=True,
    help="Remove the entire build directory instead of running the clean target.",
)
@click.option("-v", "--verbose", is_flag=True, help="Print the cmake command.")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation prompt.")
def cmd_clean(build_dir: str, do_purge: bool, verbose: bool, yes: bool) -> None:
    """Clean build artifacts.

    By default runs ``cmake --build <build_dir> --target clean``.
    Use --purge to delete the entire build directory.

    \b
    Examples:
      cmakex clean
      cmakex clean --purge
      cmakex clean -y  # Skip confirmation
    """
    bd = Path(build_dir)

    if not bd.exists():
        click.echo(f"Build directory '{build_dir}' does not exist, nothing to clean.")
        return

    # Get list of files/directories that will be removed
    try:
        cleaner = Cleaner(bd)
        if do_purge:
            clean_info = cleaner.get_purge_targets()
        else:
            clean_info = cleaner.get_clean_targets()
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    # Display what will be removed
    if clean_info.directories or clean_info.files or clean_info.installed_dirs or clean_info.installed_files:
        click.echo(click.style("The following will be removed:", bold=True))
        click.echo()

        if clean_info.directories:
            click.echo(click.style("Directories:", fg="yellow"))
            for d in clean_info.directories:
                click.echo(f"  {d}")
            click.echo()

        if clean_info.files:
            click.echo(
                click.style(f"Files ({len(clean_info.files)} total):", fg="yellow")
            )
            # Limit file display to avoid overwhelming output
            display_limit = 50
            for f in clean_info.files[:display_limit]:
                click.echo(f"  {f}")
            if len(clean_info.files) > display_limit:
                click.echo(
                    f"  ... and {len(clean_info.files) - display_limit} more files"
                )
            click.echo()

        if clean_info.installed_dirs or clean_info.installed_files:
            installed_total = clean_info.installed_dirs.__len__() + clean_info.installed_files.__len__()
            click.echo(
                click.style(
                    f"Installed (from install_manifest.txt):",
                    fg="yellow",
                )
            )
            for d in clean_info.installed_dirs:
                click.echo(f"  {d}/")
            display_limit = 50
            shown = 0
            for f in clean_info.installed_files[:display_limit]:
                click.echo(f"  {f}")
                shown += 1
            remaining = len(clean_info.installed_files) - shown
            if remaining > 0:
                click.echo(f"  ... and {remaining} more files")
            click.echo()

        # Show total count if different from displayed
        if clean_info.total_file_count > len(clean_info.files):
            click.echo(
                click.style(
                    f"Total: {clean_info.total_file_count} files in {len(clean_info.directories)} directories",
                    fg="cyan",
                )
            )
            click.echo()

        # Ask for confirmation unless -y flag is passed
        if not yes:
            if not click.confirm("Do you want to proceed?"):
                click.echo("Clean operation cancelled.")
                return
    else:
        click.echo("No files to clean.")
        return

    # Proceed with clean
    try:
        if do_purge:
            rc = purge(bd, verbose=verbose)
        else:
            rc = clean(bd, verbose=verbose)
            # Also remove files that were previously installed
            if clean_info.installed_dirs or clean_info.installed_files:
                uninstall(bd, verbose=verbose)
    except FileNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    if rc == 0:
        click.echo(click.style("Clean completed successfully.", fg="green"))

    sys.exit(rc)


# ---------------------------------------------------------------------------
# install
# ---------------------------------------------------------------------------


@cli.command("install")
@click.option(
    "-B",
    "--build-dir",
    default="build",
    show_default=True,
    help="Build directory.",
)
@click.option(
    "--prefix",
    default=None,
    metavar="PATH",
    help="Override install prefix (e.g. /usr/local or ~/myapp).",
)
@click.option(
    "--config",
    default=None,
    help="Build configuration to install, e.g. Release or Debug.",
)
@click.option(
    "--component",
    default=None,
    metavar="COMP",
    help="Install only a specific component.",
)
@click.option(
    "--strip",
    "do_strip",
    is_flag=True,
    help="Strip installed binaries.",
)
@click.option("-v", "--verbose", is_flag=True, help="Print the cmake command.")
def cmd_install(
    build_dir: str,
    prefix: Optional[str],
    config: Optional[str],
    component: Optional[str],
    do_strip: bool,
    verbose: bool,
) -> None:
    """Install the project.

    Runs ``cmake --install <build_dir> [options]``.

    \b
    Examples:
      cmakex install
      cmakex install --prefix /usr/local
      cmakex install --prefix ~/myapp --config Release --strip
      cmakex install --component headers --prefix /opt/myproject
    """
    bd = Path(build_dir)
    if not bd.exists():
        click.echo(
            f"Error: build directory '{build_dir}' does not exist. "
            "Run 'cmakex configure' and 'cmakex build' first.",
            err=True,
        )
        sys.exit(1)

    try:
        rc = install(
            build_dir=bd,
            prefix=prefix,
            config=config,
            component=component,
            strip=do_strip,
            verbose=verbose,
        )
    except FileNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    sys.exit(rc)
