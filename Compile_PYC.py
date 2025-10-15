from __future__ import annotations
import argparse
import shutil
import sys
import py_compile
import time
from pathlib import Path

DEFAULT_ROOTS = [
    "FedPro",
    "FedProProtobuf",
    "HLA_bounce",
    "RTI_py",
    "SimpleFedPro",
]

"""Compile project Python sources to .pyc under a dedicated bin tree.

Creates a mirror of the selected source package directories inside
./bin preserving their relative structure but ONLY writes __pycache__
folders with .pyc files (no source copies). This keeps runtime cache
separate from your working tree.

Usage examples:
    python compile_pyc.py                (incremental compile)
    python compile_pyc.py --clean        (wipe bin then compile)
    python compile_pyc.py -O 1           (optimize: strip asserts)
    python compile_pyc.py -O 2           (optimize: strip asserts + docstrings)
    python compile_pyc.py --roots FedPro HLA_bounce

Exit code: 0 on success, 1 if any file failed to compile.
"""

def parse_args() -> argparse.Namespace:
    # Description: Parse command-line arguments controlling compilation behavior.
    # Inputs: Reads from sys.argv implicitly (argparse).
    # Outputs: argparse.Namespace with attributes: roots (list[str]), clean (bool), opt (int), quiet (bool).
    # Exceptions: SystemExit on invalid arguments (argparse default behavior).
    parser = argparse.ArgumentParser(description="Compile project sources to .pyc under ./bin")
    parser.add_argument("--roots", nargs="*", default=DEFAULT_ROOTS, help="Root subdirectories to include")
    parser.add_argument("--clean", action="store_true", help="Remove existing bin directory before compiling")
    parser.add_argument("-O", "--opt", type=int, choices=(0, 1, 2), default=0, help="Optimization level (matches python -O / -OO)")
    parser.add_argument("--quiet", action="store_true", help="Reduce output (only errors + summary)")
    return parser.parse_args()


def compute_pyc_name(source: Path, opt: int) -> str:
    """Return canonical pycache file name for a module."""
    # Description: Build standardized .pyc filename including interpreter cache tag and optimization level.
    # Inputs:
    #   source (Path): Source .py file path.
    #   opt (int): Optimization level (0,1,2).
    # Outputs: str filename (no directory portion).
    # Exceptions: None.
    tag = sys.implementation.cache_tag or "cpython"
    opt_tag = "" if opt == 0 else f".opt-{opt}"
    return f"{source.stem}.{tag}{opt_tag}.pyc"


def should_skip(path: Path) -> bool:
    # Description: Determine whether a path should be excluded from compilation.
    # Inputs:
    #   path (Path): Candidate file path.
    # Outputs: bool True if path resides in ignored directories or hidden.
    # Exceptions: None
    parts = path.parts
    # Skip virtual envs, bin outputs, hidden dirs
    return any(
        p.startswith(".") or p.lower() in {"__pycache__", "bin", "scripts", "include", "lib", "site-packages"}
        for p in parts
    )


def compile_tree(base: Path, roots: list[str], out_root: Path, opt: int, quiet: bool) -> int:
    # Description: Recursively compile all .py files under specified roots into mirrored bin/__pycache__ tree.
    # Inputs:
    #   base (Path): Project base directory (script location).
    #   roots (list[str]): Top-level subdirectories to traverse.
    #   out_root (Path): Destination root where bin tree resides.
    #   opt (int): Optimization level passed to py_compile.
    #   quiet (bool): If True, suppress per-file success output.
    # Outputs: int number of files that failed to compile (error count).
    # Exceptions: Unexpected exceptions propagate; py_compile and OSError handled per file.
    errors = 0
    total = 0
    start = time.time()

    for root in roots:
        src_root = base / root
        if not src_root.exists():
            if not quiet:
                print(f"[WARN] Skipping missing root {src_root}")
            continue
        for py in src_root.rglob("*.py"):
            if should_skip(py):
                continue
            rel = py.relative_to(base)
            target_pkg_dir = out_root / rel.parent
            cache_dir = target_pkg_dir / "__pycache__"
            cache_dir.mkdir(parents=True, exist_ok=True)
            pyc_name = compute_pyc_name(py, opt)
            cfile = cache_dir / pyc_name
            try:
                py_compile.compile(
                    str(py),
                    cfile=str(cfile),
                    dfile=str(rel),  # recorded path inside pyc (relative)
                    optimize=opt,
                    invalidation_mode=py_compile.PycInvalidationMode.TIMESTAMP,
                )
                total += 1
                if not quiet:
                    print(f"Compiled {rel} -> {cfile.relative_to(base)}")
            except (py_compile.PyCompileError, OSError) as e:
                errors += 1
                print(f"FAILED {rel}: {e}", file=sys.stderr)
    dur = time.time() - start
    if errors:
        print(f"Completed with {errors} errors out of {total} attempted in {dur:.2f}s", file=sys.stderr)
    else:
        print(f"Success: {total} files compiled in {dur:.2f}s")
    return errors


def main() -> int:
    # Description: Orchestrate argument parsing, optional clean, directory prep, and compilation.
    # Inputs: None (reads CLI args via parse_args).
    # Outputs: int exit code (0 success, 1 on errors).
    # Exceptions: Propagates unexpected filesystem errors (e.g., permissions) not caught in compile_tree.
    args = parse_args()
    base = Path(__file__).resolve().parent
    out_root = base / "bin"

    if args.clean and out_root.exists():
        if not args.quiet:
            print(f"Removing {out_root} ...")
        shutil.rmtree(out_root, ignore_errors=True)

    out_root.mkdir(parents=True, exist_ok=True)
    if not args.quiet:
        print(f"Base:   {base}")
        print(f"Output: {out_root}")
        print(f"Roots:  {', '.join(args.roots)}")
        print(f"Opt:    {args.opt}")

    return 1 if compile_tree(base, args.roots, out_root, args.opt, args.quiet) else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
