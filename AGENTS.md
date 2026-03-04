# Agent Guidelines for numerai-predict

This document provides guidance for AI agents working on the numerai-predict repository.

## Project Overview

**numerai-predict** is an open-source prediction infrastructure for [Numerai Tournament](https://numer.ai) users. It provides Docker containers with pre-installed ML dependencies that execute user-uploaded pickle models against live tournament data.

### Core Functionality

The `predict.py` script:
1. Downloads live features from Numerai (or uses local files)
2. Loads a user's pickled model (function that takes a DataFrame and returns predictions)
3. Runs inference and validates output
4. Uploads predictions to S3 (or saves locally for debugging)

## Architecture

```
numerai-predict/
├── predict.py              # Main prediction script (entrypoint for all containers)
├── Makefile                # Build, test, and deployment targets
├── .python-version         # Default Python version for local development
├── py3.{XX}/               # One directory per supported Python version (e.g., py3.10/, py3.11/, ...)
│   ├── Dockerfile
│   ├── pyproject.toml      # Poetry dependencies (source of truth)
│   ├── poetry.lock         # Locked dependency versions
│   └── requirements.txt    # Generated from poetry for pip users
├── shell/                  # Shell container for running tests
│   └── Dockerfile
├── tests/
│   ├── test_predict.py     # Unit tests for predict.py
│   └── models/             # Test pickle files (one per Python version)
│       ├── model_3_{XX}.pkl
│       └── model_3_{XX}_legacy.pkl
└── .github/workflows/
    ├── test-all.yaml       # CI: tests all Python versions
    ├── deploy-images.yml   # CD: push to GHCR on master
    └── deploy-stable.yaml  # CD: push stable tags
```

**To discover supported Python versions:** List `py3.*` directories or check the matrix in `.github/workflows/test-all.yaml`.

## Key Files Reference

### predict.py
- Argument parsing: `--model`, `--dataset`, `--benchmarks`, `--output_dir`, `--post_url`, `--post_data`, `--debug`
- Model loading via `pd.read_pickle()`
- Supports both 1-arg models `model(features)` and 2-arg models `model(features, benchmarks)`
- Validation: checks for None, wrong type, empty results, NaN values, out-of-range predictions

### Makefile Targets

| Target | Description |
|--------|-------------|
| `help` | List all available targets |
| `lint` | Run ruff linter |
| `build` | Build all Python version containers |
| `build_3_{XX}` | Build specific Python version container |
| `build_shell` | Build shell container for testing |
| `test` | Run all tests |
| `test_predict` | Run predict.py unit tests |
| `test_3_{XX}` | Test specific Python version with its pickle models |
| `push_latest` | Push all containers with :latest tag |
| `push_latest_3_{XX}` | Push specific version with :latest tag |
| `push_stable` | Push all containers with :stable tag |
| `push_stable_3_{XX}` | Push specific version with :stable tag |

**Note:** Replace `{XX}` with the minor version number (e.g., `10`, `11`, `12`, `13`).

### pyproject.toml Structure
Each Python version's `pyproject.toml` follows this pattern:
```toml
[project]
name = "py3-{XX}"
version = "0.1.0"
readme = "../README.md"
requires-python = ">=3.{XX},<3.{YY}"  # Where YY = XX + 1

dependencies = [
    # ML frameworks: tensorflow, torch, keras, jax
    # Tree models: xgboost, lightgbm, catboost
    # Data: pandas, numpy, polars, pyarrow
    # Numerai-specific: numerapi, numerai-tools, numerblox
    # Other: scikit-learn, scipy, onnx, etc.
]

[tool.poetry]
package-mode = false

[build-system]
requires = ["poetry-core>=2.0.0,<3.0.0"]
build-backend = "poetry.core.masonry.api"
```

### GitHub Workflow Matrix
Workflows use a matrix strategy. Check the workflow files for the current list of supported versions:
```yaml
matrix:
  python-version: ['3_10', '3_11', ...]  # test-all.yaml format
  python-version: ['3{0}10', '3{0}11', ...]  # deploy workflows format
```
The deploy format allows `format(matrix.python-version, '.')` → `3.10` and `format(matrix.python-version, '_')` → `3_10`.

## Common Tasks

### Adding a New Python Version
See `SKILLS.md` for the detailed skill: `add-python-version`.

Summary:
1. Create `py3.{XX}/` directory with Dockerfile and pyproject.toml
2. Run `poetry lock` to generate poetry.lock
3. Export to requirements.txt
4. Update Makefile with build/test/push targets
5. Update all GitHub workflows to include new version
6. Create test pickle models
7. Update README.md examples to use the new version
8. Test locally with `make test_3_{XX}`

### Updating Dependencies
1. Edit the version-specific `pyproject.toml`
2. Run `poetry lock` in that directory
3. Export: `poetry export -f requirements.txt --without-hashes --output requirements.txt`
4. Clean up: `sed -i '' 's/; .*$//g' requirements.txt`
5. Build and test: `make build_3_{XX} && make test_3_{XX}`

### Testing Locally
```bash
# Run all tests
make test

# Test specific Python version (replace {XX} with version number)
make test_3_{XX}

# Debug a pickle model manually (replace {XX} with version number)
docker run -i --rm -v "$PWD:$PWD" numerai_predict_py_3_{XX}:latest --debug --model $PWD/path/to/model.pkl
```

## Dependency Considerations

### Critical Dependencies
- **numerapi**: Must be compatible for downloading tournament data
- **pandas**: Models receive and return DataFrames
- **numpy**: Underlying numerical operations
- **torch/tensorflow/keras**: Common model frameworks
- **xgboost/lightgbm/catboost**: Popular tree-based models
- **scikit-learn**: Preprocessing and simple models

### Python Version Compatibility Notes
- Some packages lag behind new Python releases (tensorflow, torch especially)
- Check PyPI for version compatibility before adding new Python version
- Some packages may need version bumps or have wheel availability issues

## Container Registries

Images are published to:
- **GitHub Container Registry (GHCR)**: `ghcr.io/numerai/numerai_predict_py_3_{XX}:latest|stable|<git-sha>`
- **AWS ECR (internal)**: For Numerai's production infrastructure

## Troubleshooting

### Poetry Lock Failures
- Check if all dependencies support the Python version
- Try loosening version constraints
- Check for conflicting transitive dependencies

### Docker Build Failures
- Ensure base image `python:3.{XX}-slim` exists on Docker Hub
- Check for missing system dependencies in apt-get install
- Verify poetry.lock is generated for the correct Python version

### Test Failures
- Pickle files must be created with the matching Python version
- Check for missing test model files in `tests/models/`
- Verify legacy and new format pickle files both exist

## Skills Available

| Skill | Location | Purpose |
|-------|----------|---------|
| add-python-version | `SKILLS.md` | Add support for a new Python version |
