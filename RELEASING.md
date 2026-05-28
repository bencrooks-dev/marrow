# Releasing marrow

The release path is automated via `.github/workflows/wheels.yml` and uses [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (no API tokens stored in GitHub secrets). To enable it you'll need a PyPI account; the rest is one-click from there.

## One-time setup

You only do this once per package per index.

### 1. Configure pending publisher on TestPyPI

1. Go to <https://test.pypi.org/manage/account/publishing/>
2. Sign in (create the account if you don't have one).
3. Under **Add a new pending publisher**, fill in:
   - **PyPI project name:** `marrow-rt`
   - **Owner:** `bencrooks-dev`
   - **Repository name:** `marrow`
   - **Workflow name:** `wheels.yml`
   - **Environment name:** `testpypi`
4. Click **Add**.

### 2. Configure pending publisher on PyPI

1. Go to <https://pypi.org/manage/account/publishing/>
2. Same flow as above, with:
   - **Environment name:** `pypi`

### 3. Create the GitHub environments

The workflow gates publishing behind two GitHub **environments**:

1. Open <https://github.com/bencrooks-dev/marrow/settings/environments>
2. Click **New environment** → name it `testpypi`. Save.
3. Click **New environment** → name it `pypi`. Save.

(You can optionally add required reviewers to the `pypi` environment if you want a manual approval gate before each prod publish.)

## Releasing a version

The workflow distinguishes **release candidates** (auto-publish to TestPyPI) from **full releases** (publish to PyPI only on GitHub Release).

### Pre-release flow (TestPyPI)

```bash
# 1. Bump version in pyproject.toml and python/marrow/__init__.py (must match)
# 2. Update CHANGELOG.md with the new version section
# 3. Commit
git add pyproject.toml python/marrow/__init__.py CHANGELOG.md
git commit -m "chore: bump version to 0.1.1rc1"

# 4. Tag (any of: rc, a, b suffixes trigger TestPyPI)
git tag v0.1.1rc1
git push origin main --tags
```

The `wheels.yml` workflow will:

1. Build wheels for Linux / macOS / Windows × Python 3.9-3.12
2. Build sdist
3. Collect into artifacts
4. **Publish to TestPyPI**

Verify:

```bash
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ \
            marrow-rt==0.1.1rc1
```

### Full release flow (PyPI)

```bash
# 1-3 same as above, but with a clean version (no rc/a/b)
git commit -m "chore: bump version to 0.1.1"
git tag v0.1.1
git push origin main --tags

# 4. Create a GitHub Release pointing at the tag
gh release create v0.1.1 \
    --title "v0.1.1" \
    --notes-file <(awk '/^## \[0\.1\.1\]/,/^## /' CHANGELOG.md | head -n -1)
```

Only the **Release published** event triggers the PyPI publish job. Pushing the tag alone is not enough — that's deliberate, so you can build wheels, inspect them, and only then promote.

## Sanity checks before any release

```bash
# All tests pass
pytest -q

# Lint is clean
ruff check python/ tests/ examples/ benchmarks/

# Docs build cleanly
mkdocs build --strict

# Examples run
for ex in examples/*.py; do python "$ex"; done

# Benchmarks complete
python -m benchmarks.run

# pyproject + __init__ versions match
grep -E '^version' pyproject.toml
grep __version__ python/marrow/__init__.py
```

If any of those fail, fix before tagging.

## Yanking a bad release

If a release ships with a critical bug:

```bash
# Yank from PyPI (does not delete; marks as "do not install")
gh api -X POST repos/bencrooks-dev/marrow/releases/<id>/assets   # delete attached assets

# Yank from PyPI manually at https://pypi.org/manage/project/marrow-rt/releases/
```

PyPI does **not** allow re-uploading the same version, even after yanking. Bump to the next patch (e.g. yank 0.1.1, ship 0.1.2 with the fix).

## Conda-forge

Not set up. Once we have a stable PyPI release, the conda-forge bot will pick up new versions automatically once a feedstock is created. See <https://conda-forge.org/docs/maintainer/adding_pkgs.html>. This is a v0.2 follow-up.
