---
name: add-python-version
description: Add support for a new Python version in numerai-predict by creating py3.x container files, updating Makefile and GitHub workflow matrices, generating lock and requirements files, creating versioned test pickle models, updating README examples, and running version-specific Docker tests. Use when asked to add, upgrade, or onboard a supported Python runtime for Numerai prediction images.
---

# Add Python Version

## Overview

Add one supported Python minor version to the numerai-predict Docker, test, and deployment matrix. Keep the implementation aligned with the latest existing `py3.*` directory and make every changed line trace to the new version.

## Inputs

Use these tokens consistently:

- `3.XX`: dotted Python version, such as `3.14`.
- `3_XX`: underscore Python version, such as `3_14`.
- `py3.XX`: version directory name.
- `3.YY`: next Python minor version for the upper `requires-python` bound.

Discover the current supported versions by listing `py3.*` directories and checking `.github/workflows/test-all.yaml`.

## Workflow

1. Verify the target Python version is viable before editing.

   Confirm that `python:3.XX-slim` exists and that core ML dependencies are available for the target version. Pay particular attention to TensorFlow, PyTorch, JAX, XGBoost, LightGBM, CatBoost, pandas, NumPy, SciPy, scikit-learn, `numerapi`, `numerai-tools`, and `numerblox`.

2. Create `py3.XX/`.

   Copy the newest existing `py3.*` directory, then update:

   - `Dockerfile`: replace the base image with `FROM python:3.XX-slim` and update any copied paths to `py3.XX`.
   - `pyproject.toml`: set `name = "py3-XX"` and `requires-python = ">=3.XX,<3.YY"`.
   - Dependencies: adjust only versions needed for Python compatibility.

3. Regenerate dependency artifacts.

   Run from the new version directory:

   ```bash
   poetry lock
   poetry export -f requirements.txt --without-hashes --output requirements.txt
   sed -i '' 's/; .*$//g' requirements.txt
   ```

   On Linux, use:

   ```bash
   sed -i 's/; .*$//g' requirements.txt
   ```

4. Update `Makefile`.

   Copy the latest existing version-specific targets and replace the version tokens. Add the new target names to the aggregate `build`, `test`, `push_latest`, and `push_stable` targets.

   Required targets:

   ```makefile
   build_3_XX
   test_3_XX
   push_latest_3_XX
   push_stable_3_XX
   ```

5. Update GitHub workflow matrices.

   Add `3_XX` to `.github/workflows/test-all.yaml`.

   Add `3{0}XX` to every Python-version matrix in:

   - `.github/workflows/deploy-images.yml`
   - `.github/workflows/deploy-stable.yaml`

6. Create test pickle models.

   Generate both files with the target Python version:

   - `tests/models/model_3_XX.pkl`: two-argument predict function, `predict(live_features, benchmark_models)`.
   - `tests/models/model_3_XX_legacy.pkl`: one-argument predict function, `predict(live_features)`.

   Prefer the repository helper when notebooks are available:

   ```bash
   python3.XX tests/generate_pkl.py --version py3.XX --notebook-path /path/to/example_model.ipynb
   python3.XX tests/generate_pkl.py --version py3.XX --notebook-path /path/to/legacy_model.ipynb --legacy
   ```

   If creating simple fixtures manually, ensure the pickle can be loaded by the target container and returns a pandas DataFrame with a `prediction` column.

7. Update `README.md`.

   Keep examples on the latest supported version:

   ```bash
   make build_3_XX
   docker run -i --rm -v "$PWD:$PWD" ghcr.io/numerai/numerai_predict_py_3_XX:stable --debug --model $PWD/model.pkl
   ```

8. Test locally.

   Run:

   ```bash
   make build_3_XX
   make test_3_XX
   ```

   If the change touches shared logic, also run:

   ```bash
   make test
   ```

## Verification Checklist

- `py3.XX/Dockerfile` exists and uses `python:3.XX-slim`.
- `py3.XX/pyproject.toml` has the correct project name and Python constraint.
- `py3.XX/poetry.lock` was generated successfully.
- `py3.XX/requirements.txt` was generated from Poetry export.
- `Makefile` includes the four version-specific targets and all aggregate target references.
- `.github/workflows/test-all.yaml` includes `3_XX`.
- `.github/workflows/deploy-images.yml` includes `3{0}XX` in all Python-version matrices.
- `.github/workflows/deploy-stable.yaml` includes `3{0}XX` in all Python-version matrices.
- Both new test pickle files exist.
- `README.md` examples use the latest supported version.
- `make build_3_XX` succeeds.
- `make test_3_XX` succeeds.

## Troubleshooting

- If Poetry cannot resolve dependencies, identify the package that lacks target-version support, then prefer compatible newer versions before loosening constraints.
- If Docker fails during `poetry install`, confirm the lock file was generated for the target Python version and that Linux wheels exist for compiled packages.
- If tests fail with pickle errors, recreate the test pickle files with the exact target Python version.
