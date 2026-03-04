#!/usr/bin/env python
"""
Generate test pickle files by running a Jupyter notebook under a specific Python version.

Usage:
    python tests/generate_pkl.py --version py3.13 --notebook-path ../example-scripts/numerai/example_model.ipynb
    python tests/generate_pkl.py --version py3.12 --notebook-path /abs/path/to/notebook.ipynb --legacy

This script:
1. Runs the notebook using the specified Python version
2. Finds the generated .pkl file in the notebook's directory
3. Copies it to tests/models/ with the appropriate naming convention

Arguments:
    --version: Python version directory (e.g., py3.10, py3.11, py3.12, py3.13)
    --notebook-path: Path to the Jupyter notebook (relative or absolute)
    --legacy: If set, names the output as model_X_XX_legacy.pkl (for 1-arg predict functions)
    --output-name: Override the output pkl filename in the notebook directory (default: auto-detect)
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def find_python_executable(version: str) -> str:
    """Find the Python executable for the given version (e.g., py3.13 -> python3.13)."""
    minor_version = version.replace("py", "").replace("_", ".")
    
    candidates = [
        f"python{minor_version}",
        f"python{minor_version.replace('.', '')}",
    ]
    
    for candidate in candidates:
        result = subprocess.run(
            ["which", candidate],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
    
    raise RuntimeError(
        f"Could not find Python executable for version {version}. "
        f"Tried: {candidates}. Make sure Python {minor_version} is installed."
    )


def run_notebook(notebook_path: Path, python_executable: str) -> None:
    """Run the notebook using papermill or nbconvert."""
    notebook_dir = notebook_path.parent
    
    try:
        subprocess.run(
            [python_executable, "-c", "import papermill"],
            capture_output=True,
            check=True
        )
        has_papermill = True
    except subprocess.CalledProcessError:
        has_papermill = False
    
    if has_papermill:
        print(f"Running notebook with papermill using {python_executable}...")
        output_notebook = notebook_path.with_suffix(".executed.ipynb")
        cmd = [
            python_executable, "-m", "papermill",
            str(notebook_path),
            str(output_notebook),
            "--cwd", str(notebook_dir)
        ]
    else:
        print(f"Running notebook with nbconvert using {python_executable}...")
        cmd = [
            python_executable, "-m", "jupyter", "nbconvert",
            "--to", "notebook",
            "--execute",
            "--inplace",
            "--ExecutePreprocessor.timeout=1800",
            str(notebook_path)
        ]
    
    print(f"Command: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=notebook_dir)
    
    if result.returncode != 0:
        raise RuntimeError(f"Notebook execution failed with exit code {result.returncode}")
    
    print("Notebook executed successfully.")


def find_pkl_file(notebook_dir: Path, output_name: str | None = None) -> Path:
    """Find the generated pkl file in the notebook directory."""
    if output_name:
        pkl_path = notebook_dir / output_name
        if pkl_path.exists():
            return pkl_path
        raise FileNotFoundError(f"Specified pkl file not found: {pkl_path}")
    
    pkl_files = list(notebook_dir.glob("*.pkl"))
    
    pkl_files = [p for p in pkl_files if ".executed" not in p.name]
    
    if not pkl_files:
        raise FileNotFoundError(f"No .pkl files found in {notebook_dir}")
    
    if len(pkl_files) > 1:
        pkl_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        print(f"Multiple pkl files found, using most recent: {pkl_files[0].name}")
    
    return pkl_files[0]


def copy_pkl_to_tests(pkl_path: Path, version: str, legacy: bool, repo_root: Path) -> Path:
    """Copy the pkl file to tests/models/ with the appropriate name."""
    version_num = version.replace("py", "").replace(".", "_")
    
    if legacy:
        dest_name = f"model_{version_num}_legacy.pkl"
    else:
        dest_name = f"model_{version_num}.pkl"
    
    dest_dir = repo_root / "tests" / "models"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / dest_name
    
    print(f"Copying {pkl_path} -> {dest_path}")
    shutil.copy2(pkl_path, dest_path)
    
    return dest_path


def main():
    parser = argparse.ArgumentParser(
        description="Generate test pickle files by running a Jupyter notebook"
    )
    parser.add_argument(
        "--version",
        required=True,
        help="Python version directory (e.g., py3.10, py3.11, py3.12, py3.13)"
    )
    parser.add_argument(
        "--notebook-path",
        required=True,
        help="Path to the Jupyter notebook (relative or absolute)"
    )
    parser.add_argument(
        "--legacy",
        action="store_true",
        help="Name output as model_X_XX_legacy.pkl (for 1-arg predict functions)"
    )
    parser.add_argument(
        "--output-name",
        help="Name of the pkl file generated by the notebook (default: auto-detect)"
    )
    parser.add_argument(
        "--skip-run",
        action="store_true",
        help="Skip running the notebook, just copy existing pkl"
    )
    
    args = parser.parse_args()
    
    script_path = Path(__file__).resolve()
    repo_root = script_path.parent.parent
    
    notebook_path = Path(args.notebook_path)
    if not notebook_path.is_absolute():
        notebook_path = Path.cwd() / notebook_path
    notebook_path = notebook_path.resolve()
    
    if not notebook_path.exists():
        print(f"Error: Notebook not found: {notebook_path}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Notebook: {notebook_path}")
    print(f"Version: {args.version}")
    print(f"Legacy: {args.legacy}")
    
    if not args.skip_run:
        python_executable = find_python_executable(args.version)
        print(f"Python executable: {python_executable}")
        
        version_check = subprocess.run(
            [python_executable, "--version"],
            capture_output=True,
            text=True
        )
        print(f"Python version: {version_check.stdout.strip()}")
        
        run_notebook(notebook_path, python_executable)
    
    pkl_path = find_pkl_file(notebook_path.parent, args.output_name)
    print(f"Found pkl file: {pkl_path}")
    
    dest_path = copy_pkl_to_tests(pkl_path, args.version, args.legacy, repo_root)
    print(f"\nSuccess! Test model saved to: {dest_path}")
    
    print(f"\nTo test this model:")
    version_num = args.version.replace("py", "").replace(".", "_")
    print(f"  make test_{version_num}")


if __name__ == "__main__":
    main()
