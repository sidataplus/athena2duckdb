# Releasing `athena2duckdb`

This repo publishes to PyPI via GitHub Actions (Trusted Publishing / OIDC).

## Packaging policy

- Source distribution (sdist) is intentionally lean. It includes:
  - `src/`
  - `tests/`
  - `README.md`
  - `LICENSE`
  - `pyproject.toml`
  - `RELEASING.md`
- Hatchling always includes root VCS ignore files (for example `/.gitignore`) in sdist metadata; treat that as expected.
- CI and publish workflows run `twine check dist/*` before any upload.

## One-time setup (PyPI)

1. Create the project on PyPI (and optionally TestPyPI) using the name `athena2duckdb`.
2. In PyPI, configure **Trusted Publishing** for this GitHub repo:
   - Owner: `sidataplus`
   - Repository: `athena2duckdb`
   - Workflow: `.github/workflows/publish.yml`

## First release (TestPyPI only once)

1. Bump `version` in `pyproject.toml` and merge to `main`.
2. Run the GitHub Actions workflow **Publish (TestPyPI)** (`.github/workflows/publish-testpypi.yml`).
3. Smoke-test install:
   - `pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ athena2duckdb`
   - `athena2duckdb --help`

## Regular releases (PyPI)

1. Bump `version` in `pyproject.toml` and merge to `main`.
2. Create and push a tag matching `v*.*.*` (example: `v0.1.1`):
   - `git tag -a v0.1.1 -m "v0.1.1"`
   - `git push origin v0.1.1`
3. The **Publish** workflow (`.github/workflows/publish.yml`) enforces that tag and project version match:
   - Tag must be `v{project.version}` from `pyproject.toml`.
   - Example: `version = "0.1.1"` requires tag `v0.1.1`.
4. The **Publish** workflow builds, validates (`twine check`), and uploads `dist/` to PyPI.

## Local validation (optional)

- `uv run pytest`
- `uv build`
- `uv run --with twine twine check dist/*`
