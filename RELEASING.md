---
type: reference
name: Releasing PyProyecto
description: The development to main to tagged release pipeline, and the PyPI setup that makes it installable
updated: 2026-09-19
---

# Releasing

The pipeline is **development → main → tagged release → PyPI**.

## 1. Land the work on `development`

Every push and pull request runs the unit tests on Python 3.11–3.14, plus ruff
and mypy. `development` is the integration branch.

## 2. Open a pull request into `main`

`main` is protected: it takes PRs only, and the `Unit tests` and
`Lint and type check` checks must pass before the merge button works. This is
the gate the user asked for — nothing reaches `main` without a green suite.

Before opening it: bump `version` in `pyproject.toml` and add a `CHANGELOG.md`
entry.

## 3. Tag the release on `main`

```bash
git switch main && git pull
git tag v0.1.0
git push origin v0.1.0
```

The tag triggers `release.yml`, which:

1. re-runs the tests at the tagged commit,
2. builds the wheel and sdist,
3. fails if the tag does not match the version in `pyproject.toml`,
4. creates a GitHub release with the distributions attached.

## 4. Final action: PyPI

**This is the step that makes `pip install pyproyecto` work, and it is
deliberately last.** Everything above runs today; publishing does not, because
it needs an account that only a human can create.

The `pypi` job in `release.yml` is skipped unless the repository variable
`PYPI_PUBLISH` is `true`. To turn it on:

### a. Create the PyPI account and project

1. Register at <https://pypi.org/account/register/> (or sign in).
2. Enable two-factor authentication — PyPI requires it for publishing.

### b. Register a Trusted Publisher (no API token to store)

At <https://pypi.org/manage/account/publishing/>, add a **pending publisher**
with exactly these values:

| Field | Value |
|---|---|
| PyPI project name | `pyproyecto` |
| Owner | `intrusive-memory` |
| Repository name | `PyProyecto` |
| Workflow name | `release.yml` |
| Environment name | `pypi` |

A pending publisher works before the project exists; the first successful
publish creates it and claims the name. As of 2026-09-17 the name `pyproyecto`
was unclaimed — check again before relying on it.

### c. Create the GitHub environment

```bash
gh api -X PUT repos/intrusive-memory/PyProyecto/environments/pypi
```

Optionally add yourself as a required reviewer on that environment, which makes
every publish need an explicit approval click.

### d. Switch it on

```bash
gh variable set PYPI_PUBLISH --body true --repo intrusive-memory/PyProyecto
```

Re-run the release workflow for the tag, or cut the next tag. The `pypi` job
will run and publish via OIDC. No API token is ever created or stored.

### If you would rather use an API token

Create a scoped token at <https://pypi.org/manage/account/token/>, add it as
the repository secret `PYPI_API_TOKEN`, and give the publish step:

```yaml
      - uses: pypa/gh-action-pypi-publish@release/v1
        with:
          password: ${{ secrets.PYPI_API_TOKEN }}
```

This is simpler to set up and leaves a long-lived credential in GitHub secrets.
Trusted Publishing is preferred.

## Verifying a release

```bash
pip install pyproyecto==<version>
python -c "import pyproyecto; print(pyproyecto.__version__)"
```

## What ships

The wheel and sdist contain `src/pyproyecto` only. Tests and fixtures are not
packaged, so nothing in `tests/fixtures/` is distributed through PyPI.
