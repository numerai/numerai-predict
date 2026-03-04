# Skills for numerai-predict

This document contains reusable skills for common tasks in the numerai-predict repository.

---

## Skill: add-python-version

### Purpose
Add support for a new Python version to the numerai-predict infrastructure. This involves creating container configurations, updating build systems, and ensuring CI/CD pipelines include the new version.

### Prerequisites
- Docker installed locally
- Poetry 2.x installed (`pip install poetry`)
- The target Python version must have a `python:X.XX-slim` Docker image available
- Key ML dependencies (tensorflow, torch, etc.) should support the target Python version

### Steps

#### Step 1: Create the Version Directory

Create a new directory `py3.XX/` (replace XX with the version number):

```bash
mkdir py3.XX
```

#### Step 2: Create the Dockerfile

Create `py3.XX/Dockerfile` with the following content:

```dockerfile
FROM python:3.XX-slim

ARG GIT_REF
ENV GIT_REF=$GIT_REF

RUN apt-get update -yqq && apt-get install -yqq --no-install-recommends \
    build-essential \
    cmake \
    git \
    curl \
    python3-dev \
    python3-pip \
    python3-venv \
    libffi-dev

RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir poetry==2.1.3

ENV POETRY_HOME="/opt/poetry"
ENV PATH="${POETRY_HOME}/bin:$PATH"

COPY ./py3.XX/pyproject.toml ./pyproject.toml
COPY ./py3.XX/poetry.lock ./poetry.lock

RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

COPY ./predict.py .

ENTRYPOINT ["python", "predict.py"]
```

#### Step 3: Create pyproject.toml

Create `py3.XX/pyproject.toml`. Start by copying from the most recent version (e.g., py3.12) and modify:

1. Change `name` to `"py3-XX"`
2. Change `requires-python` to `">=3.XX,<3.YY"` (where YY = XX + 1)
3. Review and update dependency versions for Python compatibility

Key sections:
```toml
[project]
name = "py3-XX"
version = "0.1.0"
readme = "../README.md"
requires-python = ">=3.XX,<3.YY"

dependencies = [
    # Copy dependencies from latest version, adjust versions as needed
]

[tool.poetry]
package-mode = false

[build-system]
requires = ["poetry-core>=2.0.0,<3.0.0"]
build-backend = "poetry.core.masonry.api"
```

#### Step 4: Generate poetry.lock

```bash
cd py3.XX
poetry lock
```

If dependency resolution fails:
- Check which packages don't support the new Python version
- Look for updated versions of problematic packages
- Consider loosening version constraints (e.g., `>=X.Y,<Z.0` instead of `==X.Y.Z`)
- Some packages may need to be temporarily removed or replaced

#### Step 5: Generate requirements.txt

```bash
poetry export -f requirements.txt --without-hashes --output requirements.txt
sed -i '' 's/; .*$//g' requirements.txt  # macOS
# or: sed -i 's/; .*$//g' requirements.txt  # Linux
```

#### Step 6: Update Makefile

Add the following targets to `Makefile`:

```makefile
# In the build: target, add build_3_XX
build: build_3_10 build_3_11 build_3_12 build_3_XX

.PHONY: build_3_XX
build_3_XX: ## Build Python 3.XX container
	docker build --platform=linux/amd64 --build-arg GIT_REF=${GIT_REF} -t ${NAME}_py_3_XX:${GIT_REF} -t ${NAME}_py_3_XX:latest -f py3.XX/Dockerfile .

# In the test: target, add test_3_XX
test: test_predict test_3_10 test_3_11 test_3_12 test_3_XX

.PHONY: test_3_XX
test_3_XX: build_3_XX ## Test Python 3.XX pickle
	docker run -i --rm -v ./tests/:/tests/ -v /tmp:/tmp ${NAME}_py_3_XX:latest --model /tests/models/model_3_XX_legacy.pkl
	docker run -i --rm -v ./tests/:/tests/ -v /tmp:/tmp ${NAME}_py_3_XX:latest --model /tests/models/model_3_XX.pkl

# In the push_latest: target, add push_latest_3_XX
push_latest: push_latest_3_10 push_latest_3_11 push_latest_3_12 push_latest_3_XX

.PHONY: push_latest_3_XX
push_latest_3_XX: build_3_XX ## Release Python 3.XX container tagged latest
	aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin ${ECR_REPO}
	docker tag ${NAME}_py_3_XX:${GIT_REF} ${ECR_REPO}/${NAME}_py_3_XX:${GIT_REF}
	docker tag ${NAME}_py_3_XX:latest ${ECR_REPO}/${NAME}_py_3_XX:latest
	docker push ${ECR_REPO}/${NAME}_py_3_XX:${GIT_REF}
	docker push ${ECR_REPO}/${NAME}_py_3_XX:latest

# Add push_stable_3_XX target
.PHONY: push_stable_3_XX
push_stable_3_XX: build_3_XX ## Release Python 3.XX container tagged stable
	aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin ${ECR_REPO}
	docker tag ${NAME}_py_3_XX:${GIT_REF} ${ECR_REPO}/${NAME}_py_3_XX:${GIT_REF}
	docker tag ${NAME}_py_3_XX:latest ${ECR_REPO}/${NAME}_py_3_XX:stable
	docker push ${ECR_REPO}/${NAME}_py_3_XX:${GIT_REF}
	docker push ${ECR_REPO}/${NAME}_py_3_XX:stable
```

