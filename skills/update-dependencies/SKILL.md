---
name: update-dependencies
description: Update ML dependencies in numerai-predict across one or more py3.x environment directories by editing pyproject.toml, regenerating poetry.lock and requirements.txt, and running the matching build and test targets. Use when asked to bump, pin, loosen, refresh, or troubleshoot dependency versions for Numerai prediction containers.
---

# Update Dependencies

## Overview

Update dependency constraints for the numerai-predict Python container environments. Make the smallest version changes that satisfy the request and keep generated lock and requirements files in sync with each edited `py3.*` directory.

## Workflow

1. Identify scope.

   Determine the package, target version or constraint, and affected Python versions. If the user does not name specific versions, inspect all `py3.*` directories and update every supported environment where the package exists.

2. Edit `pyproject.toml`.

   Update the dependency entry in each affected version directory. Use different constraints per Python version only when package compatibility requires it.

3. Regenerate generated files.

   Run from each edited `py3.*` directory:

   ```bash
   poetry lock
   poetry export -f requirements.txt --without-hashes --output requirements.txt
   sed -i '' 's/; .*$//g' requirements.txt
   ```

   On Linux, use:

   ```bash
   sed -i 's/; .*$//g' requirements.txt
   ```

4. Validate.

   For a single-version dependency change, run:

   ```bash
   make build_3_XX
   make test_3_XX
   ```

   For cross-version changes, run:

   ```bash
   make build
   make test
   ```

## Guidelines

- Keep dependency constraints consistent across Python versions where compatibility allows.
- Do not update unrelated packages unless Poetry resolution requires it.
- Treat ML framework updates as high risk; check release compatibility for Python, NumPy, CUDA-related packages, and transitive compiled dependencies.
- If resolution fails, report the specific conflicting package and the compatible alternatives instead of making broad speculative changes.

## Verification Checklist

- Every edited `py3.*` directory has updated `pyproject.toml`, `poetry.lock`, and `requirements.txt`.
- No unrelated version directories were changed.
- Version constraints are as consistent as package compatibility allows.
- The matching build and test targets pass.