#### Step 7: Update GitHub Workflows

**`.github/workflows/test-all.yaml`**
Add the new version to the matrix:
```yaml
matrix:
  python-version: ['3_10', '3_11', '3_12', '3_XX']
```

**`.github/workflows/deploy-images.yml`**
Add to both `public-images` and `internal-images` job matrices:
```yaml
matrix:
  python-version: ['3{0}10', '3{0}11', '3{0}12', '3{0}XX']
```

**`.github/workflows/deploy-stable.yaml`**
Add to both `public-image` and `internal-image` job matrices:
```yaml
matrix:
  python-version: ['3{0}10', '3{0}11', '3{0}12', '3{0}XX']
```

#### Step 8: Create Test Pickle Models

Test pickle files must be created using the target Python version. Two files are needed:

- **`model_3_XX.pkl`** - Uses 2-argument predict function: `predict(live_features, benchmark_models)`
- **`model_3_XX_legacy.pkl`** - Uses 1-argument predict function: `predict(live_features)`

**Option A: Generate from a Jupyter notebook**

Use the `tests/generate_pkl.py` script to run a notebook and copy the output:

```bash
# Generate non-legacy pkl (2-arg predict function)
python3.XX tests/generate_pkl.py --version py3.XX --notebook-path /path/to/example_model.ipynb

# Generate legacy pkl (1-arg predict function)
python3.XX tests/generate_pkl.py --version py3.XX --notebook-path /path/to/legacy_model.ipynb --legacy
```

**Option B: Create simple test models manually**

```python
# Run with Python 3.XX
import pickle
import pandas as pd

def predict_legacy(live_features: pd.DataFrame) -> pd.DataFrame:
    """Legacy format (1-arg): returns predictions with 'prediction' column."""
    predictions = pd.DataFrame(index=live_features.index)
    predictions["prediction"] = 0.5
    return predictions

def predict(live_features: pd.DataFrame, benchmark_models: pd.DataFrame) -> pd.DataFrame:
    """New format (2-arg): returns predictions with 'prediction' column."""
    predictions = pd.DataFrame(index=live_features.index)
    predictions["prediction"] = live_features.iloc[:, 0].rank(pct=True)
    return predictions

# Save legacy format (1-arg)
with open("tests/models/model_3_XX_legacy.pkl", "wb") as f:
    pickle.dump(predict_legacy, f)

# Save new format (2-arg)
with open("tests/models/model_3_XX.pkl", "wb") as f:
    pickle.dump(predict, f)
```

#### Step 9: Update README.md

Update the `README.md` to use the new Python version in examples. The README should always showcase the latest supported Python version:

1. Update the build example to use the new version:
```bash
# to build on python 3.XX
make build_3_XX
```

2. Update the docker run example to use the new version:
```bash
docker run -i --rm -v "$PWD:$PWD" ghcr.io/numerai/numerai_predict_py_3_XX:stable --debug --model $PWD/model.pkl
```

#### Step 10: Test Locally

```bash
# Build the container
make build_3_XX

# Run tests (requires test pickle files)
make test_3_XX

# Debug manually
docker run -i --rm -v "$PWD:$PWD" numerai_predict_py_3_XX:latest --debug --model $PWD/tests/models/model_3_XX.pkl
```

### Verification Checklist

- [ ] `py3.XX/Dockerfile` exists and uses correct base image
- [ ] `py3.XX/pyproject.toml` has correct Python version constraint
- [ ] `py3.XX/poetry.lock` generated successfully
- [ ] `py3.XX/requirements.txt` generated from poetry export
- [ ] Makefile has `build_3_XX`, `test_3_XX`, `push_latest_3_XX`, `push_stable_3_XX` targets
- [ ] `.github/workflows/test-all.yaml` includes new version in matrix
- [ ] `.github/workflows/deploy-images.yml` includes new version in both matrices
- [ ] `.github/workflows/deploy-stable.yaml` includes new version in both matrices
- [ ] `tests/models/model_3_XX.pkl` exists
- [ ] `tests/models/model_3_XX_legacy.pkl` exists
- [ ] `make build_3_XX` succeeds
- [ ] `make test_3_XX` succeeds
- [ ] `README.md` examples updated to use new Python version

### Troubleshooting

**Poetry can't resolve dependencies**
- Some packages may not support the new Python version yet
- Check PyPI for each failing package to see supported versions
- Try using newer versions of packages that failed
- As a last resort, remove packages that don't support the new version

**Docker build fails at poetry install**
- Check the poetry.lock was generated with the correct Python version
- Verify all packages have wheels for the target platform (linux/amd64)
- Check for C extension packages that may need compilation

**Tests fail with pickle errors**
- Ensure test pickle files were created with the matching Python version
- Recreate the pickle files using the instructions above

---

## Skill: update-dependencies

### Purpose
Update ML dependencies across all Python versions to newer versions.

### Steps

1. Identify the package and target version
2. Update `pyproject.toml` in each `py3.XX/` directory
3. Regenerate `poetry.lock` in each directory
4. Regenerate `requirements.txt` from poetry export
5. Build and test all versions: `make build && make test`

### Notes
- Different Python versions may need different package versions
- Keep version constraints consistent where possible
- Test thoroughly as ML packages can have breaking changes
